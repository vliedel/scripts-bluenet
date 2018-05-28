#!/usr/bin/python3

import matplotlib.pyplot as plt
import numpy as np
import json
import sys, os
# import cProfile

# Config
RTC_CLOCK_FREQ = 32768
MAX_RTC_COUNTER_VAL = 0x00FFFFFF
SAMPLE_TIME_US = 200
ALGORITHM_NUM_BUFFERS = 3 # Number of buffers the algorithm needs in memory


THRESHOLD_DIFFERENT = 200000 # Difference scores above this threshold are considered to be different
THRESHOLD_SIMILAR = 200000   # Difference scores below this threshold are considered to be similar
THRESHOLD_RATIO = 2
PLOT = False
PLOT_NONE_FOUND = False
PLOT_DEBUG = False
PLOT_SCORES = True

# -- deprecated --
MIN_DIFF_PER_SAMPLE = 0 # So that lots of small differences don't add up to something above threshold
MAX_DIFF_PER_SAMPLE = 1000000 # So that a few big differences don't add up to something above threshold
# Normalize to amplitude of 1500 (close to original signal)
# This works better, because the otherwise a difference in mean of 1 is a relative big difference
NORMALIZED_AMPLITUDE = 1500
MIN_SHIFT = -2
MAX_SHIFT = 2

def main():
	fileNames = sys.argv[1:]

	filesWithSwitch = 0
	filesWithoutSwitch = 0
	allFilesBestScores = []

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
		skipBuffers = (ALGORITHM_NUM_BUFFERS-1) # Keeps up number of buffers to skip before starting the algorithm
		bufferList = [] # List of buffers in memory, that the algorithm can use for detection
		allScoreTimestamps = []  # Timestamps to plot the scores at (list of lists, for each buffer a timestamp for each score triple)
		allScores = [] # List of list of score triples (for each buffer the scores as returned by calcScores).
		highestScores = [0,0,0,0,0] # List of highest min(score12, score23): [min(score12, score23), score12, score23, score13, ratio], where score12, score23 > score13
		largestDiffScores = [0,0,0,0,0] # List of highest min(score12, score23) - score13: [min(score12, score23) - score13, score12, score23, score13, ratio], where score12, score23 > score13
		allBuffers = []
		allTimestamps = []
		timestamps = [] # List of raw timestamps of all buffers
		timestampDiffs = [0] # List of timestamp diff between buffers
		restarted = True
		restartTimestampsMs = []
		uartNoise = False
		uartNoiseTimestampsMs = []
		foundSwitches = []
		timestampDiffMs = 0

		for entry in data:
			if ('restart' in entry):
				restarted = True
			elif ('uartNoise' in entry):
				uartNoise = True
			elif ('samples' in entry):
				buffer = entry['samples']

				# # Some data has 10bit ADC resolution
				# for k in range(0, len(buffer)):
				# 	buffer[k] *= 4

				timestamp = entry['timestamp']
				timestamps.append(timestamp)
				timestampMs = timestamp * 1000.0 / RTC_CLOCK_FREQ
				timestampsMs = np.array(range(0,len(buffer))) * SAMPLE_TIME_US / 1000.0 + timestampMs

				if i>0:
					timestampDiff = (timestamps[-1] - timestamps[-2]) & MAX_RTC_COUNTER_VAL
					timestampDiffs.append(timestampDiff)
					timestampDiffMs = timestampDiff * 1000.0 / RTC_CLOCK_FREQ

				if (uartNoise and timestampDiffMs > 40):
					restarted = True

				if (restarted):
					restartTimestampsMs.append(timestampMs)
					restarted = False
					skipBuffers = (ALGORITHM_NUM_BUFFERS-1)
					bufferList.clear()

				if PLOT and PLOT_DEBUG:
					ax1.plot(timestampsMs, buffer, '--')

				# We need to have the previous samples too
				if (skipBuffers == 0):
					bufferList.append(buffer) # Buffer -1 is the latest
					# normalizedBufferList = normalizeSamples(samplesList)
					normalizedBufferList = bufferList

					diffBuffer = []
					for j in range(0, len(normalizedBufferList[0])):
						diffBuffer.append(normalizedBufferList[-1][j] - normalizedBufferList[-2][j])
					if PLOT and PLOT_DEBUG:
						ax1.plot(allTimestamps[-1], diffBuffer)

					diffAroundBuffer = []
					for j in range(0, len(normalizedBufferList[0])):
						diffAroundBuffer.append(normalizedBufferList[-1][j] - normalizedBufferList[-3][j])
					if PLOT and PLOT_DEBUG:
						ax1.plot(allTimestamps[-2], diffAroundBuffer, '--')

					scores = calcScores(normalizedBufferList[-3], normalizedBufferList[-2], normalizedBufferList[-1])

					foundSwitch = False
					for [score12, score23, score13] in scores:
						# Check if switch was found
						minDiffScore = min(score12, score23)
						ratio = minDiffScore / score13
						if (score12 > THRESHOLD_DIFFERENT and score23 > THRESHOLD_DIFFERENT and score13 < THRESHOLD_SIMILAR):
							foundSwitch = True
						if (score12 > THRESHOLD_DIFFERENT and score23 > THRESHOLD_DIFFERENT and ratio > THRESHOLD_RATIO):
							foundSwitch = True

						# Keep up the best scores
						if (minDiffScore > score13):
							if (highestScores[0] < minDiffScore):
								highestScores = [minDiffScore, score12, score23, score13, ratio]
							if (largestDiffScores[0] < minDiffScore - score13):
								largestDiffScores = [minDiffScore - score13, score12, score23, score13, ratio]

					if (foundSwitch):
						foundSwitches.append(i)

					# Create a list of timestamps to plot the scores at.
					# We plot this halfway the previous buffer, as that's where the switch should be
					scoreTimestampInd = int(len(allTimestamps[0])/2)
					scoreTimestampIndStep = 10
					scoreTimestamps = allTimestamps[-1][scoreTimestampInd:scoreTimestampInd+len(scores)*scoreTimestampIndStep:scoreTimestampIndStep]

					if PLOT:
						if PLOT_DEBUG:
							ax1.plot(timestampsMs, bufferList[-1], '-o')
						else:
							if foundSwitch:
							# if (leftScore12 > THRESHOLD):
								ax1.plot(allTimestamps[-2], bufferList[-3], '-o') # 2 buffers ago
								ax1.plot(allTimestamps[-1], bufferList[-2], '-o') # Previous buffer
								ax1.plot(timestampsMs, bufferList[-1], '-o')
								scoreInd = 0
								for [score12, score23, score13] in scores:
									ax2.plot(scoreTimestamps[scoreInd], score12, '<')
									ax2.plot(scoreTimestamps[scoreInd], score13, '^')
									ax2.plot(scoreTimestamps[scoreInd], score23, '>')
									scoreInd += 1

								ax2.plot([allTimestamps[-2][0], timestampsMs[-1]], [THRESHOLD_DIFFERENT, THRESHOLD_DIFFERENT], '-k')
								ax2.plot([allTimestamps[-2][0], timestampsMs[-1]], [THRESHOLD_SIMILAR, THRESHOLD_SIMILAR], '--k')

								ax1.plot(allTimestamps[-1], diffBuffer)
								ax1.plot(allTimestamps[-2], diffAroundBuffer, '--')

							# # plot time diffs
							# ax1.plot(allTimestamps[-2][0], timestampDiffs[-3] * 1000.0 * 1000.0 / RTC_CLOCK_FREQ, '^')
							# ax1.plot(allTimestamps[-1][0], timestampDiffs[-2] * 1000.0 * 1000.0 / RTC_CLOCK_FREQ, '^')
							# ax1.plot(timestampMs, timestampDiffs[-1] * 1000.0 * 1000.0 / RTC_CLOCK_FREQ, '^')
					if foundSwitch:
						# print("buffer", i, "scored", usedScore, "That is", usedScore/THRESHOLD, "times threshold")
						print("buffer", i, "scored", scores)


					allScoreTimestamps.append(scoreTimestamps)
					allScores.append(scores)
					bufferList.pop(0)
				else:
					bufferList.append(buffer)
					skipBuffers -= 1
				if (uartNoise):
					uartNoiseTimestampsMs.append(timestampMs)
					uartNoise = False
				i += 1
				allBuffers.append(buffer)
				allTimestamps.append(timestampsMs)
			# if (i > 3500):
			# 	break

		# End of loop over different buffers
		if PLOT:
			if PLOT_DEBUG or PLOT_SCORES:
				scoresMat = np.array(allScores)
				ax2.plot(allScoreTimestamps, scoresMat[:,:,0], '<') # scores 12
				ax2.plot(allScoreTimestamps, scoresMat[:,:,1], '>') # scores 23
				ax2.plot(allScoreTimestamps, scoresMat[:,:,2], '^') # scores 13
				# ax2.plot(allScoreTimestamps, scoresMat[:,:,3], 'o') # ratio

				ax2.plot([allTimestamps[0][0], allTimestamps[-1][-1]], [THRESHOLD_DIFFERENT, THRESHOLD_DIFFERENT], '-k')
				ax2.plot([allTimestamps[0][0], allTimestamps[-1][-1]], [THRESHOLD_SIMILAR, THRESHOLD_SIMILAR], '--k')

				# fig2, fig2Axes = plt.subplots()
				# timestampDiffs = []
				# for i in range(1, len(timestamps)):
				# 	timestampDiff = (timestamps[i] - timestamps[i-1]) & MAX_RTC_COUNTER_VAL
				# 	timestampDiffs.append(-timestampDiff * 1000.0 * 1000.0 / RTC_CLOCK_FREQ)
				# # ax1.plot(np.array(allTimestamps[1:])[:,0], timestampDiffs)
				#
				# # fig2Axes.violinplot(timestampDiffs)
				# hist, bins = np.histogram(timestampDiffs, 100, density=True)
				# width = 0.7 * (bins[1] - bins[0])
				# center = (bins[:-1] + bins[1:]) / 2
				# fig2Axes.bar(center, hist*width, align='center', width=width)

			elif PLOT_NONE_FOUND:
				if len(foundSwitches) <= THRESHOLD_DIFFERENT:
					ax1.plot(np.transpose(allTimestamps), np.transpose(allBuffers), '-o')

			if PLOT_DEBUG or (PLOT_NONE_FOUND and len(foundSwitches) == 0):
				ax1.plot(restartTimestampsMs, [0]*len(restartTimestampsMs), 'x')
				ax1.plot(uartNoiseTimestampsMs, [-100]*len(uartNoiseTimestampsMs), 'x')

		foundStr = "switch found" if (len(foundSwitches)) else "NO switch found"
		# print(fileName, "{:12.0f}".format(max(scoresY)), "{:12.0f}".format(max(shiftScores)), foundStr)
		print(fileName, foundStr)
		if len(foundSwitches):
			filesWithSwitch += 1
		else:
			filesWithoutSwitch += 1
			print("best scores", highestScores[1:], '\n           ', largestDiffScores[1:])
		plt.show()
		# allFilesBestScores.append([highestScores[1:4], largestDiffScores[1:4]])
		allFilesBestScores.append(highestScores[1:])
		allFilesBestScores.append(largestDiffScores[1:])

	print("with switch:", filesWithSwitch)
	print("without switch:", filesWithoutSwitch)
	bestScoresMat = np.array(allFilesBestScores)
	if PLOT_SCORES and len(fileNames) > 1:
		plt.plot(bestScoresMat[:,0], '<') # scores 12
		plt.plot(bestScoresMat[:,1], '>') # scores 23
		plt.plot(bestScoresMat[:,2], '^') # scores 13
		plt.plot(bestScoresMat[:,3], 'o') # ratio
		plt.plot([0,len(bestScoresMat)], [THRESHOLD_DIFFERENT, THRESHOLD_DIFFERENT], '-k')
		plt.plot([0,len(bestScoresMat)], [THRESHOLD_SIMILAR, THRESHOLD_SIMILAR], '--k')
		plt.show()



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


def calcDiff(buf1, buf2, shift=0):
	# Calculate difference:
	diff = 0.0
	if (shift == 0):
		for i in range(0, len(buf2)):
			# d = abs(buf2[i] - buf1[i])
			# if (d > MAX_DIFF_PER_SAMPLE):
			# 	d = MAX_DIFF_PER_SAMPLE
			# if (d < MIN_DIFF_PER_SAMPLE):
			# 	d = 0
			# Square the diff, so that smaller differences count less
			# diff += d
			diff += (buf2[i] - buf1[i]) ** 2

	elif (shift > 0):
		for i in range(shift, len(buf2)):
			d = abs(buf2[i] - buf1[i-shift])
			if (d > MAX_DIFF_PER_SAMPLE):
				d = MAX_DIFF_PER_SAMPLE
			if (d < MIN_DIFF_PER_SAMPLE):
				d = 0
			# Square the diff, so that smaller differences count less
			diff += d ** 2
			# diff += d
	else:
		shift = -shift
		for i in range(shift, len(buf2)):
			diff += (buf2[i-shift] - buf1[i]) ** 2

	return diff



def calcDiffWithShifts(buf1, buf2):
	minDiff = sys.float_info.max
	bestShift = 0
	for shift in range(MIN_SHIFT, MAX_SHIFT+1):
		diff = calcDiff(buf1, buf2, shift)
		if (diff < minDiff):
			minDiff = diff
			bestShift = shift
	# if (bestShift != 0):
	# 	print("bestShift=", bestShift)
	return minDiff


def calcScores(buf1, buf2, buf3):
	bufSize = len(buf1)
	halfSize = int(bufSize/2)
	quarter = int(bufSize/4)
	left1 = buf1[0:halfSize]
	left2 = buf2[0:halfSize]
	left3 = buf3[0:halfSize]
	right1 = buf1[halfSize:bufSize]
	right2 = buf2[halfSize:bufSize]
	right3 = buf3[halfSize:bufSize]
	mid1 = buf1[quarter:quarter+halfSize]
	mid2 = buf2[quarter:quarter+halfSize]
	mid3 = buf3[quarter:quarter+halfSize]
	leftScore12 = calcDiff(left1, left2)
	leftScore23 = calcDiff(left2, left3)
	leftScore13 = calcDiff(left1, left3)
	rightScore12 = calcDiff(right1, right2)
	rightScore23 = calcDiff(right2, right3)
	rightScore13 = calcDiff(right1, right3)
	midScore12 = calcDiff(mid1, mid2)
	midScore23 = calcDiff(mid2, mid3)
	midScore13 = calcDiff(mid1, mid3)
	return [[leftScore12, leftScore23, leftScore13], [midScore12, midScore23, midScore13], [rightScore12, rightScore23, rightScore13]]



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

# cProfile.run('main()')
main()