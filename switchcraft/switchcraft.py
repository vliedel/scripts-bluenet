#!/usr/bin/python3

import matplotlib.pyplot as plt
import numpy as np
import json
import sys, os

# Config
RTC_CLOCK_FREQ = 32768
MAX_RTC_COUNTER_VAL = 0x00FFFFFF
SAMPLE_TIME_US = 200
NUM_BUFFERS = 4
DEFAULT_AMPLITUDE = 1500
MAX_DIFF_PER_SAMPLE = 450 # 450**2 = 202,500, so 2 of those are still below threshold
THRESHOLD = 500000 # Max seen in non switch data is about 350,000
PLOT = True
PLOT_DEBUG = False
MIN_SHIFT = -2
MAX_SHIFT = 2

# Reboot:
# ACR01B1D-voltage-switch-0W-2018-04-24--11-36-43.json

# No switches?:
# ACR01B1D-voltage-switch-100W-2018-04-24--13-16-58.json
# ACR01B1D-voltage-switch-100W-2018-04-24--13-17-50.json
# ACR01B1D-voltage-switch-100W-2018-04-24--13-18-22.json

# False negatives:
# ACR01B1D-voltage-switch-0W-2018-04-24--11-45-01.json
# ACR01B1D-voltage-switch-0W-2018-04-24--11-44-50.json
# ACR01B1D-voltage-switch-0W-2018-04-24--11-44-43.json
# ACR01B1D-voltage-switch-0W-2018-04-24--11-44-41.json
# ACR01B1D-voltage-switch-0W-2018-04-24--09-22-04.json

# False positives:
# ACR01B1D-voltage-switch-0W-2018-04-24--11-44-48.json <-- fixed with shift of -1
# ACR01B1D-voltage-switch-0W-2018-04-24--11-36-40.json <-- fixed with shift of -1
# ACR01B1D-voltage-switch-0W-2018-04-24--11-36-32.json <-- fixed with shift of -1
# ACR01B1D-voltage-switch-0W-2018-04-24--11-36-29.json <-- fixed with shift of -1



def main():
	fileNames = sys.argv[1:]

	filesWithSwitch = 0
	filesWithoutSwitch = 0
	for fileName in fileNames:
		if PLOT:
			if PLOT_DEBUG:
				fig, (ax1, ax2) = plt.subplots(2, sharex=True)
				plt.title(fileName)
			else:
				# plt.figure()
				fig, (ax1, ax2) = plt.subplots(2, sharex=True)
				plt.title(fileName)

		f = open(fileName, 'r')
		data = json.load(f)
		i = 0
		samplesList = []
		scoresX = []
		scoresY = []
		shiftScores = []
		allSamples = []
		allTimestamps = []

		for entry in data:
			samples = entry['samples']
			timestamp = entry['timestamp']
			timestampMs = timestamp * 1000.0 / RTC_CLOCK_FREQ
			timestampsMs = np.array(range(0,len(samples))) * SAMPLE_TIME_US / 1000.0 + timestampMs
			if PLOT_DEBUG:
				ax1.plot(timestampsMs, samples, '--')

			# We have the previous samples too
			if i >= (NUM_BUFFERS-2):
				samplesList.append(samples)
				normalizeSamples(samplesList)

				diffBuffer = []
				for i in range(0, len(samplesList[0])):
					diffBuffer.append(samplesList[-1][i] - samplesList[-2][i])
				if PLOT and PLOT_DEBUG:
					ax1.plot(timestampsMs, diffBuffer)


				score = calcDiff(samplesList)
				shiftScore = calcDiffWithShifts(samplesList)
				if PLOT:
					if PLOT_DEBUG:
						ax1.plot(timestampsMs, samplesList[-1], '-o')
					else:
						if shiftScore > THRESHOLD:
							ax1.plot(timestampsMs, samples, '-o')
							ax2.plot(timestampMs, shiftScore, 's')

				scoresX.append(timestampMs)
				scoresY.append(score)
				shiftScores.append(shiftScore)
				samplesList.pop(0)
			else:
				samplesList.append(samples)
			i += 1
			allSamples.extend(samples)
			allTimestamps.extend(timestampsMs)
		if PLOT:
			if PLOT_DEBUG:
				ax2.plot(scoresX, scoresY, '-o')
				ax2.plot(scoresX, shiftScores, '-s')
			else:
				if max(shiftScores) <= THRESHOLD:
					ax1.plot(allTimestamps, allSamples, '-o')
					ax2.plot(scoresX, shiftScores, '-s')
					print("No switch found for", fileName)
		print(fileName, "{:12.0f}".format(max(scoresY)), "{:12.0f}".format(max(shiftScores)))
		if max(shiftScores) > THRESHOLD:
			filesWithSwitch += 1
		else:
			filesWithoutSwitch += 1
		plt.show()

	print("with switch:", filesWithSwitch)
	print("without switch:", filesWithoutSwitch)
	# plt.show()



def normalizeSamples(bufferList):
	# # Calc amplitude and mean, by using tops and sum
	# # Calc mean over all buffer in list, while amplitude is calculated per buffer
	# sum = 0.0
	# amplitudeList = []
	# for buffer in bufferList:
	# 	maxVal = -10000
	# 	minVal = 10000
	# 	for val in buffer:
	# 		if (val > maxVal):
	# 			maxVal = val
	# 		if (val < minVal):
	# 			minVal = val
	# 		sum += val
	#
	# 	amplitude = 0.5*(maxVal - minVal)
	# 	amplitudeList.append(amplitude)
	# mean = 1.0 * sum / len(bufferList[0]) / len(bufferList)
	#
	# for buffer, amplitude in zip(bufferList, amplitudeList):
	# 	# Normalize
	# 	for i in range(0, len(buffer)):
	# 		buffer[i] = (buffer[i] - mean) / amplitude * 1500 + mean
	# 		# buffer[i] = (buffer[i] - mean) / amplitude + mean

	# Calc amplitude and mean, by using tops and sum
	for buffer in bufferList:
		sum = 0.0
		maxVal = -10000
		minVal = 10000
		for val in buffer:
			if (val > maxVal):
				maxVal = val
			if (val < minVal):
				minVal = val
			sum += val

		amplitude = 0.5*(maxVal - minVal)
		mean = 1.0 * sum / len(buffer)

		# Normalize
		for i in range(0, len(buffer)):
			# Normalize to amplitude of 1500 (close to original signal)
			# This works better, because the otherwise a difference in mean of 1 is a relative big difference
			buffer[i] = (buffer[i] - mean) / amplitude * DEFAULT_AMPLITUDE + mean
			# # Normalize to amplitude of 1
			# buffer[i] = (buffer[i] - mean) / amplitude + mean



def calcDiff(samplesList, shift=0):
	# Last in the list are the samples to check
	prevSamples = samplesList[-2]
	checkSamples = samplesList[-1]

	# Calculate difference:
	diff = 0.0
	if (shift >= 0):
		for i in range(shift, len(checkSamples)):
			# diff += abs(checkSamples[i] - prevSamples[i])
			d = abs(checkSamples[i] - prevSamples[i-shift])
			if (d > MAX_DIFF_PER_SAMPLE):
				d = MAX_DIFF_PER_SAMPLE
			diff += d ** 2
	else:
		for i in range(-shift, len(checkSamples)):
			diff += (checkSamples[i+shift] - prevSamples[i]) ** 2

	return diff



def calcDiffWithShifts(samplesList):
	minDiff = sys.float_info.max
	bestShift = 0
	for shift in range(MIN_SHIFT, MAX_SHIFT+1):
		diff = calcDiff(samplesList, shift)
		if (diff < minDiff):
			minDiff = diff
			bestShift = shift
	if (bestShift != 0):
		print("bestShift=", bestShift)
	return minDiff



def fit_sin(t, y):
	t = np.array(t)
	y = np.array(y)

	# Calculate the mean
	mean = np.mean(y)

	# Search for point where mean gets crossed upwards
	crossInd = None
	below = y[0] < mean
	for i in range(1, len(y)):
		if (below and y[i] >= mean):
			# Found
			crossInd = i
			break
		if (y[i] < mean):
			below = True

	if (below and y[0] >= mean):
		# Found in wrap around
		crossInd = 0

	if (crossInd is None):
		print("No crossing found!", y)
		return None

main()