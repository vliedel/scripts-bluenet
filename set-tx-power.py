#!/usr/bin/env python3

"""
Client to show binary logs.
"""
import random
import time
import argparse
import os
import asyncio

from crownstone_core.packets.assetFilter.FilterDescriptionPackets import *
from crownstone_core.packets.assetFilter.FilterIOPackets import *
from crownstone_core.packets.assetFilter.FilterMetaDataPackets import *
from crownstone_core.util import AssetFilterUtil
from crownstone_core.util.AssetFilterUtil import get_filter_crc
from crownstone_core.util.Cuckoofilter import CuckooFilter
from crownstone_uart import CrownstoneUart

from bluenet_logs import BluenetLogs

import logging

# logging.basicConfig(format='%(asctime)s %(levelname)-7s: %(message)s', level=logging.DEBUG)


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

		stoneIds = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
		# stoneIds = [3]
		txPower = 4

		print(f"Set TX power to {txPower} at crownstones {stoneIds}")
		await uart.mesh.set_tx_power(stoneIds, txPower)
		print(f"TX power set!")

		# print("Test")
		# await uart.mesh.reset_rssi_between_stones()
		# await uart.mesh.reset_rssi_between_stones([3, 24])

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
