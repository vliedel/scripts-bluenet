#!/usr/bin/env python3


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


# Initialize the Bluetooth Core.
core = CrownstoneBle(hciIndex=args.hciIndex, scanBackend=ScanBackends.Bluepy)
core.loadSettingsFromFile(args.keyFile)

def onAdv(data):
	if data["address"] == "f4:60:ef:35:22:ec":
		print(f"{time.time()} {data}")

def onRawAdv(data):
	if data.address == "f4:60:ef:35:22:ec":
		print(f"{time.time()} {data.getDictionary()}")

BleEventBus.subscribe(BleTopics.advertisement, onAdv)
BleEventBus.subscribe(SystemBleTopics.rawAdvertisement, onRawAdv)
# core.startScanning(100)

# nearestStone = core.getNearestSetupCrownstone(rssiAtLeast=-100, returnFirstAcceptable=True)
# print("Search Results:", nearestStone)
# if nearestStone is not None:

# isSetup = core.isCrownstoneInSetupMode("f4:60:ef:35:22:ec", scanDuration=10, waitUntilInRequiredMode=True)
# print(f"isCrownstoneInSetupMode={isSetup}")

address = "f4:60:ef:35:22:ec"
isNormal = core.isCrownstoneInNormalMode(address, scanDuration=60, waitUntilInRequiredMode=True)
if isNormal:
	print(f"Connecting to {address}")
	core.connect(address)

	print(f"Factory resetting {address}")
	core.control.commandFactoryReset()
else:
	print(f"{address} is not in normal mode")


print("Core shutdown")
core.shutDown()
