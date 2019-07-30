#!/usr/bin/env python3

import random
import matplotlib.pyplot as plt
import numpy as np
from enum import Enum

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
SIM_TIME_SECONDS = 60

# Whether to round intermediate calculations.
def maybeRound(val):
    return int(val)
    # return val

DIMMER_TIMER_MAX_TICKS = 4 * DIMMER_INTERVAL_US

DIMMER_NUM_CROSSINGS_BEFORE_CONTROL = 9
DIMMER_NUM_FREQUENCY_SYNCS = 5

DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC = 10

# This function is what happens in the firmware.
errIntegral = 0
zeroCrossingCounter = 0
errHist = []
avgErrSlopes = []

errSlopesPlot = [] # For plotting

class State(Enum):
    SYNC_FREQUENCY = 1
    SYNC_START = 2
nextState = State.SYNC_FREQUENCY

dimmerSynchedIntervalMaxTicks = DIMMER_TIMER_MAX_TICKS
def onZeroCrossing(dimmerTimerCapture, dimmerMaxTicks):
    global dimmerSynchedIntervalMaxTicks
    global state
    global zeroCrossingCounter
    global errIntegral
    global errSlopesPlot
    global errHist
    global nextState

    state = nextState
    target = 0
    err = maybeRound(dimmerTimerCapture) - target
    if (err > maybeRound(DIMMER_TIMER_MAX_TICKS/2)):
        err -= DIMMER_TIMER_MAX_TICKS
    if (err < maybeRound(-DIMMER_TIMER_MAX_TICKS/2)):
        err += DIMMER_TIMER_MAX_TICKS

    if (state == State.SYNC_FREQUENCY):
        errHist.append(err)
        if (len(errHist) < DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC):
            return dimmerMaxTicks
        # avgSlope = (errHist[-1] - errHist[0]) / (len(errHist) - 1)
        # avgSlope = (avgSlope + DIMMER_TIMER_MAX_TICKS / 2) % DIMMER_TIMER_MAX_TICKS - DIMMER_TIMER_MAX_TICKS / 2
        # filteredAvgSlope = avgSlope

        # errSlopes = []
        # for i in range(1, DIMMER_NUM_CROSSINGS_BEFORE_CONTROL):
        #     slope = (errHist[i] - errHist[i-1])
        #     slope = (slope + DIMMER_TIMER_MAX_TICKS / 2) % DIMMER_TIMER_MAX_TICKS - DIMMER_TIMER_MAX_TICKS / 2
        #     errSlopes.append(slope)
        # medianSlope = np.median(np.array(errSlopes))
        # filteredAvgSlope = medianSlope

        # medianErr = np.median(errHist)
        # avgDeviation = 0
        # for i in range(0, len(errHist)):
        #     deviation = abs(errHist[i] - medianErr)
        #     avgDeviation += deviation
        # avgDeviation /= len(errHist)
        # for i in range(0, len(errHist)):
        #     deviation = abs(errHist[i] - medianErr)
        #     if (deviation > 2 * avgDeviation):
        #         errHist[i] = medianErr
        # avgSlope = (errHist[-1] - errHist[0]) / (len(errHist) - 1)
        # avgSlope = (avgSlope + DIMMER_TIMER_MAX_TICKS / 2) % DIMMER_TIMER_MAX_TICKS - DIMMER_TIMER_MAX_TICKS / 2
        # filteredAvgSlope = avgSlope

        # https://en.wikipedia.org/wiki/Theil%E2%80%93Sen_estimator
        # Needs to calculate median of ((DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC-1) * ((DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC-1) + 1) / 2) values.
        # For DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC = 10, that is the median of 45 values.
        errSlopes = []
        for i in range(0, len(errHist)):
            for j in range(i+1, len(errHist)):
                dy = (errHist[j] - errHist[i])
                dy = (dy + DIMMER_TIMER_MAX_TICKS / 2) % DIMMER_TIMER_MAX_TICKS - DIMMER_TIMER_MAX_TICKS / 2
                slope = dy / (j-i)
                errSlopes.append((slope))
        filteredAvgSlope = np.median(errSlopes)

        # https://en.wikipedia.org/wiki/Repeated_median_regression
        # This way we only need to calculate the median of (DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC - 1) values, but have to do that DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC times.
        medianSlopes = []
        for i in range(0, len(errHist)):
            errSlopes = []
            for j in range(0, len(errHist)):
                if (i == j):
                    continue
                dy = (errHist[j] - errHist[i])
                dy = (dy + DIMMER_TIMER_MAX_TICKS / 2) % DIMMER_TIMER_MAX_TICKS - DIMMER_TIMER_MAX_TICKS / 2
                slope = maybeRound(dy / (j-i))
                errSlopes.append((slope))
            medianSlopes.append(np.median(errSlopes))
        filteredAvgSlope = np.median(medianSlopes)

        avgErrSlopes.append(filteredAvgSlope)
        errHist = []
        errSlopesPlot.append(filteredAvgSlope)

        if (len(avgErrSlopes) < DIMMER_NUM_FREQUENCY_SYNCS):
            return dimmerMaxTicks
        filteredAvgSlope = np.median(avgErrSlopes)

        # Every full cycle (~20ms), the err increases by slope.
        # So the interval (half cycle, ~10ms) should be increased by half the slope.
        dimmerSynchedIntervalMaxTicks += maybeRound(filteredAvgSlope / 2)

        newDimmerMaxTicks = int(dimmerSynchedIntervalMaxTicks)
        print("capture=", dimmerTimerCapture, " err=", err, " errSlope=", filteredAvgSlope, " synchedMaxTicks=",
              dimmerSynchedIntervalMaxTicks, "newMaxTicks=", newDimmerMaxTicks)
        nextState = State.SYNC_START
        return newDimmerMaxTicks
        # return dimmerMaxTicks



    if (state == State.SYNC_START):
        errHist.append(err)
        errIntegral += err
        zeroCrossingCounter += 1
        if (zeroCrossingCounter == DIMMER_NUM_CROSSINGS_BEFORE_CONTROL):
            zeroCrossingCounter = 0
            integralAbsMax = DIMMER_TIMER_MAX_TICKS * 1000
            if (errIntegral > integralAbsMax):
                errIntegral = integralAbsMax
            if (errIntegral < -integralAbsMax):
                errIntegral = -integralAbsMax

            medianErr = np.median(errHist)

            # medianSlopes = []
            # for i in range(0, len(errHist)):
            #     errSlopes = []
            #     for j in range(0, len(errHist)):
            #         if (i == j):
            #             continue
            #         dy = (errHist[j] - errHist[i])
            #         dy = (dy + DIMMER_TIMER_MAX_TICKS / 2) % DIMMER_TIMER_MAX_TICKS - DIMMER_TIMER_MAX_TICKS / 2
            #         slope = maybeRound(dy / (j - i))
            #         errSlopes.append((slope))
            #     medianSlopes.append(np.median(errSlopes))
            # filteredAvgSlope = np.median(medianSlopes)
            #
            # calculatedCurrentErr = medianErr + (filteredAvgSlope / 2) * int(DIMMER_NUM_CROSSINGS_BEFORE_CONTROL / 2)
            # previousDelta = dimmerMaxTicks - dimmerSynchedIntervalMaxTicks
            #
            # # If the same delta is used, this is the predicted error
            # predictedErr = calculatedCurrentErr + (filteredAvgSlope / 2) * DIMMER_NUM_CROSSINGS_BEFORE_CONTROL
            #
            # deltaDelta = predictedErr / (2 * DIMMER_NUM_CROSSINGS_BEFORE_CONTROL)
            # delta = previousDelta + deltaDelta

            delta = 0
            deltaP = maybeRound(medianErr / DIMMER_TIMER_MAX_TICKS * 1000)
            deltaI = maybeRound(errIntegral / DIMMER_NUM_CROSSINGS_BEFORE_CONTROL / DIMMER_TIMER_MAX_TICKS * 2)
            # delta = deltaP + deltaI
            delta = deltaP

            limitDelta = maybeRound(DIMMER_TIMER_MAX_TICKS / 120)
            if (delta > limitDelta):
                delta = limitDelta
            if (delta < -limitDelta):
                delta = -limitDelta

            # newDimmerMaxTicks = int(DIMMER_TIMER_MAX_TICKS + delta)
            newDimmerMaxTicks = int(dimmerSynchedIntervalMaxTicks + delta)
            # newDimmerMaxTicks = int(dimmerSynchedIntervalMaxTicks)

            print("capture=", dimmerTimerCapture, " err=", err, "errIntegral=", errIntegral,
                  " deltaP=", deltaP, " deltaI=", deltaI, " delta=", delta, " synchedMaxTicks=",
                  dimmerSynchedIntervalMaxTicks, "newMaxTicks=", newDimmerMaxTicks)
            # print("capture=", dimmerTimerCapture, " err=", err, "predictedErr=", predictedErr,
            #       " deltaDelta=", deltaDelta, " delta=", delta, " synchedMaxTicks=",
            #       dimmerSynchedIntervalMaxTicks, "newMaxTicks=", newDimmerMaxTicks)

            errHist = []
            return newDimmerMaxTicks
            # return dimmerMaxTicks
    return dimmerMaxTicks




def main():
    t = 0
    interruptTimestamps = []
    interruptDelays = []
    numZeroCrossing = int(SIM_TIME_SECONDS * 1000 * 1000 / GRID_INTERVAL_US)
    for i in range(0, numZeroCrossing):
        delay = 0
        if (i % 2 == 0):
            t += GRID_INTERVAL_US
            continue
        if (random.random() < ZERO_CROSSING_MISSING_CHANCE):
            t += GRID_INTERVAL_US
            continue
        if (random.random() < ZERO_CROSSING_DELAY_CHANCE):
            delay = (random.paretovariate(ZERO_CROSSING_DELAY_PARETO_ALPHA) - 1) * ZERO_CROSSING_DELAY_PARETO_MULTIPLIER
            if (delay > ZERO_CROSSING_DELAY_MAX_US):
                delay = ZERO_CROSSING_DELAY_MAX_US
        interruptDelays.append(delay)
        timestamp = t + delay
        interruptTimestamps.append(timestamp)
        t = t + GRID_INTERVAL_US

    plotTimestamp = np.array(interruptTimestamps) / 1000 / 1000

    plt.figure()
    axDelay = plt.gca()
    axDelay.set_title("Zero crossing interrupt delay")
    axDelay.set_ylabel("μs")
    axDelay.plot(plotTimestamp, interruptDelays, 'o')

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
        errSlopesPlotX.append([plotTimestamp[x0], plotTimestamp[x1]])
        errSlopesPlotY.append([dimmerOffsets[x0], dimmerOffsets[x0] + DIMMER_NUM_CROSSINGS_BEFORE_CONTROL * errSlopesPlot[i]])
    errSlopesPlotX = np.array(errSlopesPlotX).transpose()
    errSlopesPlotY = np.array(errSlopesPlotY).transpose()

    plt.figure()
    axOffset = plt.gca()
    axOffset.set_title('Zero crossing offset of dimmer')
    axOffset.set_ylabel("μs")
    axOffset.plot(plotTimestamp, dimmerOffsets, '-x')
    axOffset.plot(errSlopesPlotX, errSlopesPlotY)

    plt.figure()
    axInterval = plt.gca()
    axInterval.set_title('Dimmer interval')
    axInterval.set_ylabel("μs")
    axInterval.plot(plotTimestamp, dimmerIntervals, "-x")

    # plt.plot(interruptTimestamps, dimmerTimerStartTimes, 'x')
    # plt.plot(np.array(interruptTimestamps) - np.array(dimmerTimerStartTimes), 'x')


    plt.figure()
    axInterval = plt.gca()
    axInterval.set_title('Offset slope')
    # axInterval.set_ylabel("μs")
    axInterval.plot(errSlopesPlot, "-x")

    plt.show()

main()
