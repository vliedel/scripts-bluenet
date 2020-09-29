#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import sys, os
from enum import Enum
import re

filePath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(filePath + '/../parse')
import parse_app_files
from PowerSampleType import *

# from ..parse import parse_app_files
# from ..parse import PowerSampleType

def main():
	fileNames = sys.argv[1:]
	for fileName in fileNames:

		# Parse file
		allTimestamps, allSamples, allMetaData = parse_app_files.parse(fileName)

		hasVoltageBuffers = False
		hasCurrentBuffers = False
		for i in range(0, len(allMetaData)):
			if allMetaData[i]["bufferType"] == BufferType.Voltage:
				hasVoltageBuffers = True
			if allMetaData[i]["bufferType"] == BufferType.Current:
				hasCurrentBuffers = True

		if hasVoltageBuffers and hasCurrentBuffers:
			fig, (ax1, ax2) = plt.subplots(2, sharex=True)
		elif hasVoltageBuffers:
			fig, ax1 = plt.subplots(1, sharex=True)
		elif hasCurrentBuffers:
			fig, ax2 = plt.subplots(1, sharex=True)

		fig.suptitle(fileName)

		for i in range(0, len(allTimestamps)):
			rms = allMetaData[i]["rms"]
			rmsCorrected = allMetaData[i]["rmsCorrected"]

			# print("\n")
			# print(allTimestamps[i])
			# print(allSamples[i])
			# print(allMetaData[i])

			print("i=", i, " rms=", rms, " rmsCorrected=", rmsCorrected)

			if allMetaData[i]["bufferType"] == BufferType.Voltage:
				ax1.plot(allTimestamps[i], allSamples[i], '.-')
				ax1.annotate("rms=" + str(rms) + "\nrmsCorrected=" + str(rmsCorrected),
				             xy=(allTimestamps[i][0], allSamples[i][0]))
			else:
				ax2.plot(allTimestamps[i], allSamples[i], '.-')
				ax2.annotate("rms=" + str(rms) + "\nrmsCorrected=" + str(rmsCorrected),
				             xy=(allTimestamps[i][0], allSamples[i][0]))

	if hasVoltageBuffers:
		ax1.set_ylabel("Voltage (V)")
		ax1.set_xlabel("Time (ms)")
	if hasCurrentBuffers:
		ax2.set_ylabel("Current (A)")
		ax2.set_xlabel("Time (ms)")
	plt.show()

main()
