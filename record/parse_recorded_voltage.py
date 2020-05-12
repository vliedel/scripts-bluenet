import numpy as np
import json
import sys, os

"""
Parses a file recorded with record-voltage.py
Returns a list of consecutive (uninterrupted) timestamps and samples. 
"""

def parse(fileName):
    # Config
    RTC_CLOCK_FREQ = 32768
    MAX_RTC_COUNTER_VAL = 0x00FFFFFF
    SAMPLE_TIME_US = 200

    # Some data was recorded with 10bit ADC resolution, instead of 12bit.
    # Enabling this will change the range of the data if it's never outside the 10 bit range.
    FIX_10_BIT_DATA = True

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

    for entry in data:
        if ('restart' in entry):
            restarted = True
        elif ('uartNoise' in entry):
            uartNoise = True
        elif ('samples' in entry):
            buffer = entry['samples']

            # HACK: Some data was recorded with 10bit ADC resolution, instead of 12bit
            if (FIX_10_BIT_DATA and max(buffer) < 1024 and min(buffer) > -1024):
                for k in range(0, len(buffer)):
                    buffer[k] *= 4

            timestamp = entry['timestamp']
            timestamps.append(timestamp)
            timestampMs = timestamp * 1000.0 / RTC_CLOCK_FREQ
            timestampsMs = np.array(range(0, len(buffer))) * SAMPLE_TIME_US / 1000.0 + timestampMs

            if (restarted or uartNoise):
                if (len(consecutiveBuffers)):
                    # Current buffer is not directly following previous buffer.
                    allConsecutiveBuffers.append(consecutiveBuffers)
                    allConsecutiveTimestamps.append(consecutiveTimestamps)
                    consecutiveBuffers = []
                    consecutiveTimestamps = []

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

    f.close()

    if (len(consecutiveBuffers)):
        allConsecutiveBuffers.append(consecutiveBuffers)
        allConsecutiveTimestamps.append(consecutiveTimestamps)

    return allConsecutiveTimestamps, allConsecutiveBuffers