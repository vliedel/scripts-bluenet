#!/usr/bin/env python3
import asyncio
from os import path
import argparse

from crownstone_ble.core.container.ScanData import ScanData
from crownstone_core.packets.serviceDataParsers.containers.elements.AdvTypes import AdvType
from crownstone_ble.topics.SystemBleTopics import SystemBleTopics

from crownstone_ble import CrownstoneBle, BleEventBus, BleTopics


argParser = argparse.ArgumentParser(description="Interactive script for softfuse tests")
argParser.add_argument('--crownstoneAddress',
                       dest='crownstone_address',
                       metavar='MAC address',
                       type=str,
                       required=True,
                       help='The MAC address of the Crownstone to test.')
argParser.add_argument('--brokenCrownstoneAddress',
                       dest='broken_crownstone_address',
                       metavar='MAC address',
                       type=str,
                       required=True,
                       help='The MAC address of the Crownstone with broken IGBT (always on) to test.')
argParser.add_argument('--adapterAddress',
                       '-a',
                       dest='adapter_address',
                       metavar='MAC address',
                       type=int,
                       default=None,
                       help='Adapter MAC address of the bluetooth chip you want to use (linux only). You can get a list by running: hcitool dev')
args = argParser.parse_args()

class ServiceDataChecker:
	"""
	Base class for checking service data.
	Waits until the advertised data matches the expected value.
	"""
	def __init__(self, address: str):
		self.address = address.lower()
		self.result = False

	def handleAdvertisement(self, scanData: ScanData):
		print(scanData)
		if self.result:
			# We already have the correct result.
			return
		if scanData.payload is None:
			return
		if scanData.address.lower() != self.address:
			return
		if scanData.payload.type == AdvType.EXTERNAL_STATE or scanData.payload.type == AdvType.EXTERNAL_ERROR:
			# Only handle state of the crownstone itself.
			return
		if self.checkAdvertisement(scanData):
			self.result = True
			BleEventBus.emit(SystemBleTopics.abortScanning, True)

	# Function to be implemented by derived class.
	def checkAdvertisement(self, scanData: ScanData) -> bool:
		return False

	# Function to be implemented by derived class.
	def getErrorString(self) -> str:
		return "Error"

	async def run(self, timeout_seconds: int = 5):
		subId = BleEventBus.subscribe(BleTopics.advertisement, self.handleAdvertisement)
		await core.ble.scan(duration=timeout_seconds)
		BleEventBus.unsubscribe(subId)
		if not self.result:
			raise Exception(self.getErrorString())

class PowerUsageChecker(ServiceDataChecker):
	def __init__(self, address: str, minPower: int, maxPower: int):
		super().__init__(address)
		self.minPower = minPower
		self.maxPower = maxPower
		self.receivedValue = None

	def checkAdvertisement(self, scanData: ScanData) -> bool:
		self.receivedValue = scanData.payload.powerUsageReal
		return (self.minPower < self.receivedValue < self.maxPower)

	def getErrorString(self) -> str:
		return f"Expected power usage between {self.minPower} and {self.maxPower}, got {self.receivedValue}"

class SwitchStateChecker(ServiceDataChecker):
	def __init__(self, address: str, rawSwitchState: int):
		super().__init__(address)
		self.expectedValue = rawSwitchState
		self.receivedValue = None

	def checkAdvertisement(self, scanData: ScanData) -> bool:
		self.receivedValue = scanData.payload.switchState.raw
		return (self.receivedValue == self.expectedValue)

	def getErrorString(self) -> str:
		return f"Expected switch state {self.expectedValue}, got {self.receivedValue}"

class ErrorStateChecker(ServiceDataChecker):
	def __init__(self, address: str, errorBitmask: int):
		super().__init__(address)
		self.expectedValue = errorBitmask
		self.receivedValue = None

	def checkAdvertisement(self, scanData: ScanData) -> bool:
		if self.expectedValue == 0:
			# We want to be sure there is _no_ error. So we cannot accept a bitmask of 0, as the bitmask is 0 when no error state is advertised.
			if scanData.payload.type == AdvType.CROWNSTONE_ERROR:
				self.receivedValue = scanData.payload.errorsBitmask
				return (scanData.payload.errorsBitmask == 0)
			if scanData.payload.type == AdvType.CROWNSTONE_STATE:
				return (scanData.payload.hasError == False)
			return False
		self.receivedValue = scanData.payload.errorsBitmask
		return (self.receivedValue == self.expectedValue)

	def getErrorString(self) -> str:
		return f"Expected error bitmask {self.expectedValue}, got {self.receivedValue}"


# Lower case all options
args.crownstone_address = args.crownstone_address.lower()
args.broken_crownstone_address = args.broken_crownstone_address.lower()
args.adapter_address = args.adapter_address.lower()

# create the library instance
print(f'Initializing with adapter address={args.adapter_address}')
core = CrownstoneBle(bleAdapterAddress=args.adapter_address)

# Set default keys
core.setSettings("adminKeyForCrown", "memberKeyForHome", "basicKeyForOther", "MyServiceDataKey", "aLocalizationKey", "MyGoodMeshAppKey", "MyGoodMeshNetKey")

# Settings required for setup
sphere_id = 123

ibeacon_uuid = "1843423e-e175-4af0-a2e4-31e32f729a8a"

crownstone_id = 230
crownstone_mesh_device_key = "mesh_device_key1"
crownstone_ibeacon_major = 1234
crownstone_ibeacon_minor = 5678

broken_crownstone_id = crownstone_id + 1
broken_crownstone_mesh_device_key = "mesh_device_key2"
broken_crownstone_ibeacon_major = crownstone_ibeacon_major
broken_crownstone_ibeacon_minor = crownstone_ibeacon_minor + 1

def user_action_request(text: str):
	a = input(text + "\n<press enter when done>")

async def current_fuse_no_false_positive(dim_value=100, load_min=120, load_max=150):
	await core.connect(args.crownstone_address)
	await core.control.setRelay(False)
	await core.control.allowDimming(True)
	await core.control.setDimmer(dim_value)
	await core.disconnect()
	await SwitchStateChecker(args.crownstone_address, dim_value).run()
	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")
	await PowerUsageChecker(args.crownstone_address, load_min, load_max).run(10)
	await ErrorStateChecker(args.crownstone_address, 0).run()
	user_action_request("Place a phone next to the crownstone.")
	for i in range(0, 10):
		user_action_request("Call the phone.")
		await ErrorStateChecker(args.crownstone_address, 0).run()
		await asyncio.sleep(1 * 60)


async def main():
	normal_mode = await core.isCrownstoneInNormalMode(args.crownstone_address)
	if normal_mode:
		await core.connect(args.crownstone_address)
		await core.control.commandFactoryReset()
	await asyncio.sleep(1.0)
	await core.setup.setup(args.crownstone_address, sphere_id, crownstone_id, crownstone_mesh_device_key, ibeacon_uuid, crownstone_ibeacon_major, crownstone_ibeacon_minor)


	await current_fuse_no_false_positive(100)
	await current_fuse_no_false_positive(50)


	await core.shutDown()

try:
	# asyncio.run does not work here.
	loop = asyncio.get_event_loop()
	loop.run_until_complete(main())
except KeyboardInterrupt:
	print("Closing the test.")