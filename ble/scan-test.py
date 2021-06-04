#!/usr/bin/env python3
import logging
import time
import argparse
from crownstone_ble import CrownstoneBle, ScanBackends, BleEventBus, BleTopics
from crownstone_ble.topics.SystemBleTopics import SystemBleTopics

parser = argparse.ArgumentParser(description='Search for any Crownstone and print their information')
parser.add_argument('--hciIndex', dest='hciIndex', metavar='I', type=int, nargs='?', default=0,
        help='The hci-index of the BLE chip')
parser.add_argument('keyFile',
        help='The json file with key information, expected values: admin, member, guest, basic,' +
        'serviceDataKey, localizationKey, meshApplicationKey, and meshNetworkKey')

args = parser.parse_args()

# logging.basicConfig(format='%(levelname)-7s: %(message)s', level=logging.DEBUG)

# Initialize the Bluetooth Core.
core = CrownstoneBle(hciIndex=args.hciIndex, scanBackend=ScanBackends.Bluepy)
core.loadSettingsFromFile(args.keyFile)

def onAdv(data):
	if data["address"] == "f4:60:ef:35:22:ec":
		print(f"{time.time()} ADV: {data}")
		print()

def onRawAdv(data):
	if data.address == "f4:60:ef:35:22:ec":
		print(f"{time.time()} RAW: {data.getDictionary()}")
		print()

BleEventBus.subscribe(BleTopics.advertisement, onAdv)
BleEventBus.subscribe(SystemBleTopics.rawAdvertisement, onRawAdv)

core.startScanning(100)

# nearestStone = core.getNearestSetupCrownstone(rssiAtLeast=-100, returnFirstAcceptable=True)
# print("Search Results:", nearestStone)
# if nearestStone is not None:

# isSetup = core.isCrownstoneInSetupMode("f4:60:ef:35:22:ec", scanDuration=10, waitUntilInRequiredMode=True)
# print(f"isCrownstoneInSetupMode={isSetup}")

#isNormal = core.isCrownstoneInNormalMode("f4:60:ef:35:22:ec", scanDuration=1000, waitUntilInRequiredMode=True)
#print("====================================")
#print(f"isCrownstoneInNormalMode={isNormal}")
#print("====================================")


print("Core shutdown")
core.shutDown()
