#!/usr/bin/env python3

"""An example that sets the time on a Crownstone."""

# from crownstone_uart import CrownstoneUart
#
# uart = CrownstoneUart()
#
# # Start up the USB bridge.
# uart.initialize_usb_sync(port="/dev/ttyACM0")
# print("Init UART done")
#
# try:
# 		if uart.running:
# 			uart.mesh.set_time()
# 			print("Done")
# 		else:
# 			print("UART not running")
# except Exception as err:
# 	print("Error:", err)
#
# uart.stop()




# import asyncio
# from crownstone_uart import CrownstoneUart
#
# uart = CrownstoneUart()
#
# async def configureGuidestone():
# 	await uart.initialize_usb(port="/dev/ttyACM0")
# 	print("initialization complete!")
#
# 	await uart.mesh.set_time()
# 	print("set time!")
# 	uart.stop()
#
# asyncio.run(configureGuidestone())

"""An example that sets the current time in the Crownstone mesh."""
import asyncio
import time

from crownstone_core.util.Timestamp import getCorrectedLocalTimestamp

from crownstone_uart import CrownstoneUart

import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

uart = CrownstoneUart()

# Start up the USB bridge.
async def run_example():
	# create a connection with the crownstone usb dongle.
	await uart.initialize_usb(port="/dev/ttyACM0")
	print("initialized")

	# time.sleep(1)

	# uart.mesh.turn_crownstone_on(29)
	# print("turned on")
	#
	# time.sleep(1)

	# In the Crownstone app, we usually set the local time, which is the timestamp with correction for the timezone
	# The only important thing is that you use the same timezone when you set certain time-related things as you use here.
	timestamp = time.time()

	local_timestamp = getCorrectedLocalTimestamp(timestamp)
	await uart.mesh.set_time(int(local_timestamp))
	print("set time")

	# stop the connection to the dongle
	uart.stop()
	print("stop")

asyncio.run(run_example())
