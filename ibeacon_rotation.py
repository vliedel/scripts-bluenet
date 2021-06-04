#!/usr/bin/env python3
import asyncio
import logging
import os
import argparse
from crownstone_uart import CrownstoneUart
from bluenet_logs import BluenetLogs

# logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

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


uart = CrownstoneUart()

def onError():
	uart.stop()
	exit(1)

async def configureGuidestone():
	await uart.initialize_usb(port=args.device, writeChunkMaxSize=64)
	print("initialization complete!")

	# ibeacon_uuid = "aab094e7-569c-4bc6-8637-e11ce4221c18"  # keep this format
	# result = await uart.mesh.set_ibeacon_uuid(3, ibeacon_uuid, 1)
	# if result.success:
	# 	print("iBeacon UUID set!")
	# uart.stop()
	# exit(0)

	uids_to_interleave = [2, 3]

	enable_rotation = True

	if enable_rotation:
		ibeacon_uuid = "aab094e7-569c-4bc6-8637-e11ce4221c18" # keep this format
		ibeacon_major = 11000 # 0 .. 65535
		ibeacon_minor = 22000 # 0 .. 65535

		index = 1 # the index 1 is for the second payload, 0 is the one that was put there by the setup process

		for crownstone_uid in uids_to_interleave:
			result = await uart.mesh.set_ibeacon_uuid(crownstone_uid, ibeacon_uuid, index)
			if result.success:
				print("iBeacon UUID set!", crownstone_uid)
			else:
				print("Failed to set the uuid. Maybe try again?", crownstone_uid)
				onError()

			result = await uart.mesh.set_ibeacon_major(crownstone_uid, ibeacon_major + crownstone_uid, index)
			if result.success:
				print("iBeacon major set!", crownstone_uid)
			else:
				print("Failed to set the major. Maybe try again?", crownstone_uid)
				onError()

			result = await uart.mesh.set_ibeacon_minor(crownstone_uid, ibeacon_minor + crownstone_uid, index)
			if result.success:
				print("iBeacon minor set!", crownstone_uid)
			else:
				print("Failed to set the minor. Maybe try again?", crownstone_uid)
				onError()

		# Set ibeacon config 0 every 60s, starting at t=0
		# Set ibeacon config 1 every 60s, starting at t=30
		result = await uart.mesh.periodically_activate_ibeacon_index(uids_to_interleave, 0, 60, 0)
		print("PART 1: Here is a list of uid: resultCode of all uids:", result.acks)
		print("PART 1: As well as the result of the command:", result.success)
		if not result.success:
			onError()

		result = await uart.mesh.periodically_activate_ibeacon_index(uids_to_interleave, 1, 60, 30)
		print("PART 2: Here is a list of uid: resultCode of all uids:", result.acks)
		print("PART 2: As well as the result of the command:", result.success)
		if not result.success:
			onError()
	else:
		# Undo the rotation:
		# Set ibeacon config 1 once, starting now
		# Set ibeacon config 0 once, starting now
		result = await uart.mesh.periodically_activate_ibeacon_index(uids_to_interleave, 1, 0, 0)
		print("PART 1: Here is a list of uid: resultCode of all uids:", result.acks)
		print("PART 1: As well as the result of the command:", result.success)
		if not result.success:
			onError()

		result = await uart.mesh.periodically_activate_ibeacon_index(uids_to_interleave, 0, 0, 0)
		print("PART 2: Here is a list of uid: resultCode of all uids:", result.acks)
		print("PART 2: As well as the result of the command:", result.success)
		if not result.success:
			onError()

	uart.stop()

asyncio.run(configureGuidestone())
