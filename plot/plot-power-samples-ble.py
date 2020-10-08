#!/usr/bin/env python3
import datetime
import json
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import *


def getSamples(samplesMap):
	samples = np.array(samplesMap["samples"])
	samples = (samples - samplesMap["offset"]) * samplesMap["multiplier"]
	return samples

def calcCurrentOrVoltageRms(samples, zero):
	rms = calcRms(samples - zero, samples - zero)
	return rms

def calcRms(samples1, samples2, squareRoot=True):
	rms = 0.0
	for i in range(0, len(samples1)):
		rms += samples1[i] * samples2[i]
	rms /= len(samples1)
	if (squareRoot):
		return np.sqrt(rms)
	else:
		return rms

def calcZero(samples):
	return np.mean(samples)


def main():
	fileNames = sys.argv[1:]
	for fileName in fileNames:
		with open(fileName, 'r') as infile:
			fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, sharex=True, figsize=(10, 10))

			voltageRms = []
			voltageMean = []

			currentRms = []
			currentMean = []

			localTimestamp = []

			for line in infile:
				data = json.loads(line)
				voltageGroundTruth = data["voltageGroundTruth"]
				currentGroundTruth = data["currentGroundTruth"]
				powerGroundTruth = data["powerGroundTruth"]

				voltageMap = data["voltage"]
				currentMap = data["current"]

				Tlocal = data["localTimestamp"]

				voltageSamples = getSamples(voltageMap)
				Vrms = calcCurrentOrVoltageRms(voltageSamples, 0)
				Vmean = calcZero(voltageSamples)
				Vrmscorrected = calcCurrentOrVoltageRms(voltageSamples, Vmean)

				currentSamples = getSamples(currentMap)
				Irms = calcCurrentOrVoltageRms(currentSamples, 0)
				Imean = calcZero(currentSamples)
				Irmscorrected = calcCurrentOrVoltageRms(currentSamples, Imean)

				voltageRms.append(Vrms)
				voltageMean.append(Vmean)
				currentRms.append(Irms)
				currentMean.append(Imean)
				localTimestamp.append(datetime.datetime.fromtimestamp(Tlocal))

			ax1.plot(localTimestamp, voltageRms, '.')
			ax1.set_xlabel("time")
			ax1.set_ylabel("rms (V)")

			ax2.plot(localTimestamp, voltageMean, '.')
			ax2.set_xlabel("time")
			ax2.set_ylabel("mean (V)")

			ax3.plot(localTimestamp, currentRms, '.')
			ax3.set_xlabel("time")
			ax3.set_ylabel("rms (A)")

			ax4.plot(localTimestamp, currentMean, '.')
			ax4.set_xlabel("time")
			ax4.set_ylabel("mean (A)")
	plt.show()

main()
