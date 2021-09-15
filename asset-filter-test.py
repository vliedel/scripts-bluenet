#!/usr/bin/env python3

"""
Example to upload asset filters via UART or BLE.
"""
import argparse
import os
import asyncio
from datetime import datetime

import crownstone_core
from crownstone_ble import CrownstoneBle
from crownstone_core import Conversion
from crownstone_core.packets.assetFilter.FilterMetaDataPackets import FilterType
from crownstone_core.packets.assetFilter.builders.AssetFilter import AssetFilter
from crownstone_uart import CrownstoneUart, UartEventBus, UartTopics

from bluenet_logs import BluenetLogs

import logging

from crownstone_uart.core.uart.uartPackets.AssetMacReport import AssetMacReport
from crownstone_uart.core.uart.uartPackets.NearestCrownstones import NearestCrownstoneTrackingUpdate

from Crc32 import crc32_table

mac_addresses = [
	"d0:2b:1d:2c:de:0a",
	"d0:2b:1d:2c:de:0a",
	"d0:d2:58:31:65:94",
	"f3:4f:c7:ab:27:37",
	"e4:b2:2c:85:a9:34",
	"f4:1e:80:49:d7:25",
	"db:89:c2:4b:d6:f3",
	"d0:d2:58:31:65:94",
	"cd:01:f1:c0:68:12",
	"e4:5c:b2:ec:1d:20",
	"d0:2b:1d:2c:de:0a",
	"d1:7d:73:67:3f:d7",
	"e3:4a:7e:46:58:01",
	"da:52:37:cb:06:5b",
	"f4:1e:80:49:d7:25",
	"e4:5c:b2:ec:1d:20",
	"d0:2b:1d:2c:de:0a",
	"e4:b2:2c:85:a9:34",
	"e3:4a:7e:46:58:01",
	"e9:5f:db:b9:af:f1",
	"df:7d:88:83:f9:ea",
	"d7:1d:0e:e1:d5:2a",
	"cb:69:b8:69:14:6e",
	"e7:73:7a:f4:f0:42",
	"d0:d2:58:31:65:94",
	"d1:7d:73:67:3f:d7",
	"db:89:c2:4b:d6:f3",
	"f5:23:aa:82:ee:20",
	"fd:fc:93:f8:97:ba",
	"d0:db:21:1d:39:ca",
	"fd:d9:0e:9a:99:9a",
	"fb:42:55:78:cd:92",
	"cd:01:f1:c0:68:12",
	"d0:2b:1d:2c:de:0a",
	"d0:30:f7:32:b3:07",
	"e3:4a:7e:46:58:01",
	"f3:4f:c7:ab:27:37",
	"cd:01:f1:c0:68:12",
	"df:a6:b0:75:9a:9e",
	"d1:7d:73:67:3f:d7",
	"e8:3e:ab:e9:e0:1d",
	"e9:5f:db:b9:af:f1",
	"cf:41:34:d3:b2:3e",
	"e0:7f:01:13:fe:b8",
	"d0:2b:1d:2c:de:0a",
	"e9:5f:db:b9:af:f1",
	"e7:73:7a:f4:f0:42",
	"fb:42:55:78:cd:92",
	"d0:d2:58:31:65:94",
	"cf:41:34:d3:b2:3e",
	"e0:7f:01:13:fe:b8",
	"db:89:c2:4b:d6:f3",
	"c5:4f:b7:31:56:e2",
	"cb:69:b8:69:14:6e",
	"e4:b2:2c:85:a9:34",
	"f5:23:aa:82:ee:20",
	"fd:fc:93:f8:97:ba",
	"df:7d:88:83:f9:ea",
	"d9:df:98:98:7b:32",
	"f3:4f:c7:ab:27:37",
	"cd:01:f1:c0:68:12",
	"e3:4a:7e:46:58:01",
	"d7:1d:0e:e1:d5:2a",
	"db:89:c2:4b:d6:f3",
	"e4:b2:2c:85:a9:34",
	"fd:fc:93:f8:97:ba",
	"d0:db:21:1d:39:ca",
	"cd:01:f1:c0:68:12",
	"cb:69:b8:69:14:6e",
	"e7:73:7a:f4:f0:42",
	"e4:5c:b2:ec:1d:20",
	"db:89:c2:4b:d6:f3",
	"e3:4a:7e:46:58:01",
	"fd:fc:93:f8:97:ba",
	"fb:42:55:78:cd:92",
	"d0:d2:58:31:65:94",
	"cb:69:b8:69:14:6e",
	"e4:b2:2c:85:a9:34",
	"d0:2b:1d:2c:de:0a",
	"da:52:37:cb:06:5b",
	"e7:73:7a:f4:f0:42",
	"f8:73:8c:8f:e4:e8",
	"d0:d2:58:31:65:94",
	"e0:7f:01:13:fe:b8",
	"e4:5c:b2:ec:1d:20",
	"f5:23:aa:82:ee:20",
	"e3:4a:7e:46:58:01",
	"fd:fc:93:f8:97:ba",
	"da:52:37:cb:06:5b",
	"ee:4d:80:13:50:f0",
	"fb:42:55:78:cd:92",
	"cb:69:b8:69:14:6e",
	"fb:eb:93:3c:f4:ed",
	"d0:db:21:1d:39:ca",
	"cd:01:f1:c0:68:12",
	"d0:2b:1d:2c:de:0a",
	"db:89:c2:4b:d6:f3",
	"fd:fc:93:f8:97:ba",
	"d0:d2:58:31:65:94",
	"e4:5c:b2:ec:1d:20",
	"dc:ae:89:6e:1c:6f",
	"d0:2b:1d:2c:de:0a",
	"e7:73:7a:f4:f0:42",
	"d0:d2:58:31:65:94",
	"f3:4f:c7:ab:27:37",
	"db:89:c2:4b:d6:f3",
	"fd:fc:93:f8:97:ba",
	"cf:41:34:d3:b2:3e",
	"e5:e0:f9:f1:74:08",
	"e4:5c:b2:ec:1d:20",
	"c5:4f:b7:31:56:e2",
	"e4:b2:2c:85:a9:34",
	"e3:4a:7e:46:58:01",
	"e7:73:7a:f4:f0:42",
	"d0:db:21:1d:39:ca",
	"cf:d1:a8:65:d3:6a",
	"e5:e0:f9:f1:74:08",
	"e7:a4:cd:36:b1:26",
	"cd:01:f1:c0:68:12",
	"d0:2b:1d:2c:de:0a",
	"db:89:c2:4b:d6:f3",
	"f5:23:aa:82:ee:20",
	"fb:42:55:78:cd:92",
	"e3:4a:7e:46:58:01",
	"fd:d9:0e:9a:99:9a",
	"e7:73:7a:f4:f0:42",
	"e8:3e:ab:e9:e0:1d",
	"e3:4a:7e:46:58:01",
	"fd:d9:0e:9a:99:9a",
	"d0:db:21:1d:39:ca",
	"e5:e0:f9:f1:74:08",
	"cd:01:f1:c0:68:12",
	"c5:4f:b7:31:56:e2",
	"db:89:c2:4b:d6:f3",
	"d1:7d:73:67:3f:d7",
	"fd:fc:93:f8:97:ba",
	"cd:01:f1:c0:68:12",
	"d0:d2:58:31:65:94",
	"e4:b2:2c:85:a9:34",
	"db:89:c2:4b:d6:f3",
	"da:52:37:cb:06:5b",
	"d0:2b:1d:2c:de:0a",
	"e8:3e:ab:e9:e0:1d",
	"e3:4a:7e:46:58:01",
	"ee:4d:80:13:50:f0",
	"e7:a4:cd:36:b1:26",
	"e4:5c:b2:ec:1d:20",
	"f5:23:aa:82:ee:20",
	"db:89:c2:4b:d6:f3",
	"e3:4a:7e:46:58:01",
	"d0:30:f7:32:b3:07",
	"cf:41:34:d3:b2:3e",
	"cd:01:f1:c0:68:12",
	"e5:e0:f9:f1:74:08",
	"e4:b2:2c:85:a9:34",
	"d0:30:f7:32:b3:07",
	"cd:01:f1:c0:68:12",
	"e7:a4:cd:36:b1:26",
	"dc:ae:89:6e:1c:6f",
	"cb:69:b8:69:14:6e",
	"e4:b2:2c:85:a9:34",
	"e8:3e:ab:e9:e0:1d",
	"df:a6:b0:75:9a:9e",
	"f5:23:aa:82:ee:20",
	"cf:d1:a8:65:d3:6a",
	"cf:41:34:d3:b2:3e",
	"d0:db:21:1d:39:ca",
	"e7:73:7a:f4:f0:42",
	"df:7d:88:83:f9:ea",
	"f8:73:8c:8f:e4:e8",
	"e5:e0:f9:f1:74:08",
	"e4:5c:b2:ec:1d:20",
	"e0:7f:01:13:fe:b8",
	"ef:ad:b0:22:78:ab",
	"fb:42:55:78:cd:92",
	"e4:5c:b2:ec:1d:20",
	"e0:7f:01:13:fe:b8",
	"cb:69:b8:69:14:6e",
	"d1:7d:73:67:3f:d7",
	"d0:db:21:1d:39:ca",
	"f5:23:aa:82:ee:20",
	"ee:4d:80:13:50:f0",
	"f8:73:8c:8f:e4:e8",
	"d0:d2:58:31:65:94",
	"f5:23:aa:82:ee:20",
	"e3:4a:7e:46:58:01",
	"db:89:c2:4b:d6:f3",
	"fd:d9:0e:9a:99:9a",
	"f4:1e:80:49:d7:25",
	"d7:1d:0e:e1:d5:2a",
	"e4:5c:b2:ec:1d:20",
	"d7:1d:0e:e1:d5:2a",
	"e4:5c:b2:ec:1d:20",
	"d0:2b:1d:2c:de:0a",
	"f5:23:aa:82:ee:20",
	"e3:4a:7e:46:58:01",
	"cd:01:f1:c0:68:12",
	"fb:42:55:78:cd:92",
	"fd:d9:0e:9a:99:9a",
	"e5:e0:f9:f1:74:08",
	"cb:69:b8:69:14:6e",
	"fd:fc:93:f8:97:ba",
	"d0:30:f7:32:b3:07",
	"f8:73:8c:8f:e4:e8",
	"d0:2b:1d:2c:de:0a",
	"e4:5c:b2:ec:1d:20",
	"fd:fc:93:f8:97:ba",
	"f5:23:aa:82:ee:20",
	"db:89:c2:4b:d6:f3",
	"e5:e0:f9:f1:74:08",
	"e0:7f:01:13:fe:b8",
	"e4:b2:2c:85:a9:34",
	"e3:4a:7e:46:58:01",
	"e7:73:7a:f4:f0:42",
	"f8:73:8c:8f:e4:e8",
	"e0:7f:01:13:fe:b8",
	"e3:4a:7e:46:58:01",
	"db:89:c2:4b:d6:f3",
	"f4:1e:80:49:d7:25",
	"fb:42:55:78:cd:92",
	"d0:2b:1d:2c:de:0a",
	"cb:69:b8:69:14:6e",
	"cf:41:34:d3:b2:3e",
	"d1:7d:73:67:3f:d7",
	"e7:73:7a:f4:f0:42",
	"fb:42:55:78:cd:92",
	"d7:1d:0e:e1:d5:2a",
	"e4:5c:b2:ec:1d:20",
	"e0:7f:01:13:fe:b8",
	"fd:fc:93:f8:97:ba",
	"d1:7d:73:67:3f:d7",
	"d0:db:21:1d:39:ca",
	"db:89:c2:4b:d6:f3",
	"d0:d2:58:31:65:94",
	"d7:1d:0e:e1:d5:2a",
	"f4:1e:80:49:d7:25",
	"ee:4d:80:13:50:f0",
	"e9:5f:db:b9:af:f1",
	"fd:d9:0e:9a:99:9a",
	"d0:d2:58:31:65:94",
	"d7:1d:0e:e1:d5:2a",
	"d0:30:f7:32:b3:07",
	"fd:fc:93:f8:97:ba",
	"f5:23:aa:82:ee:20",
	"cf:d1:a8:65:d3:6a",
	"db:89:c2:4b:d6:f3",
	"f8:73:8c:8f:e4:e8",
	"e9:5f:db:b9:af:f1",
	"e5:e0:f9:f1:74:08",
	"d1:7d:73:67:3f:d7",
	"e3:4a:7e:46:58:01",
	"da:52:37:cb:06:5b",
	"cf:41:34:d3:b2:3e",
	"ee:4d:80:13:50:f0",
	"fd:d9:0e:9a:99:9a",
	"e9:5f:db:b9:af:f1",
	"d0:d2:58:31:65:94",
	"d7:1d:0e:e1:d5:2a",
	"cb:69:b8:69:14:6e",
	"da:52:37:cb:06:5b",
	"e7:73:7a:f4:f0:42",
	"ee:4d:80:13:50:f0",
	"cf:41:34:d3:b2:3e",
	"df:7d:88:83:f9:ea",
	"e4:5c:b2:ec:1d:20",
	"f5:23:aa:82:ee:20",
	"cf:d1:a8:65:d3:6a",
	"d7:1d:0e:e1:d5:2a",
	"dc:ae:89:6e:1c:6f",
	"e4:b2:2c:85:a9:34",
	"cf:d1:a8:65:d3:6a",
	"fd:d9:0e:9a:99:9a",
	"f8:73:8c:8f:e4:e8",
	"e5:e0:f9:f1:74:08",
	"f3:4f:c7:ab:27:37",
	"db:89:c2:4b:d6:f3",
	"e0:7f:01:13:fe:b8",
	"cb:69:b8:69:14:6e",
	"ef:ad:b0:22:78:ab",
	"d1:7d:73:67:3f:d7",
	"cf:d1:a8:65:d3:6a",
	"f4:1e:80:49:d7:25",
	"cd:01:f1:c0:68:12",
	"fb:42:55:78:cd:92",
	"d7:1d:0e:e1:d5:2a",
	"d0:2b:1d:2c:de:0a",
	"e3:22:9a:68:5d:ea",
	"e4:b2:2c:85:a9:34",
	"e3:4a:7e:46:58:01",
	"f5:23:aa:82:ee:20",
	"f8:73:8c:8f:e4:e8",
	"ee:4d:80:13:50:f0",
	"d0:d2:58:31:65:94",
	"d7:1d:0e:e1:d5:2a",
	"d0:2b:1d:2c:de:0a",
	"e3:4a:7e:46:58:01",
	"e7:73:7a:f4:f0:42",
	"db:89:c2:4b:d6:f3",
	"cf:41:34:d3:b2:3e",
	"df:7d:88:83:f9:ea",
	"e4:5c:b2:ec:1d:20",
	"dc:ae:89:6e:1c:6f",
	"cb:69:b8:69:14:6e",
	"f8:73:8c:8f:e4:e8",
	"d9:df:98:98:7b:32",
	"e9:5f:db:b9:af:f1",
	"fd:d9:0e:9a:99:9a",
	"cd:01:f1:c0:68:12",
	"d0:2b:1d:2c:de:0a",
	"e4:5c:b2:ec:1d:20",
	"dc:ae:89:6e:1c:6f",
	"e3:4a:7e:46:58:01",
	"e7:73:7a:f4:f0:42",
	"d0:db:21:1d:39:ca",
	"cf:41:34:d3:b2:3e",
	"d0:d2:58:31:65:94",
	"e0:7f:01:13:fe:b8",
	"f3:4f:c7:ab:27:37",
	"f5:23:aa:82:ee:20",
	"fb:eb:93:3c:f4:ed",
	"db:89:c2:4b:d6:f3",
	"ee:4d:80:13:50:f0",
	"fd:d9:0e:9a:99:9a",
	"cf:41:34:d3:b2:3e",
	"e4:b2:2c:85:a9:34",
	"d1:7d:73:67:3f:d7",
	"e9:5f:db:b9:af:f1",
	"d0:db:21:1d:39:ca",
	"cd:01:f1:c0:68:12",
	"d0:d2:58:31:65:94",
	"d7:1d:0e:e1:d5:2a",
	"e3:22:9a:68:5d:ea",
	"e0:7f:01:13:fe:b8",
	"e4:b2:2c:85:a9:34",
	"ef:ad:b0:22:78:ab",
	"fd:fc:93:f8:97:ba",
	"e3:4a:7e:46:58:01",
	"fb:eb:93:3c:f4:ed",
	"e5:e0:f9:f1:74:08",
	"e9:5f:db:b9:af:f1",
	"cd:01:f1:c0:68:12",
	"f5:23:aa:82:ee:20",
	"fd:d9:0e:9a:99:9a",
	"d7:1d:0e:e1:d5:2a",
	"e4:5c:b2:ec:1d:20",
	"d1:7d:73:67:3f:d7",
	"fd:fc:93:f8:97:ba",
	"e3:4a:7e:46:58:01",
	"e7:73:7a:f4:f0:42",
	"ee:4d:80:13:50:f0",
	"e4:5c:b2:ec:1d:20",
	"d7:1d:0e:e1:d5:2a",
	"d0:2b:1d:2c:de:0a",
	"fd:fc:93:f8:97:ba",
	"d1:7d:73:67:3f:d7",
	"e3:4a:7e:46:58:01",
	"db:89:c2:4b:d6:f3",
	"e9:5f:db:b9:af:f1",
	"cf:41:34:d3:b2:3e",
	"d0:d2:58:31:65:94",
	"fd:d9:0e:9a:99:9a",
	"d0:2b:1d:2c:de:0a",
	"e4:b2:2c:85:a9:34",
	"f3:4f:c7:ab:27:37",
	"da:52:37:cb:06:5b",
	"fb:eb:93:3c:f4:ed",
	"d9:df:98:98:7b:32",
	"e7:a4:cd:36:b1:26",
	"e0:7f:01:13:fe:b8",
	"f5:23:aa:82:ee:20",
	"e3:4a:7e:46:58:01",
	"db:89:c2:4b:d6:f3",
	"fb:42:55:78:cd:92",
	"d0:d2:58:31:65:94",
	"d7:1d:0e:e1:d5:2a",
	"cb:69:b8:69:14:6e",
	"e0:7f:01:13:fe:b8",
	"da:52:37:cb:06:5b",
	"e3:4a:7e:46:58:01",
	"e7:73:7a:f4:f0:42",
	"d0:2b:1d:2c:de:0a",
	"d0:d2:58:31:65:94",
	"ee:4d:80:13:50:f0",
	"cd:01:f1:c0:68:12",
]
#mac_addresses = mac_addresses[0:50]

assetIds = {}
for mac in mac_addresses:
	crc = crc32_table(Conversion.address_to_uint8_array(mac))
	# assetIds[mac] = [
	# 	(crc >>  0) & 0xFF,
	# 	(crc >>  8) & 0xFF,
	# 	(crc >> 16) & 0xFF]
	assetIds[mac] = crc & 0x00FFFFFF

unique_and_sorted_mac_addresses = []
for mac in mac_addresses:
	if mac not in unique_and_sorted_mac_addresses:
		unique_and_sorted_mac_addresses.append(mac)
unique_and_sorted_mac_addresses.sort()
print(f"{len(unique_and_sorted_mac_addresses)} unique MAC addresses")

received_mac_addresses = {}
for mac in mac_addresses:
	received_mac_addresses[mac] = []


defaultSourceFilesDir = os.path.abspath(f"{os.path.dirname(os.path.abspath(__file__))}/../source")

argParser = argparse.ArgumentParser(description="Client to show binary logs")
argParser.add_argument('--sourceFilesDir',
                       '-s',
                       dest='sourceFilesDir',
                       metavar='path',
                       type=str,
                       default=f"{defaultSourceFilesDir}",
                       help='The path with the bluenet source code files on your system.')
argParser.add_argument('--device',
                       '-d',
                       dest='device',
                       metavar='path',
                       type=str,
                       default=None,
                       help='The UART device to use, for example: /dev/ttyACM0')
argParser.add_argument('--address',
                       '-a',
                       dest='address',
                       type=str,
                       default=None,
                       help='The MAC address/handle of the Crownstone you want to connect to')
argParser.add_argument('--verbose',
                       '-v',
                       dest='verbose',
                       action='store_true',
                       help='Verbose output.')
args = argParser.parse_args()

if args.verbose:
	logging.basicConfig(format='%(asctime)s %(levelname)-7s: %(message)s', level=logging.DEBUG)
else:
	logging.basicConfig(format='%(asctime)s %(levelname)-7s: %(message)s', level=logging.INFO)


sourceFilesDir = args.sourceFilesDir


# Init bluenet logs, it will listen to events from the Crownstone lib.
# bluenetLogs = BluenetLogs()

# Set the dir containing the bluenet source code files.
# bluenetLogs.setSourceFilesDir(sourceFilesDir)

# Init the Crownstone UART lib.
uart = CrownstoneUart()

# Init the Crownstone BLE lib.
ble = CrownstoneBle()

print("core version:", crownstone_core.__version__)
print("ble version: ", ble.__version__)
print("uart version:", uart.__version__)

async def main():
	# The try except part is just to catch a control+c to gracefully stop the libs.
	try:
		print(f"Listening for logs and using files in \"{sourceFilesDir}\" to find the log formats.")
		await uart.initialize_usb(port=args.device, writeChunkMaxSize=64)

		def onAssetMac(report: AssetMacReport):
			print(f"onAssetMac mac={report.assetMacAddress}")

		def onAssetId(report: NearestCrownstoneTrackingUpdate):
			print(f"onAssetId id={report.assetId}")

			found = False
			for mac, assetId in assetIds.items():
				if assetId == report.assetId:
					found = True
					received_mac_addresses[mac].append(datetime.now())

					# Output a format that the log parser can handle.
					# Example: [2021-06-28 13:42:03.142532] asset mac=60:c0:bf:27:e5:67 scanned by id=96
					timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")
					print(f"{timestamp} asset mac={mac} scanned by id={report.crownstoneId}")
					break
			if not found:
				print("Asset not found")

			# print(f"  MAC={mac_addresses_in_filter[report.assetId]}")

		UartEventBus.subscribe(UartTopics.assetTrackingReport, onAssetMac)
		UartEventBus.subscribe(UartTopics.nearestCrownstoneTrackingUpdate, onAssetId)

		filterId = 0
		filter = AssetFilter(filterId)
		filter.filterByMacAddress(["01:23:45:67:89:AB", "01:23:45:67:89:CD"])
		filter.outputMacRssiReport()
		filter.setProfileId(0)
		print(filter)
		print(filter.serialize())
		print("Filter size:", len(filter.serialize()))
		print("Filter CRC:", filter.getCrc())

		filterId += 1
		filter2 = AssetFilter(filterId)
		filter2.filterByNameWithWildcards("C?W*", complete=False)
		# filter2.outputAssetId().basedOnName()
		filter2.outputMacRssiReport()
		filter2.setFilterType(FilterType.CUCKOO)
		print(filter2)
		print(filter2.serialize())
		print("Filter size:", len(filter2.serialize()))
		print("Filter CRC:", filter2.getCrc())

		filterId += 1
		filter3 = AssetFilter(filterId)
		filter3.filterByMacAddress(mac_addresses)
		# filter3.outputAssetId().basedOnName()
		filter3.outputAssetId().basedOnMac()
		# filter3.outputMacRssiReport()
		filter3.setFilterType(FilterType.CUCKOO)
		print(filter3)
		print(filter3.serialize())
		print("Filter size:", len(filter3.serialize()))
		print("Filter CRC:", filter3.getCrc())

		filters = [filter, filter2, filter3]

		if args.address is not None:
			print("Set filters via BLE.")
			await ble.connect(args.address)
			masterVersion = await ble.control.setFilters(filters)
			await ble.disconnect()
		else:
			print("Set filters via UART.")
			masterVersion = await uart.control.setFilters(filters)
		print("Master version:", masterVersion)

		# Simply keep the program running.
		while True:
			await asyncio.sleep(0.1)
	except KeyboardInterrupt:
		pass
	finally:
		for mac, timestamps in received_mac_addresses.items():
			print(f"{mac} received {len(timestamps)} times")
			if len(timestamps) > 1:
				dts = []
				for i in range(1, len(timestamps)):
					dt = (timestamps[i] - timestamps[i - 1]).total_seconds()
					dts.append(dt)
				# print(f"  dts={dts}")

		print("\nStopping UART..")
		uart.stop()
		await ble.shutDown()
		print("Stopped")

asyncio.run(main())
