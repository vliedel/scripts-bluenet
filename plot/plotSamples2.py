#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import sys, os
from enum import Enum
import re


# from ..record import parse_recorded_voltage
# from ..record import parse_app_files
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

currentMultiplier = 0.0045
voltageMultiplier = 0.2

def calcCurrentOrVoltageRms(samples, multiplier):
	zero = calcZero(samples)
	rms = calcRms(samples - zero, samples - zero)
	rms *= multiplier
	return rms

def calcRms(samples1, samples2, square=True):
	rms = 0.0
	for i in range(0, len(samples1)):
		rms += samples1[i] * samples2[i]
	rms /= len(samples1)
	if (square):
		return np.sqrt(rms)
	else:
		return rms

def calcZero(samples):
	return np.mean(samples)

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
		print("samplesType:", samplesType.name)

		if voltageAndCurrent:
			fig, (ax1, ax2) = plt.subplots(2, sharex=True)
			ax1.set_ylabel("Voltage (ADC value)")
			ax1.set_xlabel("Time (ms)")
			ax2.set_ylabel("Current (ADC value)")
			ax2.set_xlabel("Time (ms)")
		else:
			fig, ax1 = plt.subplots(1, sharex=True)
			ax1.set_ylabel("ADC value")
			ax1.set_xlabel("Time (ms)")
		fig.suptitle(fileName)

		# Parse file
		if (fileName.split('.')[-1] == 'json'):
			allTimestamps, allSamples = parse_recorded_voltage.parse(fileName, filterTimeJumps=False)
		else:
			allTimestamps, allSamples = parse_app_files.parse(fileName)

		if not voltageAndCurrent:
			for i in range(0, len(allTimestamps)):
				ax1.plot(allTimestamps[i], allSamples[i], '.-')
				multiplier = voltageMultiplier
				if (samplesType == PowerSampleType.SoftFuse):
					multiplier = currentMultiplier
				rms = calcCurrentOrVoltageRms(allSamples[i], multiplier)
				print("i=", i, " rms=", rms)

		else:
			for i in range(0, len(allTimestamps)):
				ax1.plot(allTimestamps[i][0:100], allSamples[i][0:100], '.-')
				ax2.plot(allTimestamps[i][0:100], allSamples[i][100:200], '.-')
				voltageRms = calcCurrentOrVoltageRms(allSamples[i][0:100], voltageMultiplier)
				currentRms = calcCurrentOrVoltageRms(allSamples[i][100:200], currentMultiplier)
				print("i=", i, " Vrms=", voltageRms, " Irms=", currentRms)

	plt.show()

main()
