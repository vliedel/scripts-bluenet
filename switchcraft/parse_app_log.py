import numpy as np
import json
import sys, os
import re
import matplotlib.pyplot as plt

"""
Parses an app log file.
For now, plots the
"""

# Matches first number on each line, posix timestamp in ms.
timePattern        = re.compile("^(\d+)")

# Matches: ANNOTATION: Normal Switchcraft
annotationPattern  = re.compile(".*ANNOTATION: (.*)")

# Matches: getPowerSamples triggeredSwitchcraft [{"samples":[357,443,534,279],"multiplier":0},{"samples":[-357,-443,-534,-279],"multiplier":0}]
switchcraftPattern = re.compile(".*getPowerSamples triggeredSwitchcraft \[{")

# Matches: "samples":[357,-443,534,279]
samplesPattern = re.compile("samples\":\[([0-9\- ,]+)\]")

def parse(fileName):
    with open(fileName, 'r') as file:
        lines = file.readlines()

        # The log is in reverse order
        lines.reverse()

        timestamp = 0
        annotation = ""
        samples = []

        for line in lines:


            match = timePattern.match(line)
            if (match):
                timestampMs = match.group(1)
                # print(timestampMs)

            match = annotationPattern.match(line)
            if (match):
                annotation = match.group(1)
                # Annotation comes after getting the data.
                if (len(samples) != 0):
                    plt.figure()
                    plt.plot(samples)
                    plt.title(fileName + "\n" + annotation)

            match = switchcraftPattern.match(line)
            if (match):
                samples = []
                # hah, have fun with the 3 lookalike words!
                samplesStrings = samplesPattern.findall(line)
                for samplesString in samplesStrings:
                    sampleStrings = samplesString.split(',')
                    for s in sampleStrings:
                        try:
                            sample = int(s)
                        except:
                            print("Invalid sample value:", s, "in line:", line)
                            exit(1)
                        samples.append(sample)


    plt.show()

parse(sys.argv[1])
