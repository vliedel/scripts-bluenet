#!/usr/bin/env python

""" Capture voltage samples to file """

import time, signal
import json
import select, sys
from BluenetLib import Bluenet, BluenetEventBus, Topics
from BluenetLib.lib.topics.DevTopics import DevTopics

# Declare vars so they can be used globally
bluenet = None
outputFile = None
wroteFirstEntry = False
sigInt = False
outputFilenamePrefix = None
outputFileDir = None

def main():
	# Read config file
	jsonConfigFile = open('config.json', 'r')
	jsonConfigData = json.load(jsonConfigFile)

	# Get optional configs from file
	device =               jsonConfigData.get('device', '/dev/ttyUSB0')
	baudrate =             jsonConfigData.get('baudrate', 230400)
	global outputFilenamePrefix
	outputFilenamePrefix = jsonConfigData.get('outputFilenamePrefix', 'voltage')
	global outputFileDir
	outputFileDir =        jsonConfigData.get('outputFileDir', '.')

	jsonConfigFile.close()

	newOutputFile()

	# Create new instance of Bluenet
	global bluenet
	bluenet = Bluenet(catchSIGINT=False)

	# Set up event listeners
	BluenetEventBus.subscribe(DevTopics.newVoltageData, onSamples)
	BluenetEventBus.subscribe(DevTopics.newAdcConfigPacket, onAdcConfig)
	BluenetEventBus.subscribe(DevTopics.adcRestarted, onAdcRestarted)

	# start listener for SIGINT kill command
	signal.signal(signal.SIGINT, stopAll)

	# Start up the USB bridge
	bluenet.initializeUSB(device, baudrate=baudrate)

	# Need to sleep for some reason
	time.sleep(1)

	# Enable voltage logs
	bluenet._usbDev.setSendVoltageSamples(True)

	while not sigInt:
		inputStr = pollKeyboardEnter()
		if inputStr is not None:
			newOutputFile()



def pollKeyboardEnter():
	# Polls for keyboard input
	# I have no idea how this works, got it from: https://stackoverflow.com/questions/292095/polling-the-keyboard-detect-a-keypress-in-python
	timeout = 0.0001
	try:
		i,o,e = select.select([sys.stdin], [], [], timeout)
		for s in i:
			if s == sys.stdin:
				inputStr = sys.stdin.readline()
				print("input:", inputStr)
				return inputStr
	except InterruptedError:
		return None
	return None



def newOutputFile():
	global outputFile

	closeOutputFile()

	timeStr = time.strftime("%Y-%m-%d--%H-%M-%S")
	outputFilename = outputFilenamePrefix + "-" + timeStr + ".json"
	outputFile = open(outputFileDir + '/' + outputFilename, 'w') # 'w' for overwrite, 'a' for append
	outputFile.write('[\n')
	global wroteFirstEntry
	wroteFirstEntry = False



def closeOutputFile():
	if outputFile is not None:
		outputFile.write('\n]\n')
		outputFile.close()



def onSamples(data):
	print("onSamples:", data)
	jsonStr = json.dumps({'samples': data['data'], 'timestamp': data['timestamp']})
	# json.dump(jsonData, outputFile)
	try:
		global wroteFirstEntry
		if (wroteFirstEntry):
			outputFile.write(',\n')
		wroteFirstEntry = True

		outputFile.write(jsonStr)
	except ValueError:
		print("Failed to write samples")



def onAdcConfig(data):
	print("onAdcConfig:", data)

def onAdcRestarted(data):
	print("onAdcRestart")
	jsonStr = json.dumps({'restart': True})
	try:
		global wroteFirstEntry
		if (wroteFirstEntry):
			outputFile.write(',\n')
		wroteFirstEntry = True

		outputFile.write(jsonStr)
	except ValueError:
		print("Failed to write samples")


# make sure everything is killed and cleaned up on abort.
def stopAll(signal, frame):
	global sigInt
	sigInt = True
	bluenet.stop()
	closeOutputFile()

# Call main
main()
