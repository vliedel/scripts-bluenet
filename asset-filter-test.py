#!/usr/bin/env python3

"""
Client to show binary logs.
"""
import argparse
import os
import asyncio

from crownstone_core.packets.assetFilter.FilterMetaDataPackets import FilterType
from crownstone_core.packets.assetFilter.builders.AssetFilter import AssetFilter
from crownstone_core.packets.assetFilter.util import AssetFilterMasterCrc
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

		filters = await uart.control.getFilterSummaries()
		print(filters)
		masterVersion = filters.masterVersion

		##############################################################################################
		##################################### Remove all filters #####################################
		##############################################################################################

		print("Remove all filters")
		for f in filters.summaries:
			print(f"    Remove id={f.id}")
			await uart.control.removeFilter(f.id)

		# masterVersion += 1
		# filtersAndIds = []
		# masterCrc = AssetFilterUtil.get_master_crc_from_filters(filtersAndIds)
		# print("Master CRC:", masterCrc)
		# print("Commit")
		# await uart.control.commitFilterChanges(masterVersion, masterCrc)

		#############################################################################################
		##################################### Create new filter #####################################
		#############################################################################################

		filterId = 0
		filter = AssetFilter()
		filter.setFilterId(filterId)
		filter.filterByMacAddress(["01:23:45:67:89:AB", "01:23:45:67:89:CD", "01:23:45:67:89:EF"])
		filter.outputMacRssiReport()
		filter.setProfileId(0)
		print(filter)
		print(filter.toBuffer())
		print("Filter size:", len(filter.toBuffer()))
		print("Filter CRC:", filter.getCrc())

		filterId += 1
		filter2 = AssetFilter()
		filter2.setFilterId(filterId)
		filter2.filterByNameWithWildcards("CR?N")
		filter2.outputAssetId().basedOnName()
		filter2.setFilterType(FilterType.CUCKOO)
		print(filter2)
		print(filter2.toBuffer())
		print("Filter size:", len(filter2.toBuffer()))
		print("Filter CRC:", filter2.getCrc())

		filters = [filter, filter2]


		##########################################################################################
		##################################### Upload filters #####################################
		##########################################################################################

		masterVersion += 1

		for f in filters:
			print(f"Upload filter {f.getFilterId()}")
			await uart.control.uploadFilter(f)
		print("Commit")
		await uart.control.commitFilterChanges(masterVersion, filters)

		# Simply keep the program running.
		while True:
			await asyncio.sleep(0.1)
	except KeyboardInterrupt:
		pass
	finally:
		print("\nStopping UART..")
		uart.stop()
		print("Stopped")

asyncio.run(main())
