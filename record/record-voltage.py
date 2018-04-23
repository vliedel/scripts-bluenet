#!/usr/bin/env python

""" Capture voltage samples to file """

import time, signal
import json
from BluenetLib import Bluenet, BluenetEventBus, Topics
from BluenetLib.lib.topics.DevTopics import DevTopics

# Declare vars so they can be used globally
bluenet = None
outputFile = None
wroteFirstEntry = False

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
	outputFile.write('[\n')

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



# make sure everything is killed and cleaned up on abort.
def stopAll(signal, frame):
	bluenet.stop()
	if (outputFile is not None):
		outputFile.write('\n]\n')
		outputFile.close()

# Call main
main()
