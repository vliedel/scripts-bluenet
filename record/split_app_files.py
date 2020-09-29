#!/usr/bin/env python3

import sys, os
import re
import json
from enum import Enum

samplesPattern = re.compile("stoneUID:(\d+):(\[{.*)")

class PowerSampleType(Enum):
	TriggeredSwitchcraft = 0
	NonTriggeredSwitchcraft = 1
	Filtered = 2
	Unfiltered = 3
	SoftFuse = 4


# True positive and false negative should be a triggered switchcraft
triggeredSwitchcraftPattern = re.compile("power-samples-switchcraft-(true-positive|false-negative)")

# True negative and false positive should be a non-triggered switchcraft
nonTriggeredSwitchcraftPattern = re.compile("power-samples-switchcraft-(true-negative|false-positive)")

filteredPattern = re.compile("power-samples-filteredData")
unfilteredPattern = re.compile("power-samples-unfilteredData")
softfusePattern = re.compile("power-samples-softFuseData")

def main():
	fileName = sys.argv[1]

	samplesType = None
	if triggeredSwitchcraftPattern.match(fileName):
		samplesType = PowerSampleType.TriggeredSwitchcraft
	elif nonTriggeredSwitchcraftPattern.match(fileName):
		samplesType = PowerSampleType.NonTriggeredSwitchcraft
	elif filteredPattern.match(fileName):
		samplesType = PowerSampleType.Filtered
	elif unfilteredPattern.match(fileName):
		samplesType = PowerSampleType.Unfiltered
	elif softfusePattern.match(fileName):
		samplesType = PowerSampleType.SoftFuse
	else:
		print("Unknown samples type for filename", fileName)
		return

	with open(fileName, 'r') as file:
		lines = file.readlines()
		for line in lines:
			match = samplesPattern.match(line)
			if match:
				stoneId = match.group(1)
				try:
					samplesJson = json.loads(match.group(2))
					timestamp = samplesJson[0]['timestamp']
					writeFile(samplesType, stoneId, timestamp, line)
				except Exception as e:
					print(e)
					print("Invalid data in line:", line)
					exit(1)


# Returns True when the line was new.
def writeFile(samplesType, stoneId, timestamp, line):
	print("writeFile type:", samplesType, " stoneId:", stoneId, " timestamp:", timestamp)
#	print("line:", line)

	for index in range(0, 100):
		fileName = getFileName(samplesType, stoneId, timestamp, index)
		try:
			file = open(fileName, 'r')
			if file.readline() == line:
				print("already exists as file:", fileName)
				file.close()
				return False
		except:
			print("writing to file:", fileName)
			file = open(fileName, 'w')
			file.write(line)
			return True
	print("Infinite loop? type:", samplesType, " stoneId:", stoneId, " timestamp:", timestamp)
	print("line:", line)

def getFileName(samplesType, stoneId, timestamp, index):
	print("getFileName", samplesType, stoneId, timestamp, index)
	return samplesType.name + "_" + str(timestamp) + "_" + str(stoneId) + "_" + str(index)

main()

