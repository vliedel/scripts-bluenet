import numpy as np
import json
import re
import sys, os

"""
Parses a file recorded with record-voltage.py
Returns a list of consecutive (uninterrupted) timestamps and samples.
"""

# Matches: stoneUID:24:[{"samples":[1355,1289,1236,1419],"multiplier":0,"offset":0,"sampleInterval":200,"delay":0,"timestamp":1596100484,"count":100,"index":0,"type":1},{"samples":[1354,1286,1236,1173,1425],"multiplier":0,"offset":0,"sampleInterval":200,"delay":0,"timestamp":1596100484,"count":100,"index":1,"type":1}]
samplesPattern = re.compile("stoneUID:\d+:(\[{.*)")

def parse(fileName):
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

    timestampMs = 0

    allConsecutiveSamples = []
    consecutiveSamples = []

    allConsecutiveTimestamps = []
    consecutiveTimestamps = []

    with open(fileName, 'r') as file:
        lines = file.readlines()
        for line in lines:
            match = samplesPattern.match(line)
            if (match):
                try:
                    samplesJson = json.loads(match.group(1))
                    for i in range(0, len(samplesJson)):
                        samples = samplesJson[i]["samples"]
                        sampleInterval = samplesJson[i]["sampleInterval"] / 1000.0

                        timestampsMs = np.array(range(0, len(samples))) * sampleInterval + timestampMs
                        timestampMs += len(samples) * sampleInterval

                        consecutiveSamples.extend(samples)
                        consecutiveTimestamps.extend(timestampsMs)

                    allConsecutiveSamples.append(consecutiveSamples)
                    allConsecutiveTimestamps.append(consecutiveTimestamps)
                    consecutiveSamples = []
                    consecutiveTimestamps = []
                except:
                    print("Invalid data in line:", line)
                    exit(1)



    if (len(consecutiveSamples)):
        allConsecutiveSamples.append(consecutiveSamples)
        allConsecutiveTimestamps.append(consecutiveTimestamps)

    return allConsecutiveTimestamps, allConsecutiveSamples
