#!/usr/bin/python3

import matplotlib.pyplot as plt
import numpy as np
import json
import sys, os

# Config
RTC_CLOCK_FREQ = 32768
MAX_RTC_COUNTER_VAL = 0x00FFFFFF
SAMPLE_TIME_US = 200
# SAMPLE_TIME_US = 400 # For the single channel data
NUM_BUFFERS = 4
# Normalize to amplitude of 1500 (close to original signal)
# This works better, because the otherwise a difference in mean of 1 is a relative big difference
NORMALIZED_AMPLITUDE = 1500
MAX_DIFF_PER_SAMPLE = 450 # 450**2 = 202,500, so 2 of those are still below threshold
THRESHOLD = 500000 # Max seen in non switch data is about 350,000
# THRESHOLD = 250000 # For the single channel data
PLOT = True
PLOT_NONE_FOUND = False
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
		skipBuffers = (NUM_BUFFERS-2) # Number of buffers to skip before starting the algorithm
		samplesList = [] # Small list of buffers that the algorithm can use for detection
		scoresX = []
		scoresY = []
		shiftScores = []
		allSamples = []
		allTimestamps = []
		timestamps = [] # List of raw timestamps of all buffers
		timestampDiffs = [0] # List of timestamp diff between buffers
		restarted = True
		restartTimestampsMs = []
		uartNoise = False
		uartNoiseTimestampsMs = []

		for entry in data:
			if ('restart' in entry):
				restarted = True
			elif ('uartNoise' in entry):
				uartNoise = True
			elif ('samples' in entry):
				samples = entry['samples']
				timestamp = entry['timestamp']
				timestamps.append(timestamp)
				timestampMs = timestamp * 1000.0 / RTC_CLOCK_FREQ
				timestampsMs = np.array(range(0,len(samples))) * SAMPLE_TIME_US / 1000.0 + timestampMs

				if (restarted):
					restartTimestampsMs.append(timestampMs)
					restarted = False
					skipBuffers = (NUM_BUFFERS-2)
					samplesList.clear()
				if (uartNoise):
					uartNoiseTimestampsMs.append(timestampMs)
					uartNoise = False

				if i>0:
					timestampDiff = (timestamps[-1] - timestamps[-2]) & MAX_RTC_COUNTER_VAL
					timestampDiffs.append(timestampDiff)

				if PLOT_DEBUG:
					ax1.plot(timestampsMs, samples, '--')

				# We have the previous samples too
				# if i >= (NUM_BUFFERS-2):
				if (skipBuffers == 0):
					samplesList.append(samples)
					normalizedBufferList = normalizeSamples(samplesList)

					diffBuffer = []
					for j in range(0, len(normalizedBufferList[0])):
						diffBuffer.append(normalizedBufferList[-1][j] - normalizedBufferList[-2][j])
					if PLOT and PLOT_DEBUG:
						ax1.plot(timestampsMs, diffBuffer)


					score = calcDiff(normalizedBufferList)
					shiftScore = calcDiffWithShifts(normalizedBufferList)
					usedScore = score
					if PLOT:
						if PLOT_DEBUG:
							ax1.plot(timestampsMs, samplesList[-1], '-o')
						else:
							if usedScore > THRESHOLD:
								ax1.plot(allTimestamps[-2], samplesList[-3], '-o') # Previous buffer
								ax1.plot(allTimestamps[-1], samplesList[-2], '-o') # Previous buffer
								ax1.plot(timestampsMs, samplesList[-1], '-o')
								ax2.plot(timestampMs, usedScore, 's')

								# plot time diffs
								# ax1.plot(allTimestamps[-2][0], timestampDiffs[-3] * 1000.0 * 1000.0 / RTC_CLOCK_FREQ, '<')
								# ax1.plot(allTimestamps[-1][0], timestampDiffs[-2] * 1000.0 * 1000.0 / RTC_CLOCK_FREQ, '<')
								# ax1.plot(timestampMs, timestampDiffs[-1] * 1000.0 * 1000.0 / RTC_CLOCK_FREQ, '<')


					scoresX.append(timestampMs)
					scoresY.append(score)
					shiftScores.append(shiftScore)
					samplesList.pop(0)
				else:
					samplesList.append(samples)
					skipBuffers -= 1
				i += 1
				allSamples.append(samples)
				allTimestamps.append(timestampsMs)


		# End of loop over different buffers
		if PLOT:
			if PLOT_DEBUG:
				ax2.plot(scoresX, scoresY, '-o')
				ax2.plot(scoresX, shiftScores, '-s')

				fig2, fig2Axes = plt.subplots()
				timestampDiffs = []
				for i in range(1, len(timestamps)):
					timestampDiff = (timestamps[i] - timestamps[i-1]) & MAX_RTC_COUNTER_VAL
					timestampDiffs.append(-timestampDiff * 1000.0 * 1000.0 / RTC_CLOCK_FREQ)
				# ax1.plot(np.array(allTimestamps[1:])[:,0], timestampDiffs)

				# fig2Axes.violinplot(timestampDiffs)
				hist, bins = np.histogram(timestampDiffs, 100, density=True)
				width = 0.7 * (bins[1] - bins[0])
				center = (bins[:-1] + bins[1:]) / 2
				fig2Axes.bar(center, hist*width, align='center', width=width)

			elif PLOT_NONE_FOUND:
				if max(shiftScores) <= THRESHOLD:
					ax1.plot(np.transpose(allTimestamps), np.transpose(allSamples), '-o')
					ax2.plot(scoresX, shiftScores, '-s')
		if PLOT_DEBUG or PLOT_NONE_FOUND:
			ax1.plot(restartTimestampsMs, [0]*len(restartTimestampsMs), 'x')
			ax1.plot(uartNoiseTimestampsMs, [-100]*len(uartNoiseTimestampsMs), 'x')

		foundStr = "switch found" if (max(shiftScores) > THRESHOLD) else "no switch found"
		print(fileName, "{:12.0f}".format(max(scoresY)), "{:12.0f}".format(max(shiftScores)), foundStr)
		if max(shiftScores) > THRESHOLD:
			filesWithSwitch += 1
		else:
			filesWithoutSwitch += 1
		plt.show()

	print("with switch:", filesWithSwitch)
	print("without switch:", filesWithoutSwitch)
	# plt.show()



def calcMeanAndAmplitude(buffer):
	# Calc mean by average of samples, and amplitude by using tops
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
	return (mean, amplitude)


def normalizeSamples(bufferList):
	# Returns normalized bufferlist
	normalizedBufferList = []
	for buffer in bufferList:
		(mean, amplitude) = calcMeanAndAmplitude(buffer)
		amplitudeInv = 1.0/amplitude

		normalizedBuffer = [0.0]*len(buffer)
		for i in range(0, len(buffer)):
			# Normalize (done inline, as this is called many times, and function call is a lot of overhead)
			normalizedBuffer[i] = (buffer[i] - mean) * amplitudeInv * NORMALIZED_AMPLITUDE + mean
		normalizedBufferList.append(normalizedBuffer)
	return normalizedBufferList


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
		shift = -shift
		for i in range(shift, len(checkSamples)):
			diff += (checkSamples[i-shift] - prevSamples[i]) ** 2

	return diff



def calcDiffWithShifts(samplesList):
	minDiff = sys.float_info.max
	bestShift = 0
	for shift in range(MIN_SHIFT, MAX_SHIFT+1):
		diff = calcDiff(samplesList, shift)
		if (diff < minDiff):
			minDiff = diff
			bestShift = shift
	# if (bestShift != 0):
	# 	print("bestShift=", bestShift)
	return minDiff



def fit_sin(t, y):
	# TODO
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