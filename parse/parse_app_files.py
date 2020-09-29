import numpy as np
import json
import re
import sys, os


#from .PowerSampleType import *

sys.path.append('../parse')
from PowerSampleType import *



# File patterns
#TriggeredSwitchcraftPattern = re.compile(".*power-samples-switchcraft-(true|false)-positive.*")
#NonTriggeredSwitchcraftPattern = re.compile(".*power-samples-switchcraft-(true|false)-negative.*")
#FilteredPattern = re.compile(".*power-samples-filteredData.*")
#UnfilteredPattern = re.compile(".*power-samples-unfilteredData.*")
#SoftFusePattern = re.compile(".*power-samples-softFuseData.*")

# Data patterns
# Matches: stoneUID:24:[{"samples":[1355,1289,1236,1419],"multiplier":0,"offset":0,"sampleInterval":200,"delay":0,"timestamp":1596100484,"count":100,"index":0,"type":1},{"samples":[1354,1286,1236,1173,1425],"multiplier":0,"offset":0,"sampleInterval":200,"delay":0,"timestamp":1596100484,"count":100,"index":1,"type":1}]
samplesPattern = re.compile("stoneUID:\d+:(\[{.*)")


def parse(fileName):
	"""
	Parses a power samples file downloaded with the consumer app.
	Returns a list of timestamps, samples, and metadata.

	:param fileName:        Name of the file to parse.

	:return: A list of consecutive (uninterrupted) timestamps and samples, and metadata in the form:
			 ([[t0, t1, ... , tN], [t0, t1, ... , tM], ...],
			  [[y0, y1, ... , yN], [y0, y1, ... , yM], ...],
			  [{"samplesType"=<PowerSampleType>, "bufferType"=<BufferType>, "mean"=<float>, "rms"=<float>, "rmsCorrected"=<float>}, { }, ...])
			Samples are scaled to Ampere, or Volt.
			rms uses the offset calculated by the firmware.
			rmsCorrected uses the mean of the samples to calculate the rms.
	"""

	timestampMs = 0

	allConsecutiveSamples = []
	consecutiveSamples = []

	allConsecutiveTimestamps = []
	consecutiveTimestamps = []

	allConsecutiveMetaData = []
	consecutiveMetaData = []

	with open(fileName, 'r') as file:
#		samplesType = PowerSampleType.TriggeredSwitchcraft
#		if (TriggeredSwitchcraftPattern.match(fileName)):
#			samplesType = PowerSampleType.TriggeredSwitchcraft
#		elif (NonTriggeredSwitchcraftPattern.match(fileName)):
#			samplesType = PowerSampleType.NonTriggeredSwitchcraft
#		elif (FilteredPattern.match(fileName)):
#			samplesType = PowerSampleType.Filtered
#		elif (UnfilteredPattern.match(fileName)):
#			samplesType = PowerSampleType.Unfiltered
#		elif (SoftFusePattern.match(fileName)):
#			samplesType = PowerSampleType.SoftFuse

		lines = file.readlines()

		for line in lines:
			match = samplesPattern.match(line)
			if (match):
				try:
					samplesJson = json.loads(match.group(1))
					for i in range(0, len(samplesJson)):
						samplesType = PowerSampleType(samplesJson[i]["type"])
						multiplier = samplesJson[i]["multiplier"]
						offset = samplesJson[i]["offset"]

						samples = (np.array(samplesJson[i]["samples"]) - offset) * multiplier
						sampleInterval = samplesJson[i]["sampleInterval"] / 1000.0

						timestampsMs = np.array(range(0, len(samples))) * sampleInterval + timestampMs

						if samplesType == PowerSampleType.TriggeredSwitchcraft or samplesType == PowerSampleType.NonTriggeredSwitchcraft:
							# Buffers are all after each other
							timestampMs += len(samples) * sampleInterval
						if samplesType == PowerSampleType.Filtered or samplesType == PowerSampleType.Unfiltered:
							if i % 2 == 1:
								# Buffers are interleaved
								timestampMs += len(samples) * sampleInterval
						if samplesType == PowerSampleType.SoftFuse:
							# Buffers are all after each other
							timestampMs += len(samples) * sampleInterval

						consecutiveSamples.extend(samples)
						consecutiveTimestamps.extend(timestampsMs)

						consecutiveMetaData = {
							"samplesType": samplesType,
							"bufferType": getBufferType(samplesType, i),
							"mean": calcZero(samples),
							"rms": calcCurrentOrVoltageRms(samples, 0),
							"rmsCorrected": calcCurrentOrVoltageRms(samples, calcZero(samples))
						}

						# Don't merge buffers
						allConsecutiveSamples.append(consecutiveSamples)
						allConsecutiveTimestamps.append(consecutiveTimestamps)
						allConsecutiveMetaData.append(consecutiveMetaData)
						consecutiveSamples = []
						consecutiveTimestamps = []
				except Exception as e:
					print("Invalid data in line:", line)
					print(e)
					exit(1)



	if (len(consecutiveSamples)):
		allConsecutiveSamples.append(consecutiveSamples)
		allConsecutiveTimestamps.append(consecutiveTimestamps)
		allConsecutiveMetaData.append(consecutiveMetaData)

	return allConsecutiveTimestamps, allConsecutiveSamples, allConsecutiveMetaData

def calcCurrentOrVoltageRms(samples, zero):
	rms = calcRms(samples - zero, samples - zero)
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
