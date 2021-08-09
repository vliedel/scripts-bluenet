#!/usr/bin/env python3

"""
Example to upload asset filters via UART or BLE.
"""
import argparse
import os
import asyncio

import crownstone_core
from crownstone_ble import CrownstoneBle
from crownstone_core.packets.assetFilter.FilterCommandPackets import FilterSummariesPacket
from crownstone_core.packets.assetFilter.FilterMetaDataPackets import FilterType
from crownstone_core.packets.assetFilter.builders.AssetFilter import AssetFilter
from crownstone_core.packets.assetFilter.util import AssetFilterMasterCrc
from crownstone_uart import CrownstoneUart

from bluenet_logs import BluenetLogs

import logging

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
bluenetLogs = BluenetLogs()

# Set the dir containing the bluenet source code files.
bluenetLogs.setSourceFilesDir(sourceFilesDir)

# Init the Crownstone UART lib.
uart = CrownstoneUart()

# Init the Crownstone BLE lib.
ble = CrownstoneBle()

print("core version:", crownstone_core.__version__)
print("ble version: ", ble.__version__)
print("uart version:", uart.__version__)

async def main():
	# The try except part is just to catch a control+c to gracefully stop the UART lib.
	try:
		print(f"Listening for logs and using files in \"{sourceFilesDir}\" to find the log formats.")
		await uart.initialize_usb(port=args.device, writeChunkMaxSize=64)

		filterId = 0
		filter = AssetFilter(filterId)
		filter.filterByMacAddress(["01:23:45:67:89:AB", "01:23:45:67:89:CD", "01:23:45:67:89:EF"])
		filter.outputMacRssiReport()
		filter.setProfileId(0)
		print(filter)
		print(filter.serialize())
		print("Filter size:", len(filter.serialize()))
		print("Filter CRC:", filter.getCrc())

		filterId += 1
		filter2 = AssetFilter(filterId)
		filter2.filterByNameWithWildcards("c?w*", complete=False)
		filter2.outputAssetId().basedOnName()
		filter2.setFilterType(FilterType.CUCKOO)
		print(filter2)
		print(filter2.serialize())
		print("Filter size:", len(filter2.serialize()))
		print("Filter CRC:", filter2.getCrc())

		filters = [filter, filter2]

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
		print("\nStopping UART..")
		uart.stop()
		await ble.shutDown()
		print("Stopped")

asyncio.run(main())
