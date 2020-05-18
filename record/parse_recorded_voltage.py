import numpy as np
import json
import sys, os

"""
Parses a file recorded with record-voltage.py
Returns a list of consecutive (uninterrupted) timestamps and samples.
"""

def parse(fileName, filterTimeJumps=True, fix10BitData=True):
    """
    Parses a file recorded with record-voltage.py
    Returns a list of consecutive (uninterrupted) timestamps and samples.

    :param fileName:        Name of the file to parse.
    :param filterTimeJumps: True to consider curves with a time jump between them as not consecutive.
    :param fix10BitData:    Some data was recorded with 10bit ADC resolution, instead of 12bit.
                            Enabling this will change the range of the data if it's never outside the 10 bit range.

    :return: A list of consecutive (uninterrupted) timestamps and samples in the form:
             ([[t0, t1, ... , tN], [t0, t1, ... , tM], ...], [[y0, y1, ... , yN], [y0, y1, ... , yM], ...])
    """
    # Config
    RTC_CLOCK_FREQ = 32768
    MAX_RTC_COUNTER_VAL = 0x00FFFFFF
    SAMPLE_TIME_US = 200

    # Max deviation of sample time, before considering it a time jump
    SAMPLE_TIME_US_MAX_DEVIATION = 20

    f = open(fileName, 'r')
    data = json.load(f)

    i = 0

    allConsecutiveBuffers = []
    consecutiveBuffers = []
    allConsecutiveTimestamps = []
    consecutiveTimestamps = []

    allBuffers = []
    allTimestamps = []
    timestamps = []  # List of raw timestamps of all buffers
    timestampDiffs = [0]  # List of timestamp diff between buffers
    restarted = True
    restartTimestampsMs = []
    uartNoise = False
    uartNoiseTimestampsMs = []
    timestampDiffMs = 0

    timeJump = False
    prevLastTimestamp = None

    for entry in data:
        if ('restart' in entry):
            restarted = True
        elif ('uartNoise' in entry):
            uartNoise = True
        elif ('samples' in entry):
            buffer = entry['samples']

            # HACK: Some data was recorded with 10bit ADC resolution, instead of 12bit
            if (fix10BitData and max(buffer) < 1024 and min(buffer) > -1024):
                for k in range(0, len(buffer)):
                    buffer[k] *= 4

            timestamp = entry['timestamp']
            timestamps.append(timestamp)
            timestampMs = timestamp * 1000.0 / RTC_CLOCK_FREQ
            timestampsMs = np.array(range(0, len(buffer))) * SAMPLE_TIME_US / 1000.0 + timestampMs

            timeJump = False
            if (prevLastTimestamp is not None):
                dt = timestampsMs[0] - prevLastTimestamp
                dtMin = (SAMPLE_TIME_US - SAMPLE_TIME_US_MAX_DEVIATION) / 1000.0
                dtMax = (SAMPLE_TIME_US + SAMPLE_TIME_US_MAX_DEVIATION) / 1000.0
#                print("dt=", dt, "dtMax=", dtMax, "dtMin=", dtMin)
                if (dtMin > dt or dt > dtMax):
                    print("time jump of", dt - SAMPLE_TIME_US/1000.0, "ms")
                    timeJump = True
            prevLastTimestamp = timestampsMs[-1]

            if (restarted or uartNoise or (filterTimeJumps and timeJump)):
                if (len(consecutiveBuffers)):
                    # Current buffer is not directly following previous buffer.
                    allConsecutiveBuffers.append(consecutiveBuffers)
                    allConsecutiveTimestamps.append(consecutiveTimestamps)
                    consecutiveBuffers = []
                    consecutiveTimestamps = []
            else:
                if (len(consecutiveBuffers)):
                    # Assume the first sample is exactly "sample time" after the last sample of the previous buffer.
                    print("timestampMs=", timestampMs, " corrected=", consecutiveTimestamps[-1] + SAMPLE_TIME_US / 1000.0)
                    timestampMs = consecutiveTimestamps[-1] + SAMPLE_TIME_US / 1000.0
                    timestampsMs = np.array(range(0, len(buffer))) * SAMPLE_TIME_US / 1000.0 + timestampMs

            consecutiveBuffers.extend(buffer)
            consecutiveTimestamps.extend(timestampsMs)



            if i > 0:
                timestampDiff = (timestamps[-1] - timestamps[-2]) & MAX_RTC_COUNTER_VAL
                timestampDiffs.append(timestampDiff)
                timestampDiffMs = timestampDiff * 1000.0 / RTC_CLOCK_FREQ

            if (uartNoise and timestampDiffMs > 40):
                restarted = True

            if (restarted):
                restartTimestampsMs.append(timestampMs)
                restarted = False

            if (uartNoise):
                uartNoiseTimestampsMs.append(timestampMs)
                uartNoise = False

            i += 1
            allBuffers.append(buffer)
            allTimestamps.append(timestampsMs)
            # if i > 3:
            #     break

    f.close()

    if (len(consecutiveBuffers)):
        allConsecutiveBuffers.append(consecutiveBuffers)
        allConsecutiveTimestamps.append(consecutiveTimestamps)

    return allConsecutiveTimestamps, allConsecutiveBuffers