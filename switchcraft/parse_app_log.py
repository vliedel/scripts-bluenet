import numpy as np
import json
import sys, os
import re
import matplotlib.pyplot as plt
import json

"""
Parses an app log file.
For now, plots the
"""

# Matches first number on each line, posix timestamp in ms.
timePattern        = re.compile("^(\d+)")

# Matches: ANNOTATION: Normal Switchcraft
annotationPattern  = re.compile(".*ANNOTATION: (.*)")

# Matches: getPowerSamples triggeredSwitchcraft [{"samples":[357,443,534,279],"multiplier":0},{"samples":[-357,-443,-534,-279],"multiplier":0}]
switchcraftPattern = re.compile(".*getPowerSamples (triggered|missed)Switchcraft (\[{.*)")

def parse(fileName):
    with open(fileName, 'r') as file:
        lines = file.readlines()

        # The log is in reverse order
#        lines.reverse()

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
                try:
                    samplesJson = json.loads(match.group(2))
                    for i in range(0, len(samplesJson)):
                        samples.extend(samplesJson[i]["samples"])
                except:
                    print("Invalid data in line:", line)
                    exit(1)

    plt.show()

parse(sys.argv[1])
