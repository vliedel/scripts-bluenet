#!/usr/bin/env python3

"""An example that switches a Crownstone, and prints the power usage of the selected Crownstone."""
import logging
import time
from crownstone_uart import CrownstoneUart, UartEventBus, UartTopics

logging.basicConfig(format='%(levelname)-7s: %(message)s', level=logging.DEBUG)
#logging.basicConfig(format='%(levelname)-7s: %(message)s', level=logging.INFO)

def showNewData(data):
	global targetCrownstoneId
	if data["id"] == targetCrownstoneId:
		print("New data received!")
		print("PowerUsage of crownstone", data["id"], data["powerUsageReal"])
		print("-------------------")


uart = CrownstoneUart()

# Start up the USB bridge.
uart.initialize_usb_sync(port='/dev/ttyUSB0')
#uart.initialize_usb_sync(port='/dev/ttyACM0')
# you can alternatively do this async by
# await uart.initialize_usb()

# Set up event listeners
UartEventBus.subscribe(UartTopics.newDataAvailable, showNewData)

# The try except part is just to catch a control+c, time.sleep does not appreciate being killed.
try:
	uart._usbDev.setUartMode(3)
	time.sleep(60)
except KeyboardInterrupt:
	print("\nClosing example.... Thanks for your time!")

uart.stop()
