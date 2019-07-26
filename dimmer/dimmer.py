#!/usr/bin/env python3

import random
import matplotlib.pyplot as plt
import numpy as np

GRID_INTERVAL_US   = 10080
DIMMER_INTERVAL_US = 10000


ZERO_CROSSING_MISSING_CHANCE = 0.1
ZERO_CROSSING_DELAY_CHANCE = 1.0
ZERO_CROSSING_DELAY_PARETO_ALPHA = 3
ZERO_CROSSING_DELAY_PARETO_MULTIPLIER = 100
# ZERO_CROSSING_DELAY_PARETO_MULTIPLIER = 0
SIM_TIME_SECONDS = 10

ZERO_CROSSINGS = int(2 * SIM_TIME_SECONDS * 1000 * 1000 / GRID_INTERVAL_US)


def maybeRound(val):
    return int(val)
    # return val

errIntegral = 0
zeroCrossingCounter = 0
def onZeroCrossing(dimmerTimerCapture, dimmerInterval):
    target = 0
    err = target - maybeRound(dimmerTimerCapture)
    if (err > maybeRound(DIMMER_INTERVAL_US/2)):
        err -= DIMMER_INTERVAL_US
    if (err < maybeRound(-DIMMER_INTERVAL_US/2)):
        err += DIMMER_INTERVAL_US

    global errIntegral
    errIntegral += -err
    integralAbsMax = DIMMER_INTERVAL_US * 1000
    if (errIntegral > integralAbsMax):
        errIntegral = integralAbsMax
    if (errIntegral < -integralAbsMax):
        errIntegral = -integralAbsMax

    global zeroCrossingCounter
    zeroCrossingCounter += 1
    if (zeroCrossingCounter % 10 == 0):
        delta = 0
        deltaP = maybeRound(-err / maybeRound(DIMMER_INTERVAL_US / 400))
        deltaI = maybeRound(errIntegral / 1000 / maybeRound(DIMMER_INTERVAL_US / 400))
        delta = deltaP + deltaI

        limitDelta = maybeRound(DIMMER_INTERVAL_US / 120)
        if (delta > limitDelta):
            delta = limitDelta
        if (delta < -limitDelta):
            delta = -limitDelta

        newInterval = int(DIMMER_INTERVAL_US + delta)
        print("capture=", dimmerTimerCapture, " err=", err, " errIntegral=", errIntegral, " deltaP=", deltaP, " deltaI=", deltaI, " delta=", delta, " newInterval=", newInterval)
        return newInterval
    return dimmerInterval

def main():
    print(ZERO_CROSSINGS)
    t = 0
    interruptTimestamps = []
    for i in range(0, ZERO_CROSSINGS):
        timestamp = t
        if random.random() < ZERO_CROSSING_MISSING_CHANCE:
            t += GRID_INTERVAL_US
            continue
        if random.random() < ZERO_CROSSING_DELAY_CHANCE:
            delay = (random.paretovariate(ZERO_CROSSING_DELAY_PARETO_ALPHA) - 1) * ZERO_CROSSING_DELAY_PARETO_MULTIPLIER
            timestamp = t + delay
            # print(delay)
        interruptTimestamps.append(timestamp)
        t = t + GRID_INTERVAL_US
    # plt.plot(interruptTimestamps)
    diffs = np.diff(np.array(interruptTimestamps))
    # plt.figure()
    # plt.plot(diffs, 'o')

    dimmerTimerStart = 0
    dimmerInterval = DIMMER_INTERVAL_US
    dimmerTimerStartTimes = []
    dimmerTimerCaptures = []
    dimmerIntervals = []
    for zeroCrossingInterruptTime in interruptTimestamps:
        while ((dimmerTimerStart + dimmerInterval) < zeroCrossingInterruptTime):
            dimmerTimerStart += dimmerInterval
        dimmerTimerStartTimes.append(dimmerTimerStart)
        dimmerTimerCapture = zeroCrossingInterruptTime - dimmerTimerStart
        dimmerTimerCaptures.append(dimmerTimerCapture)
        dimmerIntervals.append(dimmerInterval)

        # Control action here
        dimmerInterval = onZeroCrossing(dimmerTimerCapture, dimmerInterval)


    dimmerOffsets = np.array(dimmerTimerCaptures)
    # dimmerOffsets = np.array(interruptTimestamps) - np.array(dimmerTimerStartTimes)
    for i in range(0, len(dimmerOffsets)):
        if (dimmerOffsets[i] > GRID_INTERVAL_US/2):
            dimmerOffsets[i] -= GRID_INTERVAL_US


    plt.figure()
    plt.plot(dimmerOffsets, '-x')
    plt.figure()
    plt.plot(dimmerIntervals, "-x")
    # plt.plot(interruptTimestamps, dimmerTimerStartTimes, 'x')
    # plt.plot(np.array(interruptTimestamps) - np.array(dimmerTimerStartTimes), 'x')

    plt.show()

main()
