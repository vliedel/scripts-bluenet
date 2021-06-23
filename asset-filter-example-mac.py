#!/usr/bin/env python3

"""
Example to upload a filter with MAC addresses.
"""
import math
import argparse
import os
import asyncio

from crownstone_core.packets.assetFilter.FilterMetaDataPackets import *
from crownstone_core.util import AssetFilterUtil
from crownstone_core.util.AssetFilterUtil import get_filter_crc
from crownstone_core.util.Cuckoofilter import CuckooFilter
from crownstone_uart import CrownstoneUart
import itertools

from bluenet_logs import BluenetLogs

import logging
#logging.basicConfig(format='%(asctime)s %(levelname)-7s: %(message)s', level=logging.DEBUG)


defaultSourceFilesDir = os.path.abspath(f"{os.path.dirname(os.path.abspath(__file__))}/../source")

argParser = argparse.ArgumentParser(description="Client to show binary logs")
argParser.add_argument('--assetAddress',
                       '-a',
                       dest='assetMacAddresses',
                       metavar='MAC',
                       type=str,
                       nargs='+',
                       required=True,
                       help='The MAC addresses of the assets, for example: 00:11:22:33:44:55 AA:BB:CC:66:77:88')
argParser.add_argument('--device',
                       '-d',
                       dest='device',
                       metavar='path',
                       type=str,
                       default=None,
                       help='The UART device to use, for example: /dev/ttyACM0')
argParser.add_argument('--sourceFilesDir',
                       '-s',
                       dest='sourceFilesDir',
                       metavar='path',
                       type=str,
                       default=f"{defaultSourceFilesDir}",
                       help='The path with the bluenet source code files on your system.')
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

		filters = await uart.control.getFilterSummaries()
		# print(filters)
		masterVersion = filters.masterVersion.val

		##############################################################################################
		##################################### Remove all filters #####################################
		##############################################################################################

		print("Remove all filters")
		# TODO: getting filter IDs doesn't work?
		for f in filters.summaries.val:
			print(f"    Remove id={f.filterId}")
			await uart.control.removeFilter(f.filterId)
		# for f in [0, 1]:
		# 	await uart.control.removeFilter(f)

		masterVersion += 1
		filtersAndIds = []
		masterCrc = AssetFilterUtil.get_master_crc_from_filters(filtersAndIds)
		print("Master CRC:", masterCrc)
		print("Commit")
		await uart.control.commitFilterChanges(masterVersion, masterCrc)

		#############################################################################################
		##################################### Create new filter #####################################
		#############################################################################################

		filter = AssetFilter()

		filterInput = FilterInputDescription()
		filterInput.format.type = AdvertisementSubdataType.MAC_ADDRESS

		filterOutputDescription = FilterOutputDescription()
		filterOutputDescription.out_format.type = FilterOutputFormat.MAC_ADDRESS
		# filterOutputDescription.in_format = None

		metadata = FilterMetaData()

		# Using the EXACT_MATCH filter takes up more space, but has no false positives.
		metadata.type = FilterType.EXACT_MATCH

		# Setting profile ID 0 will make the asset also trigger behaviours.
		metadata.profileId = 0

		metadata.inputDescription = filterInput
		metadata.outputDescription = filterOutputDescription
		filter.metadata = metadata

		print(f"MACs={args.assetMacAddresses}")
		macAddressesAsBytes = []
		for a in args.assetMacAddresses:
			print(f"Adding asset MAC {a} to filter")
			buf = Conversion.address_to_uint8_array(a)
			if not buf:
				raise Exception(f"Invalid MAC: {a}")
			macAddressesAsBytes.append(list(buf))

		if metadata.type == FilterType.CUCKOO:
			# Create the cuckoo filter
			max_buckets_log2 = int(math.log2(len(macAddressesAsBytes))) + 1
			nests_per_bucket = 2
			cuckooFilter = CuckooFilter(max_buckets_log2, nests_per_bucket)
			max_items = cuckooFilter.fingerprintcount()
			for a in macAddressesAsBytes:
				if not cuckooFilter.add(a):
					print("Failed to add to cuckoo filter")
					raise Exception("Failed to add to cuckoo filter")
			cuckooFilterData = cuckooFilter.getData()
			filter.filterdata.val = cuckooFilterData

		elif metadata.type == FilterType.EXACT_MATCH:
			# Create the exact filter
			exactFilter = ExactMatchFilterData(len(macAddressesAsBytes), 6)
			exactFilter.itemArray.val = list(itertools.chain.from_iterable(macAddressesAsBytes))
			filter.filterdata.val = exactFilter

		else:
			raise Exception("Invalid filter type")

		print("Filter size:", len(filter.getPacket()))
		print("Filter CRC:", get_filter_crc(filter))


		###########################################################################################
		##################################### Uploade filters #####################################
		###########################################################################################

		filters = [filter]

		filterId = 0
		masterVersion += 1

		filtersAndIds = []
		for f in filters:
			filtersAndIds.append(AssetFilterAndId(filterId, filter))
			filterId += 1

		masterCrc = AssetFilterUtil.get_master_crc_from_filters(filtersAndIds)
		print("Master CRC:", masterCrc)
		print("Master version:", masterVersion)

		filterId = 0
		for f in filters:
			print(f"Upload filter {filterId}")
			await uart.control.uploadFilter(filterId, f)
			filterId += 1
		print("Commit")
		await uart.control.commitFilterChanges(masterVersion, masterCrc)
		print("Done!")

		# Simply keep the program running.
		while True:
			await asyncio.sleep(0.1)
	except KeyboardInterrupt:
		pass
	finally:
		# time.sleep(1)
		print("\nStopping UART..")
		uart.stop()
		print("Stopped")

asyncio.run(main())
