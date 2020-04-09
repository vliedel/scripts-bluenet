#!/usr/bin/python3


import matplotlib.pyplot as plt
import matplotlib.dates as pltDates
import numpy as np
import sys, os
import time, datetime
import re




def main():
    # [2019-01-03 12:09:50.723]
    timestampFormat = "%Y-%m-%d %H:%M:%S.%f"
    patternTime = re.compile("\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d\.\d+")
    patternRssi = re.compile("rssi=(-?\d+)")


    fileName = sys.argv[1]
    dirPath = os.getcwd()

    posixTimestamps=[]
    timestamps=[]
    rssis=[]

    f = open(fileName, 'r')
    for line in f:
        #print(line)
        # match = patternTime.match(line) # Match only searches beginning of string
        match = patternTime.search(line)
        if (match):
            # In seconds, inverse of time.localtime(..)
            # timestamp = time.mktime(datetime.datetime.strptime(match.group(0), timestampFormat).timetuple())
            timestamp = datetime.datetime.strptime(match.group(0), timestampFormat)
            print(match.group(0), timestamp)
            match = patternRssi.search(line)
            if match:
                print(match.group(0), match.group(1))
                rssi = int(match.group(1))
                timestamps.append(timestamp)
                posixTimestamps.append(timestamp.timestamp())
                rssis.append(rssi)


    dts = np.diff(posixTimestamps)
    plt.figure()
    plt.plot(dts, '.')

    plt.figure()
    plt.plot(timestamps, rssis, '.')

    plt.show()

main()