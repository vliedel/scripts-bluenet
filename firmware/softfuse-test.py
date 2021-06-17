#!/usr/bin/env python3
import asyncio
from os import path
import argparse

from crownstone_ble.core.container.ScanData import ScanData
from crownstone_core.Enums import CrownstoneOperationMode
from crownstone_core.packets.serviceDataParsers.containers.elements.AdvTypes import AdvType
from crownstone_ble.topics.SystemBleTopics import SystemBleTopics

from crownstone_ble import CrownstoneBle, BleEventBus, BleTopics
from crownstone_core.protocol.SwitchState import SwitchState

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
		self.default_timeout = 5

	def handle_advertisement(self, scan_data: ScanData):
		print(scan_data)
		if self.result:
			# We already have the correct result.
			return
		if scan_data.payload is None:
			return
		if scan_data.address.lower() != self.address:
			return
		if scan_data.payload.type == AdvType.EXTERNAL_STATE or scan_data.payload.type == AdvType.EXTERNAL_ERROR:
			# Only handle state of the crownstone itself.
			return
		if self.check_advertisement(scan_data):
			self.result = True
			BleEventBus.emit(SystemBleTopics.abortScanning, True)

	# Function to be implemented by derived class.
	def check_advertisement(self, scan_data: ScanData) -> bool:
		return False

	# Function to be implemented by derived class.
	def get_error_string(self) -> str:
		return "Error"

	# Function to be implemented by derived class.
	def get_run_string(self) -> str:
		return "Checking"

	async def run(self, timeout_seconds: int = None):
		print(self.get_run_string())
		subId = BleEventBus.subscribe(BleTopics.advertisement, self.handle_advertisement)
		if timeout_seconds is None:
			timeout_seconds = self.default_timeout
		await core.ble.scan(duration=timeout_seconds)
		BleEventBus.unsubscribe(subId)
		if not self.result:
			raise Exception(self.get_error_string())



class PowerUsageChecker(ServiceDataChecker):
	def __init__(self, address: str, min_power: float, max_power: float):
		super().__init__(address)
		self.default_timeout = 10
		self.min_power = min_power
		self.max_power = max_power
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE, AdvType.CROWNSTONE_ERROR]:
			return False
		self.received_value = scan_data.payload.powerUsageReal
		return (self.min_power <= self.received_value <= self.max_power)

	def get_error_string(self) -> str:
		return f"Expected power usage between {self.min_power}W and {self.max_power}W, got {self.received_value}W"

	def get_run_string(self) -> str:
		return f"Checking if power usage is between {self.min_power}W and {self.max_power}W ..."


class SwitchStateChecker(ServiceDataChecker):
	def __init__(self, address: str, dimmer_value: int, relay_on: bool):
		super().__init__(address)
		# There is no constructor yet that creates a switch state from dimmer value and relay, so we store both.
		self.expected_dimmer_value = dimmer_value
		self.expected_relay_value = relay_on
		self.received_dimmer_value = None
		self.received_relay_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE]:
			return False
		self.received_dimmer_value = scan_data.payload.switchState.dimmer
		self.received_relay_value = scan_data.payload.switchState.relay
		return (self.received_dimmer_value == self.expected_dimmer_value and self.received_relay_value == self.expected_relay_value)

	def get_error_string(self) -> str:
		return f"Expected dimmer value {self.expected_dimmer_value} and relay {self.expected_relay_value}, " \
		       f"got dimmer {self.received_dimmer_value} and relay {self.received_relay_value}"

	def get_run_string(self) -> str:
		return f"Checking if dimmer value is {self.expected_dimmer_value} and relay is {self.expected_relay_value} ..."


class ErrorStateChecker(ServiceDataChecker):
	def __init__(self, address: str, error_bitmask: int):
		super().__init__(address)
		self.expected_value = error_bitmask
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool:
		if self.expected_value == 0:
			# We want to be sure there is _no_ error. This means the error type is likely not being advertised.
			if scan_data.payload.type in [AdvType.CROWNSTONE_ERROR, AdvType.SETUP_STATE]:
				self.received_value = scan_data.payload.errorsBitmask
				return (scan_data.payload.errorsBitmask == 0)
			if scan_data.payload.type == AdvType.CROWNSTONE_STATE:
				return (scan_data.payload.hasError == False)
			return False
		if scan_data.payload.type in [AdvType.CROWNSTONE_ERROR, AdvType.SETUP_STATE]:
			self.received_value = scan_data.payload.errorsBitmask
			return (self.received_value == self.expected_value)

	def get_error_string(self) -> str:
		return f"Expected error bitmask {self.expected_value}, got {self.received_value}"

	def get_run_string(self) -> str:
		return f"Checking if error bitmask is {self.expected_value} ..."


class DimmerReadyChecker(ServiceDataChecker):
	def __init__(self, address: str, dimmer_ready: bool):
		super().__init__(address)
		self.default_timeout = 70
		self.expected_value = dimmer_ready
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE, AdvType.CROWNSTONE_ERROR]:
			return False
		self.received_value = scan_data.payload.flags.dimmerReady
		return (self.received_value == self.expected_value)

	def get_error_string(self) -> str:
		return f"Expected dimmer ready to be {self.expected_value}, got {self.received_value}"



class ChipTempChecker(ServiceDataChecker):
	def __init__(self, address: str, chip_temp_min: float, chip_temp_max: float):
		super().__init__(address)
		self.chip_temp_min = chip_temp_min
		self.chip_temp_max = chip_temp_max
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE, AdvType.CROWNSTONE_ERROR]:
			return False
		self.received_value = scan_data.payload.temperature
		return (self.chip_temp_min <= self.received_value <= self.chip_temp_max)

	def get_error_string(self) -> str:
		return f"Expected dimmer ready to be {self.expectedValue}, got {self.received_value}"




# Lower case all options
args.crownstone_address = args.crownstone_address.lower()
args.broken_crownstone_address = args.broken_crownstone_address.lower()
#args.adapter_address = args.adapter_address.lower()

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

async def factory_reset(address: str):
	"""
	Perform factory reset if the stone is in normal mode.
	"""
	op_mode = await core.getMode(address)
	if op_mode == CrownstoneOperationMode.NORMAL:
		print("Crownstone is in normal mode, attempting to factory reset ...")
		await core.connect(address)
		await core.control.commandFactoryReset()
		await core.disconnect()
		await asyncio.sleep(3.0)

async def setup(address: str):
	"""
	Perform setup if the stone is in setup mode.
	"""
	op_mode = await core.getMode(address)
	if op_mode == CrownstoneOperationMode.SETUP:
		print("Crownstone is in setup mode, performing setup ...")
		await core.setup.setup(address,
	                       sphere_id,
	                       crownstone_id,
	                       crownstone_mesh_device_key,
	                       ibeacon_uuid,
	                       crownstone_ibeacon_major,
	                       crownstone_ibeacon_minor)


async def current_fuse_no_false_positive(dim_value=100, load_min=120, load_max=150):
	await setup(args.crownstone_address)
	await DimmerReadyChecker(args.crownstone_address, True).run()
	await core.connect(args.crownstone_address)
	print("Turn relay off")
	await core.control.setRelay(False)
	await core.control.allowDimming(True)
	await core.control.setDimmer(dim_value)
	await core.disconnect()
	await SwitchStateChecker(args.crownstone_address, dim_value, False).run()
	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")
	await PowerUsageChecker(args.crownstone_address, int(load_min * 100 / dim_value), int(load_max * 100 / dim_value)).run()
	await ErrorStateChecker(args.crownstone_address, 0).run()
	user_action_request("Place a phone next to the crownstone.")
	for i in range(0, 10):
		user_action_request("Call the phone.")
		await ErrorStateChecker(args.crownstone_address, 0).run()
		await asyncio.sleep(1 * 60)


async def current_fuse_overload_dimmer(dim_value=100, load_min=300, load_max=500):
	await setup(args.crownstone_address)
	await DimmerReadyChecker(args.crownstone_address, True).run()
	await core.connect(args.crownstone_address)
	await core.control.setRelay(False)
	await core.control.allowDimming(True)
	await core.control.setDimmer(dim_value)
	await core.disconnect()
	await SwitchStateChecker(args.crownstone_address, dim_value, False).run()
	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")

	# Expected error: current overload dimmer
	error_bitmask = 1 << 1
	await ErrorStateChecker(args.crownstone_address, error_bitmask).run()

	# Relay should be turned on.
	await SwitchStateChecker(args.crownstone_address, 0, True).run()

	# Now we can check for the correct power usage.
	await PowerUsageChecker(args.crownstone_address, load_min, load_max).run()

	await core.connect(args.crownstone_address)
	await core.control.setRelay(False)

	dimming_allowed = await core.state.getDimmingAllowed()
	if dimming_allowed:
		raise Exception(f"Dimming allowed is {dimming_allowed}")

	await core.control.allowDimming(True)
	await core.control.setDimmer(dim_value)

	await core.disconnect()

	# Relay should still be turned on, and dimmer turned off.
	await SwitchStateChecker(args.crownstone_address, 0, True).run()


async def chip_temperature(setup_mode: bool):
	if setup_mode:
		await factory_reset(args.crownstone_address)
	else:
		await setup(args.crownstone_address)
	print("Waiting for chip to cool off ...")
	await ChipTempChecker(args.crownstone_address, 0, 50).run(1 * 60)
	await DimmerReadyChecker(args.crownstone_address, True).run()
	await core.connect(args.crownstone_address)
	await core.control.setRelay(True)
	await core.control.allowDimming(True)
	await core.control.setDimmer(0)
	await core.control.lockSwitch(True)
	await core.disconnect()
	await SwitchStateChecker(args.crownstone_address, 0, True).run()
	user_action_request(f"Heat up the chip, by blowing hot air on it.")

	# Expected error: chip temp overload
	error_bitmask = 1 << 2
	await ErrorStateChecker(args.crownstone_address, error_bitmask).run(5 * 60)

	# Temperature should still be close to the threshold.
	await ChipTempChecker(args.crownstone_address, 70, 76).run()

	# Relay should be turned off.
	await SwitchStateChecker(args.crownstone_address, 0, False).run()

	await core.connect(args.crownstone_address)
	await core.control.lockSwitch(False)
	await core.control.setRelay(True)
	await core.control.allowDimming(True)
	await core.control.setDimmer(0)
	await core.disconnect()

	await SwitchStateChecker(args.crownstone_address, 0, False).run()


current_threshold_dimmer_set = False
async def dimmer_temperature_init():
	await setup(args.crownstone_address)
	await DimmerReadyChecker(args.crownstone_address, True).run()

	global current_threshold_dimmer_set
	if not current_threshold_dimmer_set:
		await core.connect(args.crownstone_address)
		await core._dev.setCurrentThresholdDimmer(16)
		await core.control.allowDimming(True)
		await core.control.reset()
		await core.disconnect()

		# Wait for reboot
		await asyncio.sleep(3)

	await core.connect(args.crownstone_address)
	current_threshold = await core._dev.getCurrentThresholdDimmer()
	if (current_threshold != 16.0):
		raise Exception(f"Current threshold is {current_threshold}")
	current_threshold_dimmer_set = True
	# await core.disconnect()

async def dimmer_temperature_holds():
	await dimmer_temperature_init()

	await core.connect(args.crownstone_address)
	await core.control.setRelay(False)
	await core.control.allowDimming(True)
	await core.control.setDimmer(100)
	await core.control.lockSwitch(True)
	await core.disconnect()

	await SwitchStateChecker(args.crownstone_address, 100, False).run()

	load_min = 200
	load_max = 250
	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")
	await PowerUsageChecker(args.crownstone_address, load_min, load_max).run()

	print("Wait for 5 minutes")
	await asyncio.sleep(5 * 60)

	await ErrorStateChecker(args.crownstone_address, 0).run()

async def dimmer_temperature_overloads():
	await dimmer_temperature_init()

	await core.connect(args.crownstone_address)
	await core.control.setRelay(False)
	await core.control.allowDimming(True)
	await core.control.setDimmer(100)
	await core.control.lockSwitch(True)
	await core.disconnect()

	await SwitchStateChecker(args.crownstone_address, 100, False).run()

	load_min = 300
	load_max = 500
	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")
	await PowerUsageChecker(args.crownstone_address, load_min, load_max).run()

	print(f"Waiting for dimmer temperature to rise ...")
	# Expected error: dimmer temp overload
	error_bitmask = 1 << 3
	await ErrorStateChecker(args.crownstone_address, error_bitmask).run(5 * 60)

	await SwitchStateChecker(args.crownstone_address, 0, True).run()

	await core.connect(args.crownstone_address)
	await core.control.setRelay(False)

	dimming_allowed = await core.state.getDimmingAllowed()
	if dimming_allowed:
		raise Exception(f"Dimming allowed is {dimming_allowed}")

	await core.control.allowDimming(True)
	await core.control.setDimmer(100)

	# Relay should still be turned on, and dimmer turned off.
	switch_state = await core.state.getSwitchState()
	if switch_state.dimmer != 0 or switch_state.relay == False:
		raise Exception(f"Switch state is {switch_state}")

	await core.control.commandFactoryReset()
	await core.disconnect()


async def main():
	await factory_reset(args.crownstone_address)
	await setup(args.crownstone_address)

	await current_fuse_no_false_positive(100)
	await current_fuse_no_false_positive(50)

	await current_fuse_overload_dimmer(100, 300, 500)
	await current_fuse_overload_dimmer(100, 2000, 3000)

	await chip_temperature(False)
	await chip_temperature(True)

	await dimmer_temperature_holds()
	await dimmer_temperature_overloads()

	await core.shutDown()

try:
	# asyncio.run does not work here.
	loop = asyncio.get_event_loop()
	loop.run_until_complete(main())
except KeyboardInterrupt:
	print("Closing the test.")