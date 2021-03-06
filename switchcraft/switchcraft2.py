#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import json
import sys, os
# import cProfile

sys.path.append('../record')
import parse_recorded_voltage
import parse_app_files

######################
##### ADC Config #####
#######################
SAMPLES_PER_BUFFER = 100



#######################
##### Plot config #####
#######################
# Plot for each file
PLOT = True

# Plot all data when no switch is found
PLOT_NONE_FOUND = True

# Plot all data
PLOT_DEBUG = False

# Plot overall scores
PLOT_SCORES = True



############################
##### Algorithm config #####
############################
ALGORITHM_NUM_BUFFERS = 3    # Number of buffers the algorithm needs in memory
THRESHOLD_DIFFERENT = 100000 # Difference scores above this threshold are considered to be different
THRESHOLD_SIMILAR =   100000 # Difference scores below this threshold are considered to be similar



######################
##### Deprecated #####
######################

# Basically set threshold_similar to threshold_ratio * minimal difference score.
THRESHOLD_RATIO = 100

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
				fig.suptitle(fileName)
			else:
				fig, (ax1, ax2) = plt.subplots(2, sharex=True)
				print(ax1)
				fig.suptitle(fileName)

		# Init file vars
		openedFig = False
		foundSwitches = []
		allScoreTimestamps = []  # Timestamps to plot the scores at (list of lists, for each buffer a timestamp for each score triple)
		allScores = [] # List of list of score triples (for each buffer the scores as returned by calcScores).
		highestScores = [0, 0, 0, 0, 0]      # List of highest min(score12, score23):           [min(score12, score23),           score12, score23, score13, ratio], where score12, score23 > score13
		largestDiffScores = [0, 0, 0, 0, 0]  # List of highest min(score12, score23) - score13: [min(score12, score23) - score13, score12, score23, score13, ratio], where score12, score23 > score13

		# Parse file
		if (fileName.split('.')[-1] == 'json'):
			allTimestamps, allSamples = parse_recorded_voltage.parse(fileName, filterTimeJumps=False)
		else:
			allTimestamps, allSamples = parse_app_files.parse(fileName)

		for i in range(0, len(allSamples)):
			numBufs = int(len(allSamples[i]) / SAMPLES_PER_BUFFER)

			if (numBufs < ALGORITHM_NUM_BUFFERS):
				continue

			for j in range(0, numBufs - ALGORITHM_NUM_BUFFERS + 1):
				buf0 = np.array(allSamples[i][(j + 0) * SAMPLES_PER_BUFFER : (j + 1) * SAMPLES_PER_BUFFER])
				buf1 = np.array(allSamples[i][(j + 1) * SAMPLES_PER_BUFFER : (j + 2) * SAMPLES_PER_BUFFER])
				buf2 = np.array(allSamples[i][(j + 2) * SAMPLES_PER_BUFFER : (j + 3) * SAMPLES_PER_BUFFER])

				t0 = np.array(allTimestamps[i][(j + 0) * SAMPLES_PER_BUFFER: (j + 1) * SAMPLES_PER_BUFFER])
				t1 = np.array(allTimestamps[i][(j + 1) * SAMPLES_PER_BUFFER: (j + 2) * SAMPLES_PER_BUFFER])
				t2 = np.array(allTimestamps[i][(j + 2) * SAMPLES_PER_BUFFER: (j + 3) * SAMPLES_PER_BUFFER])

				diffBuffer = buf2 - buf1
				diffAroundBuffer = buf2 - buf0

				scores = calcScores(buf0, buf1, buf2)

				foundSwitch = False
				for [score12, score23, score13] in scores:
					# Check if switch was found
					minDiffScore = min(score12, score23)
					ratio = minDiffScore / score13
					if (score12 > THRESHOLD_DIFFERENT and score23 > THRESHOLD_DIFFERENT and score13 < THRESHOLD_SIMILAR):
						foundSwitch = True
#					if (score12 > THRESHOLD_DIFFERENT and score23 > THRESHOLD_DIFFERENT and ratio > THRESHOLD_RATIO):
#						foundSwitch = True

					# Keep up the best scores
					if (minDiffScore > score13):
						if (highestScores[0] < minDiffScore):
							highestScores = [minDiffScore, score12, score23, score13, ratio]
#						if (largestDiffScores[0] < minDiffScore - score13):
#							largestDiffScores = [minDiffScore - score13, score12, score23, score13, ratio]

				if (foundSwitch):
					foundSwitches.append(i)
					print("buffer", i, j, "scored", scores)

				# Create a list of timestamps to plot the scores at.
				# We plot this halfway the middle buffer, as that's where the switch should be
				scoreTimestampInd = int(len(t0) / 2)
				scoreTimestampIndStep = 10
				scoreTimestamps = t1[scoreTimestampInd:scoreTimestampInd + len(scores) * scoreTimestampIndStep:scoreTimestampIndStep]

				# Keep up scores of this file.
				allScoreTimestamps.append(scoreTimestamps)
				allScores.append(scores)

				if PLOT:
					if PLOT_DEBUG:
						pass
					else:
						if foundSwitch:
							# if (leftScore12 > THRESHOLD):
							ax1.plot(t0, buf0, '.-')
							ax1.plot(t1, buf1, '.-')
							ax1.plot(t2, buf2, '.-')
							scoreInd = 0
							for [score12, score23, score13] in scores:
								ax2.plot(scoreTimestamps[scoreInd], score12, '<')
								ax2.plot(scoreTimestamps[scoreInd], score13, '^')
								ax2.plot(scoreTimestamps[scoreInd], score23, '>')
								scoreInd += 1

							ax2.plot([t0[0], t2[-1]], [THRESHOLD_DIFFERENT, THRESHOLD_DIFFERENT], '-k')
							ax2.plot([t0[0], t2[-1]], [THRESHOLD_SIMILAR, THRESHOLD_SIMILAR], '--k')

							ax1.plot(t1, diffBuffer)
							ax1.plot(t1, diffAroundBuffer, '--')

		# End of loop over different buffers
		if PLOT:
			if PLOT_DEBUG or (PLOT_NONE_FOUND and len(foundSwitches) == 0):
				for i in range(0, len(allSamples)):
					numBufs = int(len(allSamples[i]) / SAMPLES_PER_BUFFER)
					for j in range(0, numBufs - ALGORITHM_NUM_BUFFERS + 1):
						buf0 = np.array(allSamples[i][(j + 0) * SAMPLES_PER_BUFFER: (j + 1) * SAMPLES_PER_BUFFER])
						buf1 = np.array(allSamples[i][(j + 1) * SAMPLES_PER_BUFFER: (j + 2) * SAMPLES_PER_BUFFER])
						buf2 = np.array(allSamples[i][(j + 2) * SAMPLES_PER_BUFFER: (j + 3) * SAMPLES_PER_BUFFER])

						t0 = np.array(allTimestamps[i][(j + 0) * SAMPLES_PER_BUFFER: (j + 1) * SAMPLES_PER_BUFFER])
						t1 = np.array(allTimestamps[i][(j + 1) * SAMPLES_PER_BUFFER: (j + 2) * SAMPLES_PER_BUFFER])
						t2 = np.array(allTimestamps[i][(j + 2) * SAMPLES_PER_BUFFER: (j + 3) * SAMPLES_PER_BUFFER])

						diffBuffer = buf2 - buf1
						diffAroundBuffer = buf2 - buf0

						ax1.plot(t0, buf0, '.-')
						ax1.plot(t1, diffBuffer)
						ax1.plot(t1, diffAroundBuffer, '--')

					# Also plot last 2 buffers of consecutive buffers list
					ax1.plot(t1, buf1, '.-')
					ax1.plot(t2, buf2, '.-')

				scoresMat = np.array(allScores)
				ax2.plot(allScoreTimestamps, scoresMat[:,:,0], '<') # scores 12
				ax2.plot(allScoreTimestamps, scoresMat[:,:,1], '>') # scores 23
				ax2.plot(allScoreTimestamps, scoresMat[:,:,2], '^') # scores 13
				# ax2.plot(allScoreTimestamps, scoresMat[:,:,3], '.') # ratio

				ax2.plot([allTimestamps[0][0], allTimestamps[-1][-1]], [THRESHOLD_DIFFERENT, THRESHOLD_DIFFERENT], '-k')
				ax2.plot([allTimestamps[0][0], allTimestamps[-1][-1]], [THRESHOLD_SIMILAR, THRESHOLD_SIMILAR], '--k')

#			if PLOT_DEBUG or (PLOT_NONE_FOUND and len(foundSwitches) == 0):
#				ax1.plot(restartTimestampsMs, [0]*len(restartTimestampsMs), 'x')
#				ax1.plot(uartNoiseTimestampsMs, [-100]*len(uartNoiseTimestampsMs), 'x')

		foundStr = "switch found" if (len(foundSwitches)) else "NO switch found"
		# print(fileName, "{:12.0f}".format(max(scoresY)), "{:12.0f}".format(max(shiftScores)), foundStr)
		print(fileName, foundStr)
		if len(foundSwitches):
			filesWithSwitch += 1
		else:
			filesWithoutSwitch += 1
			print("best scores", highestScores[1:])
#			print("best scores", highestScores[1:], '\n           ', largestDiffScores[1:])
		plt.show()
		# allFilesBestScores.append([highestScores[1:4], largestDiffScores[1:4]])
		allFilesBestScores.append(highestScores[1:])
#		allFilesBestScores.append(largestDiffScores[1:])

	print("with switch:", filesWithSwitch)
	print("without switch:", filesWithoutSwitch)
	bestScoresMat = np.array(allFilesBestScores)
	if PLOT_SCORES and len(fileNames) > 1:
		fig, (ax1, ax2) = plt.subplots(2, sharex=True)
		ax1.plot(bestScoresMat[:,0], '<') # scores 12
		ax1.plot(bestScoresMat[:,1], '>') # scores 23
		ax1.plot(bestScoresMat[:,2], '^') # scores 13
		ax1.plot([0,len(bestScoresMat)], [THRESHOLD_DIFFERENT, THRESHOLD_DIFFERENT], '-k')
		ax1.plot([0,len(bestScoresMat)], [THRESHOLD_SIMILAR, THRESHOLD_SIMILAR], '--k')

		ax2.plot(bestScoresMat[:, 3], '.')  # ratio
		ax2.plot([0, len(bestScoresMat)], [THRESHOLD_RATIO, THRESHOLD_RATIO], '--k')
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


# cProfile.run('main()')
main()
