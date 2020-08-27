#!/usr/bin/env python3

import json
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import *

PLOT_SAMPLES = False

def calcAveragePower(fileNames, voltageMultiplier, currentMultiplier):
	for fileName in fileNames:
		with open(fileName, 'r') as infile:
			data = json.load(infile)
		voltageSamples = np.array(data["voltageSampes"])
		currentSamples = np.array(data["currentSampes"])

		# Shift the samples by average zero
		voltageZero = calcZero(voltageSamples)
		currentZero = calcZero(currentSamples)
		voltageSamplesShifted = voltageSamples - voltageZero
		currentSamplesShifted = currentSamples - currentZero

		voltageSamplesCorrected = voltageSamplesShifted * voltageMultiplier
		currentSamplesCorrected = currentSamplesShifted * currentMultiplier

		# Calculate RMS values and power
#		voltageRms = calcAverageRms(voltageSamplesCorrected, voltageSamplesCorrected)
#		currentRms = calcAverageRms(currentSamplesCorrected, currentSamplesCorrected)
		powerRms = calcAverageRms(voltageSamplesCorrected, currentSamplesCorrected, False)
		return powerRms

def calcAverageRms(samplesList1, samplesList2, square=True):
	rms = []
	for i in range(0, len(samplesList1)):
		rms.append(calcRms(samplesList1[i], samplesList2[i], square))
#	print(rms)
	return (np.mean(rms), np.std(rms))

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
	return np.mean(np.mean(samples))


def main():
	fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=False, figsize=(10, 10))

	if PLOT_SAMPLES:
		fig2, (ax21, ax22) = plt.subplots(2, sharex=True)
		t=0

	voltageTruth = []
	voltageMean = []
	voltageStd = []
	currentTruth = []
	currentMean = []
	currentStd = []
	powerTruth = []
	powerMean = []
	powerStd = []

	fileNames = sys.argv[1:]
	for fileName in fileNames:
		with open(fileName, 'r') as infile:
			data = json.load(infile)
		voltageGroundTruth = data["voltageGroundTruth"]
		currentGroundTruth = data["currentGroundTruth"]
		powerGroundTruth = data["powerGroundTruth"]
		voltageSamples = np.array(data["voltageSampes"])
		currentSamples = np.array(data["currentSampes"])

		# Shift the samples by average zero
		voltageZero = calcZero(voltageSamples)
		currentZero = calcZero(currentSamples)
		voltageSamplesShifted = voltageSamples - voltageZero
		currentSamplesShifted = currentSamples - currentZero

		# Calculate RMS values and power
		voltageRms = calcAverageRms(voltageSamplesShifted, voltageSamplesShifted)
		currentRms = calcAverageRms(currentSamplesShifted, currentSamplesShifted)
		powerRms = calcAverageRms(voltageSamplesShifted, currentSamplesShifted, False)

		# Append for plot
		voltageTruth.append(voltageGroundTruth)
		voltageMean.append(voltageRms[0])
		voltageStd.append(voltageRms[1])
		currentTruth.append(currentGroundTruth)
		currentMean.append(currentRms[0])
		currentStd.append(currentRms[1])
		powerTruth.append(powerGroundTruth)
		powerMean.append(powerRms[0])
		powerStd.append(powerRms[1])

		# Plot std
		ax1.plot([voltageGroundTruth, voltageGroundTruth], [voltageRms[0] - voltageRms[1], voltageRms[0] + voltageRms[1]], '-k')
		ax2.plot([currentGroundTruth, currentGroundTruth], [currentRms[0] - currentRms[1], currentRms[0] + currentRms[1]], '-k')
		# ax3.plot([powerGroundTruth, powerGroundTruth], [powerRms[0] - powerRms[1], powerRms[0] + powerRms[1]], '-k')

		if PLOT_SAMPLES:
			for i in range(0, len(voltageSamples)):
				x = range(t, t + len(voltageSamples[i]))
				ax21.plot(x, voltageSamples[i], '.-')
				ax22.plot(x, currentSamples[i], '.-')
				t += len(voltageSamples[i])

	# Fit the data: calibrated = x[0] * truth + x[1]
	# voltageFit = np.polyfit(voltageTruth, voltageMean, 1)
	# currentFit = np.polyfit(currentTruth, currentMean, 1)

	# Fit the data: calibrated = x[0] * truth
	optimize_func = lambda x: x[0] * np.array(voltageTruth) - np.array(voltageMean)
	beta0 = [0]
	lsq = least_squares(optimize_func, beta0, method='lm', loss='linear')
	voltageFit = np.array([lsq.x[0], 0])

	# Fit the data: calibrated = x[0] * truth
	# optimize_func = lambda x: x[0] * np.array(currentTruth) - np.array(currentMean)
	# beta0 = [0]
	# lsq = least_squares(optimize_func, beta0, method='lm', loss='linear')
	# currentFit = np.array([lsq.x[0], 0])


	# Fit the data: calibrated = b * truth + sigma
	optimize_func = lambda x, b: b * x

	# Higher currents are expected to have a larger measurement error.
	# Up to something like 0.3A it should all be equally precise.
	sigma = np.maximum(powerTruth, 0.3)
	popt, pcov = curve_fit(optimize_func, currentTruth, currentMean, sigma=np.maximum(currentTruth, 0.1))
	currentFit = np.array([popt[0], 0])


	# Fit the data: calibrated = b * truth + a
	# Determine current multiplier on power usage.
	optimize_func = lambda x, b, a: b * x + a
	# Higher power usage is expected to have a larger measurement error.
	# Up to something like 10W it should all be equally precise.
	sigma = np.maximum(powerTruth, 10)
	popt, pcov = curve_fit(optimize_func, powerTruth, powerMean, sigma=sigma)
	powerFit = np.array([popt[0], popt[1]])
	powerMultiplier = 1.0 / powerFit[0]

	currentFit = np.array([-1 * powerFit[0] / voltageFit[0], 0])


	voltageMultiplier = 1.0 / voltageFit[0]
	currentMultiplier = 1.0 / currentFit[0]
	print("voltageMultiplier:", voltageMultiplier)
	print("currentMultiplier:", currentMultiplier)



#	# Use the multipliers to scale the power
#	powerMean = np.array(powerMean) * voltageMultiplier * currentMultiplier
#
#
#	# Fit the data: calibrated = b * truth + a
#	optimize_func = lambda x, b, a: b * x + a
#	# Higher power usage is expected to have a larger measurement error.
#	# Up to something like 10W it should all be equally precise.
#	sigma = np.maximum(powerTruth, 10)
#	popt, pcov = curve_fit(optimize_func, powerTruth, powerMean, sigma=sigma)
#	powerFit = np.array([popt[0], popt[1]])
#	powerMultiplier = 1.0 / powerFit[0]



	# Plot all truth vs mean
	ax1.plot(voltageTruth, voltageMean, 'o', label="calculated")
	ax1.plot(voltageTruth, np.poly1d(voltageFit)(voltageTruth), label="fit")
	ax1.set_xlabel("truth (V)")
	ax1.set_ylabel("calculated (V)")
	ax1.set_title('Voltage multiplier=' + str(voltageMultiplier))

	ax2.plot(currentTruth, currentMean, 'o', label="calculated")
	ax2.plot(currentTruth, np.poly1d(currentFit)(currentTruth), label="fit")
	ax2.set_xlabel("truth (A)")
	ax2.set_ylabel("calculated (A)")
	ax2.set_title('Current multiplier=' + str(currentMultiplier))

	ax3.plot(powerTruth, powerMean, 'o', label="power")
	ax3.plot(powerTruth, np.poly1d(powerFit)(powerTruth), label="fit")
	ax3.set_xlabel("truth (W)")
	ax3.set_ylabel("calculated (W)")
	ax3.set_title('Power multiplier=' + str(powerMultiplier) + " offset=" + str(powerFit[1]))

	fig.tight_layout()
	plt.show()

	# # Adjust current multiplier based on power multiplier?
	# currentMultiplier = currentMultiplier * powerMultiplier
	# print("currentMultiplier fitted on power:", currentMultiplier)

main()
