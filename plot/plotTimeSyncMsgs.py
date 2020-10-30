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

# matches: [2020-10-30 18:04:27.107] [rce/src/time/cs_SystemTime.cpp : 418  ] onTimeSyncMsg msg: {id=19 version=29 s=1604081066 ms=267} cur: {id=19 version=29 s=1604081066 ms=272}
timeSyncMsgPattern = re.compile("^\[([^\]]+)\] .* onTimeSyncMsg msg: \{id=(\d+) version=\d+ s=(\d+) ms=(\d+)")

# format of laptop timestamps
timeFormat = "%Y-%m-%d %H:%M:%S.%f"

fileName = sys.argv[1]
with open(fileName, 'r') as file:
	lines = file.readlines()

	laptopTimes = {}
	laptopDateTimes = {}
	stoneTimes = {}

	for line in lines:
		match = timeSyncMsgPattern.match(line)
		if match:
			laptopTimeStr = match.group(1)
			laptopDateTime = datetime.datetime.strptime(laptopTimeStr, timeFormat)
			laptopTimestamp = laptopDateTime.timestamp()

			stoneId = int(match.group(2))
			stoneTimestamp = int(match.group(3)) + int(match.group(4)) / 1000.0
			print(line)
			print(f"laptopTime={laptopTimestamp} stoneId={stoneId} stoneTime={stoneTimestamp}")

			if stoneId not in stoneTimes:
				stoneTimes[stoneId] = []
				laptopTimes[stoneId] = []
				laptopDateTimes[stoneId] = []

			stoneTimes[stoneId].append(stoneTimestamp)
			laptopDateTimes[stoneId].append(laptopDateTime)
			laptopTimes[stoneId].append(laptopTimestamp)

	for stoneId in stoneTimes.keys():
		timeDiff = np.array(laptopTimes[stoneId]) - np.array(stoneTimes[stoneId])

		plt.figure(1)
		plt.plot(laptopTimes[stoneId], stoneTimes[stoneId], '.-', label=stoneId)

		plt.figure(2)
		plt.plot(laptopDateTimes[stoneId], timeDiff, '.-', label=stoneId)

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