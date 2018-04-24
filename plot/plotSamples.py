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

def main():
	fileName = sys.argv[1]
	dirPath = os.getcwd()
	# f = open(dirPath + '/' + fileName, 'r')
	f = open(fileName, 'r')
	data = json.load(f)
	for entry in data:
		# print(entry)
		samples =   entry['samples']
		timestamp = entry['timestamp']
		timestampMs = timestamp * 1000.0 / RTC_CLOCK_FREQ
		timestampsMs = np.array(range(0,len(samples))) * SAMPLE_TIME_US / 1000.0 + timestampMs
		global allSamples
		allSamples.extend(samples)
		global allTimestamps
		allTimestamps.extend(timestampsMs)
		plt.plot(timestampsMs, samples, '-o')
	# plt.plot(allTimestamps, allSamples, '-o')
	plt.show()

main()