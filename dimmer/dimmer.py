#!/usr/bin/env python3

import random
import matplotlib.pyplot as plt
import numpy as np
from enum import Enum

# Starting interval of the dimmer in μs.
DIMMER_INTERVAL_US = 10000

# Starting interval of zero crossings of the grid, in μs.
# GRID_INTERVAL_US   = 10080
GRID_INTERVAL_US   = 9920

# Minimum interval of zero crossings of the grid in μs.
GRID_INTERVAL_MIN_US = 9900

# Maximum interval of zero crossings of the grid in μs.
GRID_INTERVAL_MAX_US = 10100

# For how long the grid interval remain the same at least in μs.
GRID_INTERVAL_MIN_STABLE_TIME = 20*1000*1000

# Max step of grid interval in μs.
GRID_INTERVAL_MAX_STEP_US = 20


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
SIM_TIME_SECONDS = 600

# Whether to round intermediate calculations.
def maybeRound(val):
    return int(val)
    # return val


DIMMER_TIMER_MAX_TICKS = 4 * DIMMER_INTERVAL_US

DIMMER_NUM_CROSSINGS_BEFORE_CONTROL = 9
DIMMER_NUM_FREQUENCY_SYNCS = 5

DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC = 10

DIMMER_NUM_START_SYNCS_BETWEEN_FREQ_SYNC = 100

# This function is what happens in the firmware.
errIntegral = 0
zeroCrossingCounter = 0
errHist = []
avgErrSlopes = []
numStartSyncs = 0

errSlopesPlot = [] # For plotting

class State(Enum):
    SYNC_FREQUENCY = 1
    SYNC_START = 2
nextState = State.SYNC_FREQUENCY

dimmerSynchedIntervalMaxTicks = DIMMER_TIMER_MAX_TICKS
def onZeroCrossing(plotIndex, dimmerTimerCapture, dimmerMaxTicks):
    global dimmerSynchedIntervalMaxTicks
    global state
    global zeroCrossingCounter
    global errIntegral
    global errSlopesPlot
    global errHist
    global nextState
    global numStartSyncs

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

        # # https://en.wikipedia.org/wiki/Theil%E2%80%93Sen_estimator
        # # Needs to calculate median of ((DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC-1) * ((DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC-1) + 1) / 2) values.
        # # For DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC = 10, that is the median of 45 values.
        # errSlopes = []
        # for i in range(0, len(errHist)):
        #     for j in range(i+1, len(errHist)):
        #         dy = (errHist[j] - errHist[i])
        #         dy = (dy + DIMMER_TIMER_MAX_TICKS / 2) % DIMMER_TIMER_MAX_TICKS - DIMMER_TIMER_MAX_TICKS / 2
        #         slope = dy / (j-i)
        #         errSlopes.append((slope))
        # filteredAvgSlope = np.median(errSlopes)

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
        errHist.clear()
        errSlopesPlot.append([plotIndex, filteredAvgSlope])

        if (len(avgErrSlopes) < DIMMER_NUM_FREQUENCY_SYNCS):
            return dimmerMaxTicks
        filteredAvgSlope = np.median(avgErrSlopes)

        # Every full cycle (~20ms), the err increases by slope.
        # So the interval (half cycle, ~10ms) should be increased by half the slope.
        dimmerSynchedIntervalMaxTicks = dimmerMaxTicks + maybeRound(filteredAvgSlope / 2)

        newDimmerMaxTicks = int(dimmerSynchedIntervalMaxTicks)
        print("capture=", dimmerTimerCapture, " err=", err, " errSlope=", filteredAvgSlope, " synchedMaxTicks=",
              dimmerSynchedIntervalMaxTicks, "newMaxTicks=", newDimmerMaxTicks)
        avgErrSlopes.clear()
        nextState = State.SYNC_START
        return newDimmerMaxTicks


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

            deltaP = maybeRound(medianErr / DIMMER_TIMER_MAX_TICKS * 1000)
            deltaI = maybeRound(errIntegral / DIMMER_NUM_CROSSINGS_BEFORE_CONTROL / DIMMER_TIMER_MAX_TICKS * 2)
            delta = deltaP + deltaI
            # delta = deltaP

            limitDelta = maybeRound(DIMMER_TIMER_MAX_TICKS / 120)
            if (delta > limitDelta):
                delta = limitDelta
            if (delta < -limitDelta):
                delta = -limitDelta

            newDimmerMaxTicks = int(dimmerSynchedIntervalMaxTicks + delta)
            # newDimmerMaxTicks = int(dimmerSynchedIntervalMaxTicks)

            print("capture=", dimmerTimerCapture, " err=", err, "errIntegral=", errIntegral,
                  " deltaP=", deltaP, " deltaI=", deltaI, " delta=", delta, " synchedMaxTicks=",
                  dimmerSynchedIntervalMaxTicks, "newMaxTicks=", newDimmerMaxTicks)
            # print("capture=", dimmerTimerCapture, " err=", err, "predictedErr=", predictedErr,
            #       " deltaDelta=", deltaDelta, " delta=", delta, " synchedMaxTicks=",
            #       dimmerSynchedIntervalMaxTicks, "newMaxTicks=", newDimmerMaxTicks)

            if (numStartSyncs == DIMMER_NUM_START_SYNCS_BETWEEN_FREQ_SYNC):
                numStartSyncs = 0
                errIntegral = 0
                nextState = State.SYNC_FREQUENCY
            else:
                numStartSyncs += 1
            errHist = []
            return newDimmerMaxTicks
    return dimmerMaxTicks




def main():
    t = 0
    i = 0
    dimmerTimerStartTimestamp = 0
    gridSimilarIntervalUS = 0
    gridInterval = GRID_INTERVAL_US
    dimmerInterval = DIMMER_INTERVAL_US
    zeroCrossingTimestamps = []
    interruptTimestamps = []
    interruptDelays = []
    gridIntervals = []
    dimmerTimerStartTimes = []
    dimmerTimerCaptures = []
    dimmerIntervals = []
    dimmerOffsets = []
    # numZeroCrossing = int(SIM_TIME_SECONDS * 1000 * 1000 / GRID_INTERVAL_US)
    # for i in range(0, numZeroCrossing):
    while (t < SIM_TIME_SECONDS * 1000 * 1000):
        if (i % 2 == 0):
            # We only get interrupts for upwards (or only downwards) zero crossings.
            pass
        elif (random.random() < ZERO_CROSSING_MISSING_CHANCE):
            # Sometimes a zero crossing interrupt is skipped because there was too much delay, or the ADC restarted.
            pass
        else:
            delay = 0
            if (random.random() < ZERO_CROSSING_DELAY_CHANCE):
                delay = (random.paretovariate(ZERO_CROSSING_DELAY_PARETO_ALPHA) - 1) * ZERO_CROSSING_DELAY_PARETO_MULTIPLIER
                if (delay > ZERO_CROSSING_DELAY_MAX_US):
                    delay = ZERO_CROSSING_DELAY_MAX_US
            interruptTimestamp = t + delay

            # Calculate the dimmer timer value at the moment of the interrupt.
            while ((dimmerTimerStartTimestamp + dimmerInterval) < interruptTimestamp):
                dimmerTimerStartTimestamp += dimmerInterval
            dimmerTimerCapture = 4 * (interruptTimestamp - dimmerTimerStartTimestamp)

            # Store value for plotting.
            dimmerIntervals.append(dimmerInterval)

            # Calculate the offset of the dimmer timer start with the grid zero crossing.
            dimmerTimerOffset = t - dimmerTimerStartTimestamp
            if (dimmerTimerOffset > gridInterval / 2):
                dimmerTimerOffset -= gridInterval

            # Control action: change dimmer interval.
            dimmerInterval = onZeroCrossing(len(zeroCrossingTimestamps), dimmerTimerCapture, 4 * dimmerInterval) / 4

            # Store values for plotting
            dimmerTimerStartTimes.append(dimmerTimerStartTimestamp)
            if (dimmerTimerCapture > DIMMER_TIMER_MAX_TICKS / 2):
                dimmerTimerCapture -= DIMMER_TIMER_MAX_TICKS
            dimmerTimerCaptures.append(dimmerTimerCapture)
            dimmerOffsets.append(dimmerTimerOffset)
            interruptDelays.append(delay)
            zeroCrossingTimestamps.append(t)
            interruptTimestamps.append(interruptTimestamp)
            gridIntervals.append(gridInterval)

        # Maybe change the grid interval
        if (gridSimilarIntervalUS > GRID_INTERVAL_MIN_STABLE_TIME):
            gridInterval += random.randint(-GRID_INTERVAL_MAX_STEP_US, GRID_INTERVAL_MAX_STEP_US)
            if (gridInterval > GRID_INTERVAL_MAX_US):
                gridInterval = GRID_INTERVAL_MAX_US
            if (gridInterval < GRID_INTERVAL_MIN_US):
                gridInterval = GRID_INTERVAL_MIN_US
            gridSimilarIntervalUS = 0
        else:
            gridSimilarIntervalUS += gridInterval
        i += 1
        t = t + gridInterval




    plotTimestamp = np.array(zeroCrossingTimestamps) / 1000 / 1000

    numZeroCrossing = len(interruptTimestamps)
    global errSlopesPlot
    # errSlopesPlotX = [DIMMER_NUM_CROSSINGS_BEFORE_CONTROL * np.array(range(0, len(errSlopes))), DIMMER_NUM_CROSSINGS_BEFORE_CONTROL * np.array(range(1, len(errSlopes))) - 1]
    errSlopesPlotX = []
    errSlopesPlotY = []

    for i in range(0, len(errSlopesPlot)):
        index = errSlopesPlot[i][0]
        slope = errSlopesPlot[i][1]
        # x0 = index * DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC
        # x1 = (index + 1) * DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC
        x0 = index - DIMMER_NUM_SAMPLES_FOR_FREQ_SYNC + 1
        x1 = index
        errSlopesPlotX.append([plotTimestamp[x0], plotTimestamp[x1]])
        errSlopesPlotY.append([dimmerTimerCaptures[x0], dimmerTimerCaptures[x0] + DIMMER_NUM_CROSSINGS_BEFORE_CONTROL * slope])
    errSlopesPlotX = np.array(errSlopesPlotX).transpose()
    errSlopesPlotY = np.array(errSlopesPlotY).transpose()

    plt.figure()
    axDelay = plt.gca()
    axDelay.set_title("Zero crossing interrupt delay")
    axDelay.set_ylabel("μs")
    axDelay.plot(plotTimestamp, interruptDelays, 'o')

    plt.figure()
    axCapture = plt.gca()
    axCapture.set_title('Timer value of dimmer at zero crossing interrupt')
    axCapture.set_ylabel("ticks")
    axCapture.set_xlabel("time (s)")
    axCapture.plot(plotTimestamp, dimmerTimerCaptures, '-')
    axCapture.plot(errSlopesPlotX, errSlopesPlotY)

    plt.figure()
    axOffset = plt.gca()
    axOffset.set_title('Offset of dimmer interval start to zero crossing')
    axOffset.set_ylabel("offset (μs)")
    axOffset.set_xlabel("time (s)")
    axOffset.plot([plotTimestamp[0], plotTimestamp[-1]], [0, 0], '--k')
    axOffset.plot(plotTimestamp, dimmerOffsets, '-')
    axOffset.plot(errSlopesPlotX, errSlopesPlotY)


    plt.figure()
    axInterval = plt.gca()
    axInterval.set_title('Dimmer interval')
    axInterval.set_ylabel("μs")
    axInterval.set_xlabel("time (s)")
    axInterval.plot(plotTimestamp, gridIntervals, '--k')
    axInterval.plot(plotTimestamp, dimmerIntervals, "-")

    plt.figure()
    axInterval = plt.gca()
    axInterval.set_title('Error slopes')
    # axInterval.set_ylabel("μs")
    axInterval.set_xlabel("time (s)")

    errSlopesPlotX = []
    errSlopesPlotY = []
    for i in range(0, len(errSlopesPlot)):
        index = errSlopesPlot[i][0]
        slope = errSlopesPlot[i][1]
        errSlopesPlotX.append(plotTimestamp[index])
        errSlopesPlotY.append(slope)
    axInterval.plot(errSlopesPlotX, errSlopesPlotY, 'x')

    plt.show()

main()
