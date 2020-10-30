#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import sys, os
import re
import datetime

# matches: [2020-10-30 12:55:13.349] [rce/src/time/cs_SystemTime.cpp : 349  ] updateRootTimeStamp s=2524 ms=215
timePattern = re.compile("^\[([^\]]+)\] .* updateRootTimeStamp s=(\d+) ms=(\d+)")

# matches: [2020-10-30 15:40:39.680] [rce/src/time/cs_SystemTime.cpp : 334  ] setRootTimeStamp, posix=67 ms=844 version=0 id=209
timeSetPattern = re.compile("^\[([^\]]+)\] .* setRootTimeStamp, posix=(\d+) ms=(\d+)")

# format of laptop timestamps
timeFormat = "%Y-%m-%d %H:%M:%S.%f"

for fileName in sys.argv[1:]:
	with open(fileName, 'r') as file:
		lines = file.readlines()

		laptopTimes = []
		laptopDateTimes = []
		stoneTimes = []

		for line in lines:
			match = timePattern.match(line)
			if not match:
				match = timeSetPattern.match(line)

			if match:
				laptopTimeStr = match.group(1)
				laptopDateTime = datetime.datetime.strptime(laptopTimeStr, timeFormat)
				laptopTimestamp = laptopDateTime.timestamp()

				stoneTimestamp = int(match.group(2)) + int(match.group(3)) / 1000.0
				print(line)
				print(f"laptopTime={laptopTimestamp} stoneTime={stoneTimestamp}")

				laptopDateTimes.append(laptopDateTime)
				laptopTimes.append(laptopTimestamp)
				stoneTimes.append(stoneTimestamp)

		# laptopTimes = np.array(laptopTimes) - laptopTimes[0]
		# stoneTimes = np.array(stoneTimes) - stoneTimes[0]

		timeDiff = np.array(laptopTimes) - np.array(stoneTimes)

		plt.figure(1)
		plt.plot(laptopTimes, stoneTimes, '.-', label=fileName)


		plt.figure(2)
		plt.plot(laptopDateTimes, timeDiff, '.-', label=fileName)

plt.figure(1)
# plt.title(fileName)
plt.xlabel("laptop timestamp (s)")
plt.ylabel("stone timestamp (s)")
plt.legend()

plt.figure(2)
# plt.title(fileName)
plt.xlabel("laptop time")
plt.ylabel("time diff (s)")
plt.legend()

plt.show()