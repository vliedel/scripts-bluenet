#!/usr/bin/env python3

import random
import matplotlib.pyplot as plt
import numpy as np

GRID_INTERVAL_US   = 10080
DIMMER_INTERVAL_US = 10000


# Chance that a zero crossing interrupt is skipped.
ZERO_CROSSING_MISSING_CHANCE = 0.1

# Change that there's a delay of the zero crossing interrupt.
ZERO_CROSSING_DELAY_CHANCE = 1.0

# How much the zero crossing interrupt is delayed.
ZERO_CROSSING_DELAY_PARETO_ALPHA = 2 # Lower alpha means more spread.
ZERO_CROSSING_DELAY_PARETO_MULTIPLIER = 100
# ZERO_CROSSING_DELAY_PARETO_MULTIPLIER = 0
ZERO_CROSSING_DELAY_MAX_US = 5000 # Delay will never be more than this.

# How much time to simulate.
SIM_TIME_SECONDS = 10

# Whether to round intermediate calculations.
def maybeRound(val):
    return int(val)
    # return val

DIMMER_TIMER_MAX_TICKS = 4 * DIMMER_INTERVAL_US

DIMMER_NUM_CROSSINGS_BEFORE_CONTROL = 10

# This function is what happens in the firmware.
errIntegral = 0
zeroCrossingCounter = 0
errHist = []
errSlopesPlot = [] # For plotting

dimmerSynchedIntervalMaxTicks = DIMMER_TIMER_MAX_TICKS
def onZeroCrossing(dimmerTimerCapture, dimmerMaxTicks):
    target = 0
    err = maybeRound(dimmerTimerCapture) - target
    if (err > maybeRound(DIMMER_TIMER_MAX_TICKS/2)):
        err -= DIMMER_TIMER_MAX_TICKS
    if (err < maybeRound(-DIMMER_TIMER_MAX_TICKS/2)):
        err += DIMMER_TIMER_MAX_TICKS

    global errHist
    errHist.append(err)

    global errIntegral
    errIntegral += err

    global zeroCrossingCounter
    zeroCrossingCounter += 1
    if (zeroCrossingCounter % DIMMER_NUM_CROSSINGS_BEFORE_CONTROL == 0):
        avgSlope = errHist[DIMMER_NUM_CROSSINGS_BEFORE_CONTROL-1] - errHist[0]
        if (avgSlope > maybeRound(DIMMER_TIMER_MAX_TICKS / 2)):
            avgSlope -= DIMMER_TIMER_MAX_TICKS
        if (avgSlope < maybeRound(-DIMMER_TIMER_MAX_TICKS / 2)):
            avgSlope += DIMMER_TIMER_MAX_TICKS

        errSlopes = []
        avgDeviationFromAvg = 0
        for i in range(1, DIMMER_NUM_CROSSINGS_BEFORE_CONTROL):
            slope = errHist[i] - errHist[i-1]
            if (slope > maybeRound(DIMMER_TIMER_MAX_TICKS / 2)):
                slope -= DIMMER_TIMER_MAX_TICKS
            if (slope < maybeRound(-DIMMER_TIMER_MAX_TICKS / 2)):
                slope += DIMMER_TIMER_MAX_TICKS
            errSlopes.append(slope)
            avgDeviationFromAvg += abs(slope - avgSlope)
        avgDeviationFromAvg /= (DIMMER_NUM_CROSSINGS_BEFORE_CONTROL-1)

        filteredAvgSlope = 0
        for i in range(0, DIMMER_NUM_CROSSINGS_BEFORE_CONTROL-1):
            slope = errSlopes[i]
            if (abs(slope - avgSlope) < 2 * avgDeviationFromAvg):
                filteredAvgSlope += slope
        filteredAvgSlope /= (DIMMER_NUM_CROSSINGS_BEFORE_CONTROL-1)

        errHist = []
        global errSlopesPlot
        errSlopesPlot.append(filteredAvgSlope)

        global dimmerSynchedIntervalMaxTicks
        dimmerSynchedIntervalMaxTicks += maybeRound(filteredAvgSlope / DIMMER_TIMER_MAX_TICKS * 4000)

        integralAbsMax = DIMMER_TIMER_MAX_TICKS * 1000
        if (errIntegral > integralAbsMax):
            errIntegral = integralAbsMax
        if (errIntegral < -integralAbsMax):
            errIntegral = -integralAbsMax

        delta = 0
        deltaP = maybeRound(err / DIMMER_TIMER_MAX_TICKS * 1000)
        deltaI = maybeRound(errIntegral / DIMMER_TIMER_MAX_TICKS * 2)
        delta = deltaP + deltaI
        # delta = deltaP

        limitDelta = maybeRound(DIMMER_TIMER_MAX_TICKS / 120)
        if (delta > limitDelta):
            delta = limitDelta
        if (delta < -limitDelta):
            delta = -limitDelta

        # newDimmerMaxTicks = int(DIMMER_TIMER_MAX_TICKS + delta)
        newDimmerMaxTicks = int(dimmerSynchedIntervalMaxTicks + delta)
        print("capture=", dimmerTimerCapture, " err=", err, " errSlope=", filteredAvgSlope, "errIntegral=", errIntegral, " deltaP=", deltaP, " deltaI=", deltaI, " delta=", delta, " synchedMaxTicks=", dimmerSynchedIntervalMaxTicks,  "newMaxTicks=", newDimmerMaxTicks)
        return newDimmerMaxTicks
    return dimmerMaxTicks




def main():
    t = 0
    interruptTimestamps = []
    interruptDelays = []
    numZeroCrossing = int(SIM_TIME_SECONDS * 1000 * 1000 / GRID_INTERVAL_US)
    for i in range(0, numZeroCrossing):
        delay = 0
        if random.random() < ZERO_CROSSING_MISSING_CHANCE:
            t += GRID_INTERVAL_US
            continue
        if random.random() < ZERO_CROSSING_DELAY_CHANCE:
            delay = (random.paretovariate(ZERO_CROSSING_DELAY_PARETO_ALPHA) - 1) * ZERO_CROSSING_DELAY_PARETO_MULTIPLIER
            if (delay > ZERO_CROSSING_DELAY_MAX_US):
                delay = ZERO_CROSSING_DELAY_MAX_US
        interruptDelays.append(delay)
        timestamp = t + delay
        interruptTimestamps.append(timestamp)
        t = t + GRID_INTERVAL_US

    plt.figure()
    axDelay = plt.gca()
    axDelay.set_title("Zero crossing interrupt delay")
    axDelay.set_ylabel("μs")
    axDelay.plot(interruptDelays, 'o')

    dimmerTimerStart = 0
    dimmerInterval = DIMMER_INTERVAL_US
    dimmerTimerStartTimes = []
    dimmerTimerCaptures = []
    dimmerIntervals = []
    for zeroCrossingInterruptTime in interruptTimestamps:
        while ((dimmerTimerStart + dimmerInterval) < zeroCrossingInterruptTime):
            dimmerTimerStart += dimmerInterval
        dimmerTimerStartTimes.append(dimmerTimerStart)
        dimmerTimerCapture = 4*(zeroCrossingInterruptTime - dimmerTimerStart)
        dimmerTimerCaptures.append(dimmerTimerCapture)
        dimmerIntervals.append(dimmerInterval)

        # Control action here
        dimmerInterval = onZeroCrossing(dimmerTimerCapture, 4 * dimmerInterval) / 4


    dimmerOffsets = np.array(dimmerTimerCaptures)
    # dimmerOffsets = np.array(interruptTimestamps) - np.array(dimmerTimerStartTimes)
    for i in range(0, len(dimmerOffsets)):
        if (dimmerOffsets[i] > DIMMER_TIMER_MAX_TICKS/2):
            dimmerOffsets[i] -= DIMMER_TIMER_MAX_TICKS

    numZeroCrossing = len(interruptTimestamps)
    global errSlopesPlot
    # errSlopesPlotX = [DIMMER_NUM_CROSSINGS_BEFORE_CONTROL * np.array(range(0, len(errSlopes))), DIMMER_NUM_CROSSINGS_BEFORE_CONTROL * np.array(range(1, len(errSlopes))) - 1]
    errSlopesPlotX = []
    errSlopesPlotY = []

    for i in range(0, len(errSlopesPlot)):
        x0 = i*DIMMER_NUM_CROSSINGS_BEFORE_CONTROL
        # x1 = (i+1)*DIMMER_NUM_CROSSINGS_BEFORE_CONTROL - 1
        x1 = (i + 1) * DIMMER_NUM_CROSSINGS_BEFORE_CONTROL
        errSlopesPlotX.append([x0, x1])
        errSlopesPlotY.append([dimmerOffsets[x0], dimmerOffsets[x0] + DIMMER_NUM_CROSSINGS_BEFORE_CONTROL * errSlopesPlot[i]])
    errSlopesPlotX = np.array(errSlopesPlotX).transpose()
    errSlopesPlotY = np.array(errSlopesPlotY).transpose()

    plt.figure()
    axOffset = plt.gca()
    axOffset.set_title('Zero crossing offset of dimmer')
    axOffset.set_ylabel("μs")
    axOffset.plot(dimmerOffsets, '-x')
    axOffset.plot(errSlopesPlotX, errSlopesPlotY)

    plt.figure()
    axInterval = plt.gca()
    axInterval.set_title('Dimmer interval')
    axInterval.set_ylabel("μs")
    axInterval.plot(dimmerIntervals, "-x")

    # plt.plot(interruptTimestamps, dimmerTimerStartTimes, 'x')
    # plt.plot(np.array(interruptTimestamps) - np.array(dimmerTimerStartTimes), 'x')


    plt.figure()
    axInterval = plt.gca()
    axInterval.set_title('Offset slope')
    # axInterval.set_ylabel("μs")
    axInterval.plot(errSlopesPlot, "-x")

    plt.show()

main()
