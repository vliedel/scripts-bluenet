#!/usr/bin/python3

import matplotlib.pyplot as plt
import numpy as np
import json
import sys, os

# Config
RTC_CLOCK_FREQ = 32768
MAX_RTC_COUNTER_VAL = 0x00FFFFFF
SAMPLE_TIME_US = 200

allSamples = []
allTimestamps = []
restartTimestamps = []
firstSamplesFound = False

def main():
	fileNames = sys.argv[1:]
	dirPath = os.getcwd()

	for fileName in fileNames:
		global allSamples
		global allTimestamps
		global restartTimestamps
		global firstSamplesFound

		plt.figure()
		# f = open(dirPath + '/' + fileName, 'r')
		f = open(fileName, 'r')
		data = json.load(f)
		for entry in data:
			# print(entry)
			if ('samples' in entry):
				firstSamplesFound = True
				samples =   entry['samples']
				timestamp = entry['timestamp']
				timestampMs = timestamp * 1000.0 / RTC_CLOCK_FREQ
				timestampsMs = np.array(range(0,len(samples))) * SAMPLE_TIME_US / 1000.0 + timestampMs
				allSamples.extend(samples)
				allTimestamps.extend(timestampsMs)
				# plt.plot(timestampsMs, samples, '.')
			if ('restart' in entry):
				if (firstSamplesFound):
					restartTimestamps.append(timestampsMs[-1])
		plt.plot(allTimestamps, allSamples)
		plt.plot(restartTimestamps, [0]*len(restartTimestamps), 'x')
		plt.title(fileName)
	plt.show()

main()