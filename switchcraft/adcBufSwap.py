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
ALGORITHM_NUM_BUFFERS = 2 # Number of buffers the algorithm needs in memory


PLOT_PER_FILE = False
PLOT_DEBUG = True
PLOT_BEST = True



def main():
	fileNames = sys.argv[1:]

	largestDiffs = []  # List of largest diff per file.

	for fileName in fileNames:
		if PLOT_PER_FILE:
			if PLOT_DEBUG:
				fig, (ax1, ax2) = plt.subplots(2, sharex=True)
				plt.title(fileName)
			else:
				# plt.figure()
				fig, (ax1, ax2) = plt.subplots(2, sharex=True)
				plt.title(fileName)

		f = open(fileName, 'r')
		data = json.load(f)

		# Bookkeeping
		i = 0
		restarted = True
		uartNoise = False
		timestampDiffMs = 0
		skipBuffers = (ALGORITHM_NUM_BUFFERS - 1)  # Keeps up number of buffers to skip before starting the algorithm
		bufferList = []  # List of buffers in memory, that the algorithm can use

		# Used for plotting
		allBuffers = [] # List with list of samples, of each buffer.
		allTimestamps = [] # List with list of timestamps of each sample, of each buffer.
		timestamps = [] # List of the raw start timestamp of each buffer
		timestampDiffs = [0] # List of timestamp diff between buffers
		restartTimestampsMs = [] # List of timestamps of ADC restarts.
		uartNoiseTimestampsMs = [] # List of timestamps of UART noise.
		diffs = []
		diffsTimestampsMs = []


		for entry in data:
			if ('restart' in entry):
				restarted = True
			elif ('uartNoise' in entry):
				uartNoise = True
			elif ('samples' in entry):
				buffer = entry['samples']

				# Some data was recorded with 10bit ADC resolution, instead of 12bit
				if (max(buffer) < 1024):
					for k in range(0, len(buffer)):
						buffer[k] *= 4

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

				if PLOT_PER_FILE and PLOT_DEBUG:
					ax1.plot(timestampsMs, buffer, '--')

				bufferList.append(buffer)

				if (skipBuffers == 0):
					# There are enough consecutive buffers to perform calculations.
					# Buffer -1 is the latest
					diff = calcDiff(bufferList[-1], bufferList[-2])
					diffs.append(diff)
					diffsTimestampsMs.append(timestampMs)

				else:
					skipBuffers -= 1

				if (len(bufferList) > ALGORITHM_NUM_BUFFERS):
					bufferList.pop(0)

				if (uartNoise):
					uartNoiseTimestampsMs.append(timestampMs)
					uartNoise = False
				i += 1
				allBuffers.append(buffer)
				allTimestamps.append(timestampsMs)
			# if (i > 3500):
			# 	break

		# End of loop over different buffers
		largestDiffs.append(max(diffs))
		if PLOT_PER_FILE:
			ax2.plot(diffsTimestampsMs, diffs, '.')

			if PLOT_DEBUG:
				ax1.plot(restartTimestampsMs, [0]*len(restartTimestampsMs), 'x')
				ax1.plot(uartNoiseTimestampsMs, [-100]*len(uartNoiseTimestampsMs), 'x')
			plt.show()

	if PLOT_BEST:
		plt.figure()
		plt.plot(largestDiffs, 'o')
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


def calcDiff(buf1, buf2):
	# Calculate difference:
	diff = 0.0
	for i in range(0, len(buf2)):
		# d = abs(buf2[i] - buf1[i])
		# if (d > MAX_DIFF_PER_SAMPLE):
		# 	d = MAX_DIFF_PER_SAMPLE
		# if (d < MIN_DIFF_PER_SAMPLE):
		# 	d = 0
		# Square the diff, so that smaller differences count less
		# diff += d

		# diff += (buf2[i] - buf1[i]) ** 2
		diff += abs(buf2[i] - buf1[i])

	return diff

# cProfile.run('main()')
main()