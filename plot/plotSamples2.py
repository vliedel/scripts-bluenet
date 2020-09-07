#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import sys, os
from enum import Enum
import re

sys.path.append('../record')
import parse_recorded_voltage
import parse_app_files

class PowerSampleType(Enum):
	TriggeredSwitchcraft = 0
	NonTriggeredSwitchcraft = 1
	Filtered = 2
	Unfiltered = 3
	SoftFuse = 4

TriggeredSwitchcraftPattern = re.compile(".*power-samples-switchcraft-(true|false)-positive.*")
NonTriggeredSwitchcraftPattern = re.compile(".*power-samples-switchcraft-(true|false)-negative.*")
FilteredPattern = re.compile(".*power-samples-filteredData.*")
UnfilteredPattern = re.compile(".*power-samples-unfilteredData.*")
SoftFusePattern = re.compile(".*power-samples-softFuseData.*")


def main():
	fileNames = sys.argv[1:]
	for fileName in fileNames:

		samplesType = PowerSampleType.TriggeredSwitchcraft
		if (TriggeredSwitchcraftPattern.match(fileName)):
			samplesType = PowerSampleType.TriggeredSwitchcraft
		elif (NonTriggeredSwitchcraftPattern.match(fileName)):
			samplesType = PowerSampleType.NonTriggeredSwitchcraft
		elif (FilteredPattern.match(fileName)):
			samplesType = PowerSampleType.Filtered
		elif (UnfilteredPattern.match(fileName)):
			samplesType = PowerSampleType.Unfiltered
		elif (SoftFusePattern.match(fileName)):
			samplesType = PowerSampleType.SoftFuse

		voltageAndCurrent = True
		if (samplesType == PowerSampleType.TriggeredSwitchcraft) \
				or (samplesType == PowerSampleType.NonTriggeredSwitchcraft) \
				or (samplesType == PowerSampleType.SoftFuse):
			voltageAndCurrent = False

		if voltageAndCurrent:
			fig, (ax1, ax2) = plt.subplots(2, sharex=True)
		else:
			fig, ax1 = plt.subplots(1, sharex=True)
		fig.suptitle(fileName)

		# Parse file
		if (fileName.split('.')[-1] == 'json'):
			allTimestamps, allSamples = parse_recorded_voltage.parse(fileName, filterTimeJumps=False)
		else:
			allTimestamps, allSamples = parse_app_files.parse(fileName)

		if not voltageAndCurrent:
			for i in range(0, len(allTimestamps)):
				ax1.plot(allTimestamps[i], allSamples[i], '.-')

		else:
			for i in range(0, len(allTimestamps)):
				ax1.plot(allTimestamps[i][0:100], allSamples[i][0:100], '.-')
				ax2.plot(allTimestamps[i][0:100], allSamples[i][100:200], '.-')

	plt.show()

main()
