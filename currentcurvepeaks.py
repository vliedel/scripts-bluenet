#!/usr/bin/env python

__author__ = 'Bart van Vliet'

import matplotlib.pyplot as plt
import optparse
import sys
import numpy as np
from scipy import signal
import time, datetime


def create_array(n):
    return [None] * n

def sort_block(alpha):
    pairs = [(alpha[i], i) for i in range(len(alpha))]
    return [i for v,i in sorted(pairs)]


class Block:
    def __init__(self, h, alpha):
        assert 2 * h + 1 == len(alpha)
        self.k = len(alpha)
        self.alpha = alpha
        self.pi = sort_block(alpha)
        self.prev = create_array(self.k + 1)
        self.next = create_array(self.k + 1)
        self.tail = self.k
        self.init_links()
        self.m = self.pi[h]
        self.s = h

    def init_links(self):
        # Use permutation pi to construct a doubly linked list.
        # There is an additional element at index k, which
        # serves as the head and the tail of the list.
        p = self.tail
        for i in range(self.k):
            q = self.pi[i]
            self.next[p] = q
            self.prev[q] = p
            p = q
        self.next[p] = self.tail
        self.prev[self.tail] = p

    def unwind(self):
        # Delete all elements from the list.
        for i in range(self.k-1, -1, -1):
            self.next[self.prev[i]] = self.next[i]
            self.prev[self.next[i]] = self.prev[i]
        self.m = self.tail
        self.s = 0

    def delete(self, i):
        # Delete one element.
        # Guarantee: s decreases by one (unless already zero).
        self.next[self.prev[i]] = self.next[i]
        self.prev[self.next[i]] = self.prev[i]
        if self.is_small(i):
            # We deleted a small element.
            self.s -= 1
        else:
            # We deleted a large element (or m itself).
            if self.m == i:
                # Make sure that m is still well-defined.
                self.m = self.next[self.m]
            if self.s > 0:
                # Move m so that we can decrease s.
                self.m = self.prev[self.m]
                self.s -= 1

    def undelete(self, i):
        # Put back one element.
        # Guarantee: s does not change.
        self.next[self.prev[i]] = i
        self.prev[self.next[i]] = i
        if self.is_small(i):
            # We deleted a small element.
            # Move m so that s is still correct.
            self.m = self.prev[self.m]

    def advance(self):
        # Increase s by one.
        self.m = self.next[self.m]
        self.s += 1

    def at_end(self):
        return self.m == self.tail

    def peek(self):
        return float('Inf') if self.at_end() else self.alpha[self.m]

    def get_pair(self, i):
        return (self.alpha[i], i)

    def is_small(self, i):
        return self.at_end() or self.get_pair(i) < self.get_pair(self.m)


def sort_median(h, b, x):
    k = 2 * h + 1
    assert len(x) == k * b
    B = Block(h, x[0:k])
    y = []
    y.append(B.peek())
    for j in range(1, b):
        A = B
        B = Block(h, x[j*k:(j+1)*k])
        B.unwind()
        assert A.s == h
        assert B.s == 0
        for i in range(k):
            A.delete(i)
            B.undelete(i)
            assert A.s + B.s <= h
            if A.s + B.s < h:
                if A.peek() <= B.peek():
                    A.advance()
                else:
                    B.advance()
            assert A.s + B.s == h
            y.append(min(A.peek(), B.peek()))
        assert A.s == 0
        assert B.s == h
    return y


if __name__ == '__main__':
	try:
		parser = optparse.OptionParser(usage="%prog [-v] [-f <input file>] \n\nExample:\n\t%prog -f file.txt",
									version="0.1")

		parser.add_option('-v', '--verbose',
				action="store_true",
				dest="verbose",
				help="Be verbose."
				)
		parser.add_option('-f', '--file',
				action='store',
				dest="data_file",
				type="string",
				default="data.txt",
				help='File to get the data from'
				)
		parser.add_option('-F', '--filtered',
				action="store_true",
				dest="filtered",
				default=False,
				help="Input data contains filtered curves too."
				)

		options, args = parser.parse_args()

	except Exception, e:
		print e
		print "For help use --help"
		sys.exit(2)

	cZero = 1995.0
	cMultiplier = 0.0045
	labels = []
	timestamps = []
	currentRmses = []
	currentRmsAvgs = []
	filteredCurrentRmses = []
	filteredCurrentRmsAvgs = []
	cZeros = []

	currentCurves = []
	currentCurvesFiltered = []
	voltageCurves = []
	filteredCurrentInFile = options.filtered
	with open(options.data_file, 'r') as f:
		for line in f.xreadlines():
			words = line.split()
			voltageFound = False
			currentFound = False
			filteredCurrentFound = False
			currentRmsFound = False
			currentCurve = []
			voltageCurve = []

			currentRms = "0"
			currentRmsAvg = "0"
			filteredCurrentRms = "0"
			filteredCurrentRmsAvg = "0"
			for word in words:
				if currentFound or filteredCurrentFound:
					currentCurve.append(int(word))
				if voltageFound:
					voltageCurve.append(int(word))
				if word == "Current:":
					currentFound = True
				if word == "Voltage:":
					voltageFound = True
				if word == "Filtered:":
					filteredCurrentFound = True
					filteredCurrentInFile = True
				if word.startswith("Irms="):
					currentRmsFound = True
					currentRms = word[len("Irms="):]
				if word.startswith("median=") and currentRmsFound:
					currentRmsAvg = word[len("median="):]
				if word.startswith("filtered=") and currentRmsFound:
					filteredCurrentRms = word[len("filtered="):]
				if word.startswith("filtered_median=") and currentRmsFound:
					filteredCurrentRmsAvg = word[len("filtered_median="):]
				if word.startswith("cZero=") and currentRmsFound:
					cZeros.append(int(word[len("cZero="):]) / 1000)

			if currentFound:
				if (options.filtered and (len(currentCurves) + len(currentCurvesFiltered)) % 2):
					currentCurvesFiltered.append(currentCurve)
				else:
					currentCurves.append(currentCurve)
			if filteredCurrentFound:
				currentCurvesFiltered.append(currentCurve)
			if voltageFound:
				voltageCurves.append(voltageCurve)
			if currentRmsFound:
				timestamps.append(words[0] + " " + words[1])
				currentRmses.append(int(currentRms))
				currentRmsAvgs.append(int(currentRmsAvg))
				filteredCurrentRmses.append(int(filteredCurrentRms))
				filteredCurrentRmsAvgs.append(int(filteredCurrentRmsAvg))
				labels.append("rms=" + currentRms + " median=" + currentRmsAvg)

	fig, axes = plt.subplots(nrows=2, sharex=True, sharey=True)
	Irmss=[]
	IrmssFiltered=[]
	curveStarts = []
	n=0
	windowSize=0
	for i in range(0, len(currentCurves)):
#		if (currentRmsAvgs[i] <= 1000 and currentRmses[i] <= 5000):
#		if (currentRmses[i] <= 5000):
#		if (currentRmsAvgs[i] <= 2000):
#			continue
		curve = np.array(currentCurves[i])
		# if (len(cZeros)):
		# 	curve -= cZeros[i]
		# else:
		# 	curve -= cZero
		axes[0].plot(range(n, n+len(curve)), curve)
		# label = timestamps[i] + "\n" + labels[i]
		# label = timestamps[i]
		#axes[0].text(n, 4000, label, rotation=45)

		if not filteredCurrentInFile:
			# curveFiltered = signal.medfilt(curve, 7)

			# halfWindow = 5
			halfWindow = 16
			windowSize = halfWindow * 2 + 1
			curveExt = halfWindow*[curve[0]]
			curveExt.extend(curve)
			curveExt.extend(halfWindow*[curve[-1]])
			blockCount = len(curveExt) / windowSize
			curveFiltered = sort_median(halfWindow, blockCount, curveExt)


			# # Filter again with same window size!
			# curveExt = halfWindow*[curveFiltered[0]]
			# curveExt.extend(curveFiltered)
			# curveExt.extend(halfWindow*[curveFiltered[-1]])
			# blockCount = len(curveExt) / windowSize
			# curveFiltered = sort_median(halfWindow, blockCount, curveExt)


			#axes[0].plot(range(n, n+len(curveFiltered)), curveFiltered, '--')
			currentCurvesFiltered.append(curveFiltered)

		# Calculate Irms
		ISquareSum = 0
		for c in curve:
			ISquareSum += c**2
		Irmss.append((ISquareSum * cMultiplier**2 / len(curve))**0.5 * 1000)

		curveStarts.append(n)
		n += len(curve) + 10

	# axes[0].plot(curveStarts, currentRmses,   'ro') # red
	# axes[0].plot(curveStarts, currentRmsAvgs, 'bo') # blue
	if (len(cZeros)):
		axes[0].plot(curveStarts, cZeros, 'ko') # black
	# axes[0].plot(curveStarts, Irmss, 'go') # green
	# axes[0].plot([curveStarts[0], curveStarts[-1]], [0, 0], 'k') # black

	# n=0
	for i in range(0, len(currentCurvesFiltered)):
		curve = np.array(currentCurvesFiltered[i])
		# if (filteredCurrentInFile):
		# 	if (len(cZeros)):
		# 		curve -= cZeros[i]
		# 	else:
		# 		curve -= cZero
		n = curveStarts[i]
		axes[1].plot(range(n, n+len(curve)), curve)

		# Calculate Irms
		ISquareSum = 0
		for c in curve:
			ISquareSum += c**2
		IrmssFiltered.append((ISquareSum * cMultiplier**2 / len(curve))**0.5 * 1000)
		# n += len(curve) + 10

	# axes[1].plot(curveStarts, filteredCurrentRmses,   'ro') # red
	# axes[1].plot(curveStarts, filteredCurrentRmsAvgs, 'bo') # blue
	if (len(cZeros)):
		axes[1].plot(curveStarts, cZeros, 'ko') # black
	# axes[1].plot(curveStarts, IrmssFiltered, 'go') # green
	# axes[1].plot([curveStarts[0], curveStarts[-1]], [0, 0], 'k') # black

	if windowSize:
		plt.title("window=" + str(windowSize))

	# currentCurvesFilteredMore = []


	# plt.figure()
	# n=0
	# for i in range(0, len(voltageCurves)):
	# 	curve = voltageCurves[i]
	# 	plt.plot(range(n, n+len(curve)), curve)
	# 	plt.text(n, 4000, labels[i], rotation=45)
	# 	n += len(curve) + 10

	plt.show()
