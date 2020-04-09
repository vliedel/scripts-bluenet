#!/usr/bin/env python3

# Parses a uart logfile and plots the results.
# Make sure the regex patterns and time format are correct.

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
import json
import sys, os
import re
import datetime

# Config
RTC_CLOCK_FREQ = 32768
MAX_RTC_COUNTER_VAL = 0x00FFFFFF
SAMPLE_TIME_US = 200
NUM_SAMPLES = 100
VOLTAGE_MULTIPLIER = -0.253
CURRENT_MULTIPLIER = 0.0071

#currentRegex = "\[.*\] current: (-?\d+ ?)+" # re doesn't support repeating captures.
samplesPattern      = re.compile("\[.*\] (current|voltage): ([0-9\- ]*)")
timePattern         = re.compile("^\[([^\]]+)\]")
temperaturePattern  = re.compile(".* T=(-?\d+)")
currentPattern      = re.compile(".* Crms=(-?\d+)")
voltagePattern      = re.compile(".* Vrms=(-?\d+)")
powerPattern        = re.compile(".* P=(-?\d+)")
currentZeroPattern  = re.compile(".* C0=(-?\d+)")
forceRelayOnPattern = re.compile(".* forceRelayOn")

timeFormat = "%Y-%m-%d %H:%M:%S.%f"

if (len(sys.argv) != 2):
	print("Usage: " + sys.argv[0] + " <uart-log-file-name>")
	exit(1)

# Read the log file and store in a string array
with open(sys.argv[1], 'r') as file:
	data = file.readlines()

# Start parsing
currentSamples = []
currentSamplesTime = []
voltageSamples = []
voltageSamplesTime = []
temperatures = []
temperaturesTime = []
relays = []
relaysTime = []
currents = []
currentsTime = []
voltages = []
voltagesTime = []
powers = []
powersTime = []
currentZeros = []
currentZerosTime = []

# Calculated values
powerCalcs = []
powerCalcsTime = []
currentMeans = []
currentMeansTime = []
voltageMeans = []
voltageMeansTime = []

timestamp = 0
firstTimestamp = 0
temperature = 0
relay = 0
current = 0
voltage = 0
power = 0
currentZero = 0
voltageZero = 0
powerCalc = 0.0
currentMean = 0.0
voltageMean = 0.0
for line in data:
	addedCurrentSamples = False
	addedVoltageSamples = False
	match = timePattern.match(line)
	if (match):
		time = datetime.datetime.strptime(match.group(1), timeFormat)
		timestamp = time.timestamp()
		if (firstTimestamp == 0):
			firstTimestamp = timestamp
		timestamp -= firstTimestamp
	
	match = samplesPattern.match(line)
	if (match):
		samples = []
		sampleTypeStr = match.group(1)
		sampleStrings = match.group(2).strip().split(' ')
		mean = 0.0
		if (len(sampleStrings) == NUM_SAMPLES):
			for s in sampleStrings:
				try:
					sample = int(s)
				except:
					print("Invalid sample value:", s, "in line:", line)
					exit(1)
				samples.append(sample)
				mean += sample
			mean = mean / len(samples)
			timestamps = timestamp + np.array(range(0, len(samples))) * SAMPLE_TIME_US / 1000 / 1000
			if (sampleTypeStr == "current"):
				currentSamples.append(samples)
				currentSamplesTime.append(timestamps)
				currentMean = mean
				currentMeans.append(currentMean)
				currentMeansTime.append(timestamp)
			else:
				voltageSamples.append(samples)
				voltageSamplesTime.append(timestamps)
				voltageMean = mean
				voltageMeans.append(voltageMean)
				voltageMeansTime.append(timestamp)
				
				# Calculate power
				if (len(currentSamples) > 0):
					voltageZero = 0.0
					for i in range(0, NUM_SAMPLES):
						voltageZero += voltageSamples[-1][i]
					voltageZero = voltageZero / NUM_SAMPLES
					powerCalc = 0
					for i in range(0, NUM_SAMPLES):
						powerCalc = powerCalc + (voltageSamples[-1][i] - voltageZero) * (currentSamples[-1][i] - currentZero)
					powerCalc = powerCalc * VOLTAGE_MULTIPLIER * CURRENT_MULTIPLIER * 1000 / NUM_SAMPLES
					powerCalcs.append(powerCalc)
					powerCalcsTime.append(timestamp)
	
	match = temperaturePattern.match(line)
	if (match):
		temperature = int(match.group(1).strip())
		temperatures.append(temperature)
		temperaturesTime.append(timestamp)
	match = forceRelayOnPattern.match(line)
	if (match):
		relay = 1
		relays.append(relay)
		relaysTime.append(timestamp)
		relays.append(0)
		relaysTime.append(timestamp)
	match = currentPattern.match(line)
	if (match):
		current = int(match.group(1).strip())
		currents.append(current)
		currentsTime.append(timestamp)
	match = voltagePattern.match(line)
	if (match):
		voltage = int(match.group(1).strip())
		voltages.append(voltage)
		voltagesTime.append(timestamp)
	match = powerPattern.match(line)
	if (match):
		power = int(match.group(1).strip())
		powers.append(power)
		powersTime.append(timestamp)
	match = currentZeroPattern.match(line)
	if (match):
		currentZero = int(match.group(1).strip()) / 1000.0
		currentZeros.append(currentZero)
		currentZerosTime.append(timestamp)

# Plot the results
fig = plt.figure()
gs = GridSpec(9, 1)
axs = []
axs.append(fig.add_subplot(gs[0:3, 0]))
for i in range(1, 7):
	axs.append(fig.add_subplot(gs[i+2, 0], sharex=axs[0]))
for i in range(0, 6):
	axs[i].xaxis.set_visible(False)

#fig, axs = plt.subplots(7, 1, sharex=True)
axs[0].plot(currentMeansTime, currentMeans, label="Cmean")
axs[1].plot(voltageMeansTime, voltageMeans, label="Vmean")
#axs[0].plot(np.array(currentSamplesTime).transpose(), np.array(currentSamples).transpose(), label="current")
#axs[0].plot(currentZerosTime, currentZeros)
#axs[1].plot(np.array(voltageSamplesTime).transpose(), np.array(voltageSamples).transpose(), label="voltage")
#axs[2].plot(temperaturesTime, temperatures, label="temperature")
#axs[3].plot(relaysTime, relays, label="forceRelayOn")
#axs[4].plot(currentsTime, currents, label="Irms")
#axs[5].plot(voltagesTime, voltages, label="Vrms")
#axs[6].plot(powersTime, powers, label="P")
#axs[6].plot(powerCalcsTime, powerCalcs, label="Pcalc")

for i in range(2, 7):
	axs[i].legend()

#plt.figure()
#plt.plot(np.array(currentSamplesTime).transpose(), np.array(currentSamples).transpose())
plt.show()
