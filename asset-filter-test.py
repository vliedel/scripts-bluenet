#!/usr/bin/env python3

"""
Client to show binary logs.
"""
import time
import argparse
import os
import asyncio

from crownstone_core.packets.assetFilter.FilterDescriptionPackets import *
from crownstone_core.packets.assetFilter.FilterIOPackets import *
from crownstone_core.packets.assetFilter.FilterMetaDataPackets import *
from crownstone_core.util import AssetFilterUtil
from crownstone_core.util.Cuckoofilter import CuckooFilter
from crownstone_uart import CrownstoneUart

from bluenet_logs import BluenetLogs

import logging
#logging.basicConfig(format='%(asctime)s %(levelname)-7s: %(message)s', level=logging.DEBUG)


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
args = argParser.parse_args()

sourceFilesDir = args.sourceFilesDir


# Init bluenet logs, it will listen to events from the Crownstone lib.
bluenetLogs = BluenetLogs()

# Set the dir containing the bluenet source code files.
bluenetLogs.setSourceFilesDir(sourceFilesDir)

# Init the Crownstone UART lib.
uart = CrownstoneUart()

async def main():
	# The try except part is just to catch a control+c to gracefully stop the UART lib.
	try:
		print(f"Listening for logs and using files in \"{sourceFilesDir}\" to find the log formats.")
		await uart.initialize_usb(port=args.device, writeChunkMaxSize=64)
#		logging.DEBUG("init done")

		await asyncio.sleep(1)

		filters = await uart.control.getFilterSummaries()
		print(filters)

		filterInput = FilterInputDescription()
		filterInput.format.type = AdvertisementSubdataType.MAC_ADDRESS

		filterOutputDescription = FilterOutputDescription()
		filterOutputDescription.out_format.type = FilterOutputFormat.MAC_ADDRESS
		# filterOutputDescription.in_format = None

		metadata = FilterMetaData()
		metadata.type = FilterType.CUCKOO
		metadata.profileId = 255
		metadata.inputDescription = filterInput
		metadata.outputDescription = filterOutputDescription

		# Create the cuckoo filter
		max_buckets_log2 = 3
		nests_per_bucket = 4
		load_factor = 0.75
		cuckooFilter = CuckooFilter(max_buckets_log2, nests_per_bucket)
		max_items = cuckooFilter.fingerprintcount()
		num_items_to_test = int(max_items * load_factor)
		for i in range(num_items_to_test):
			if not cuckooFilter.add([i]):
				print("Failed to add to cuckoo filter")
				raise(Exception)
		cuckooFilterData = cuckooFilter.getData()

		filter = AssetFilter()
		filter.metadata = metadata
		filter.filterdata.val = cuckooFilterData

		print("Filter size:", len(filter.getPacket()))

		filterId = 0
		masterVersion = 1
		masterCrc = AssetFilterUtil.get_master_crc_from_filters([AssetFilterAndId(filterId, filter)])

		print(f"Upload filter {filterId}")
		await uart.control.uploadFilter(filterId, filter)
		#
		# await asyncio.sleep(0.1)

		print("Commit")
		await uart.control.commitFilterChanges(masterVersion, masterCrc)

		# Simply keep the program running.
		while True:
			await asyncio.sleep(1)
	except KeyboardInterrupt:
		pass
	finally:
		time.sleep(1)
		print("\nStopping UART..")
		uart.stop()
		print("Stopped")

asyncio.run(main())
