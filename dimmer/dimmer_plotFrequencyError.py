#!/usr/bin/env python3

###################################################################################################################

# Take from the command line as input: a log file consiting of data received over the UART port from a running Crownstone
# Note that the lines referred to below are from the cs_PWM.cpp file.

# To plot:
#   1. Errors in the tick count: refer to the line cs_write("ticks=%u err=%i \r\n", ticks, errTicks)
#   2. Accumulated errors: refer to the line cs_write("medErr=%i errInt=%i P=%i I=%i ticks=%u \r\n", medianError, _zeroCrossOffsetIntegral, deltaP, deltaI, _adjustedMaxTickVal);

###################################################################################################################

import sys
import re
import matplotlib.pyplot as plt

# Read the command line for getting the log file from minicon as input
argLen = len(sys.argv)

if (argLen != 2):
    print("Error in the input! \nUsage: " + sys.argv[0] + " <log-file-name>")
    sys.exit()

# Read the log file and store in a string array
with open(sys.argv[1], 'r') as file:
    data = file.readlines()

# May have to change this based on how the log file is written to.
TICK_ERROR_REGEX_STRING = ".*ticks=([0-9]+) err=([-]*[0-9]+)"
tickErrorPattern = re.compile(TICK_ERROR_REGEX_STRING)

# Reboot regex, just any string that happens only once on boot.
REBOOT_REGEX_STRING = ".*startWritesToFlash.*"
rebootPattern = re.compile(REBOOT_REGEX_STRING)

# Store necessary data in lists
ticks = []
err = []

# Add extracted data to the lists
for s in data:
    matchObj = tickErrorPattern.match(s) 
    if matchObj:
        ticks.append(int(matchObj.group(1)))
        err.append(int(matchObj.group(2)))
    matchObj = rebootPattern.match(s)
    if matchObj:
        ticks.clear()
        err.clear()

# Currently against indices, can be changed to the actual timestamp values
indices = list(range(0, len(ticks)))

# Plot using matplotlib

plt.figure()
tickPlot = plt.gca()
tickPlot.set_title("Tick count")
tickPlot.set_ylabel("ticks")
tickPlot.plot(indices, ticks, 'o')

plt.figure()
errPlot = plt.gca()
errPlot.set_title("Error")
errPlot.set_ylabel("error (ticks)")
errPlot.plot(indices, err, 'o')

plt.show()