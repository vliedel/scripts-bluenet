#!/usr/bin/env python3

"""
Capture voltage samples to file.

Assumes there is a file "config.json" with optional:
  device:               UART tty device.
  baudrate:             UART baudrate.
  outputFilenamePrefix: Prefix of the output file names.
  outputFileDir:        Directory to put the output files.
  readStdin:            Whether to read std input
"""

import time, signal
import json
import select, sys

from crownstone_uart import CrownstoneUart, UartEventBus, UartTopics
from crownstone_uart.topics.DevTopics import DevTopics

# Declare vars so they can be used globally
crownstone = None
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
	readStdin =            jsonConfigData.get('readStdin', True)

	jsonConfigFile.close()

	newOutputFile()

	# Create new instance of Crownstone UART.
	global crownstone
	crownstone = CrownstoneUart()

	# Set up event listeners
	UartEventBus.subscribe(DevTopics.newVoltageData, onSamples)
	UartEventBus.subscribe(DevTopics.newAdcConfigPacket, onAdcConfig)
	UartEventBus.subscribe(DevTopics.adcRestarted, onAdcRestarted)
	UartEventBus.subscribe(DevTopics.uartNoise, onUartNoise)

	# start listener for SIGINT kill command
	signal.signal(signal.SIGINT, stopAll)

	# Start up the USB bridge
	crownstone.initialize_usb_sync()

	# Need to sleep for some reason
	time.sleep(1)

	# Enable voltage logs
	crownstone._usbDev.setSendVoltageSamples(True)

	while not sigInt:
		if (readStdin):
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
		print("Failed to write")

def onUartNoise(data):
	print("onUartNoise")
	jsonStr = json.dumps({'uartNoise': True})
	try:
		global wroteFirstEntry
		if (wroteFirstEntry):
			outputFile.write(',\n')
		wroteFirstEntry = True

		outputFile.write(jsonStr)
	except ValueError:
		print("Failed to write")

# make sure everything is killed and cleaned up on abort.
def stopAll(signal, frame):
	global sigInt
	sigInt = True
	crownstone.stop()
	closeOutputFile()

# Call main
main()
