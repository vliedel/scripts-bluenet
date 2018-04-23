#!/usr/bin/env python

""" Capture voltage samples to file """

import time, signal
import json
from BluenetLib import Bluenet, BluenetEventBus, Topics
from BluenetLib.lib.topics.DevTopics import DevTopics

# Declare vars so they can be used globally
bluenet = None
outputFile = None

def main():
	# Read config file
	jsonConfigFile = open('config.json', 'r')
	jsonConfigData = json.load(jsonConfigFile)

	# Get optional configs from file
	device =         jsonConfigData.get('device', '/dev/ttyUSB0')
	baudrate =       jsonConfigData.get('baudrate', 230400)
	outputFilename = jsonConfigData.get('outputFilename', 'voltage.json')

	jsonConfigFile.close()

	# Output file
	global outputFile
	outputFile = open(outputFilename, 'w') # 'w' for overwrite, 'a' for append

	# Create new instance of Bluenet
	global bluenet
	bluenet = Bluenet(catchSIGINT=False)

	# Set up event listeners
	BluenetEventBus.subscribe(DevTopics.newVoltageData, onSamples)
	BluenetEventBus.subscribe(DevTopics.newAdcConfigPacket, onAdcConfig)

	# start listener for SIGINT kill command
	signal.signal(signal.SIGINT, stopAll)

	# Start up the USB bridge
	bluenet.initializeUSB(device, baudrate=baudrate)

	# Need to sleep for some reason
	time.sleep(1)

	# Enable voltage logs
	bluenet._usbDev.setSendVoltageSamples(True)


# make sure everything is killed and cleaned up on abort.
def stopAll(signal, frame):
	bluenet.stop()
	if (outputFile is not None):
		outputFile.close()

def onSamples(data):
	print("onSamples:", data)
	jsonStr = json.dumps({'samples': data['data']})
	# json.dump(jsonData, outputFile)
	outputFile.write(jsonStr)
	outputFile.write('\n')

def onAdcConfig(data):
	print("onAdcConfig:", data)


# Call main
main()
