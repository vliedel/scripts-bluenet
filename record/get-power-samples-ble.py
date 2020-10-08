#!/usr/bin/env python3

import argparse
import time

from crownstone_ble import CrownstoneBle
from crownstone_core.packets.debug.PowerSamplesPacket import PowerSamplesPacket
from crownstone_core.protocol.BluenetTypes import PowerSamplesType
import traceback
import numpy as np
import select
import sys
import json
import datetime

parser = argparse.ArgumentParser(description='Connect to Crownstone and repeatedly get power samples')
parser.add_argument('-H', '--hciIndex', dest='hciIndex', type=int, nargs='?', default=0,
		help='The hci-index of the BLE chip')
parser.add_argument('-N', '--times', dest='numTimes', type=int, nargs='?', default=10,
        help='Number of times to get buffers')
parser.add_argument('-V', '--voltage', dest='voltageGroundTruth', type=float, nargs='?', default=0.0,
		help='The ground truth RMS voltage')
parser.add_argument('-C', '--current', dest='currentGroundTruth', type=float, nargs='?', default=0.0,
		help='The ground truth RMS current')
parser.add_argument('-P', '--power', dest='powerGroundTruth', type=float, nargs='?', default=0.0,
		help='The ground truth RMS real power')
parser.add_argument('-O', '--outputPrefix', dest='outputPrefix', type=str, nargs='?', default="output",
		help='Output filename prefix')
parser.add_argument('keyFile',
		help='The json file with key information, expected values: admin, member, guest, basic,' +
		'serviceDataKey, localizationKey, meshApplicationKey, and meshNetworkKey')
parser.add_argument('bleAddress', type=str,
		help='The BLE address of Crownstone to switch')

args = parser.parse_args()

def calcCurrentOrVoltageRms(samples, zero):
	rms = calcRms(samples - zero, samples - zero)
	return rms

def calcRms(samples1, samples2, squareRoot=True):
	rms = 0.0
	for i in range(0, len(samples1)):
		rms += samples1[i] * samples2[i]
	rms /= len(samples1)
	if (squareRoot):
		return np.sqrt(rms)
	else:
		return rms

def calcZero(samples):
	return np.mean(samples)


def pollKeyboard():
	# dr, dw, de = select.select([sys.stdin], [], [], 0)
	# if not dr == []:
	#     return sys.stdin.read(1)
	return None

def getMap(powerSamplesPacket: PowerSamplesPacket):
	powerSamplesMap = {}
	powerSamplesMap["timestamp"] = powerSamplesPacket.timestamp
	powerSamplesMap["sampleIntervalUs"] = powerSamplesPacket.sampleIntervalUs
	powerSamplesMap["offset"] = powerSamplesPacket.offset
	powerSamplesMap["multiplier"] = powerSamplesPacket.multiplier
	powerSamplesMap["samples"] = powerSamplesPacket.samples
	return powerSamplesMap

# Initialize the Bluetooth Core.
core = CrownstoneBle(hciIndex=args.hciIndex)
core.loadSettingsFromFile(args.keyFile)

try:
	print("Connecting to", args.bleAddress)
	core.connect(args.bleAddress)

	try:
		for i in range(0, args.numTimes):
			output = {}
			output["voltageGroundTruth"] = args.voltageGroundTruth
			output["currentGroundTruth"] = args.currentGroundTruth
			output["powerGroundTruth"] = args.powerGroundTruth

#            print("Retrieving power samples..")

#            powerSamplesUnfiltered = core.debug.getPowerSamples(PowerSamplesType.NOW_UNFILTERED)
#            power = calcPower(powerSamplesUnfiltered)
#            print("Unfiltered:", power)

			powerSamplesFiltered = core.debug.getPowerSamples(PowerSamplesType.NOW_FILTERED)
			voltageSamples = np.array(powerSamplesFiltered[0].samples)
			voltageSamples = (voltageSamples - powerSamplesFiltered[0].offset) * powerSamplesFiltered[0].multiplier
			currentSamples = np.array(powerSamplesFiltered[1].samples)
			currentSamples = (currentSamples - powerSamplesFiltered[1].offset) * powerSamplesFiltered[1].multiplier
			print("Vrms={:8.2f} Voffset={:8.2f} Vrms-corrected={:8.2f}".format(
			      calcCurrentOrVoltageRms(voltageSamples, 0),
			      calcZero(voltageSamples),
			      calcCurrentOrVoltageRms(voltageSamples, calcZero(voltageSamples))
			      ))
			print("Irms={:8.2f} Ioffset={:8.2f} Irms-corrected={:8.2f}".format(
			      calcCurrentOrVoltageRms(currentSamples, 0),
			      calcZero(currentSamples),
			      calcCurrentOrVoltageRms(currentSamples, calcZero(currentSamples))
			      ))
			print("")

			output["localTime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
			output["localTimestamp"] = time.time()
			output["voltage"] = getMap(powerSamplesFiltered[0])
			output["current"] = getMap(powerSamplesFiltered[1])

			key = pollKeyboard()
			if key is not None:
				print("Pressed:", key)

			fileName = args.outputPrefix + "_" + args.bleAddress + ".txt"
			with open(fileName, 'a') as outfile:
				json.dump(output, outfile)
				outfile.write("\n")

	except Exception as err:
		print("Failed to get power samples:", err)
		traceback.print_exc()

	print("Disconnect")
	core.control.disconnect()

except Exception as err:
	print("Failed to connect:", err)



core.shutDown()
