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
                       type=str,
                       default=None,
                       help='Adapter MAC address of the bluetooth chip you want to use (linux only). You can get a list by running: hcitool dev')
args = argParser.parse_args()

class StateChecker:
	"""
	Base class for checking the state of a crownstone.
	Either checks first result, or waits until the state matches the expected value.
	When already connected, will first check the state via a command.
	Afterwards, will check via service data.
	"""
	def __init__(self, address: str):
		self.address = address.lower()
		self.result = None
		self.default_timeout = 5
		self.option_wait_for_state_match = True

	def handle_advertisement(self, scan_data: ScanData):
		#print(scan_data)
		if self.result == True:
			# We already have the correct result.
			return
		if scan_data.payload is None:
			return
		if scan_data.address.lower() != self.address:
			return
		if scan_data.payload.type == AdvType.EXTERNAL_STATE or scan_data.payload.type == AdvType.EXTERNAL_ERROR:
			# Only handle state of the crownstone itself.
			return
		result = self.check_advertisement(scan_data)
		if (result == True) or (result == False and not self.option_wait_for_state_match):
			self.result = result
			BleEventBus.emit(SystemBleTopics.abortScanning, True)

	# Function to be implemented by derived class.
	def check_advertisement(self, scan_data: ScanData) -> bool or None:
		return None

	# Function that can be implemented by derived class.
	async def check_via_command(self) -> bool or None:
		return None

	# Function to be implemented by derived class.
	def get_error_string(self) -> str:
		return "Error"

	# Function to be implemented by derived class.
	def get_run_string(self, wait_for_state_match: bool) -> str:
		if wait_for_state_match:
			return "Waiting"
		return "Checking"

	async def check(self, timeout: int = None):
		"""
		Checks if the first encountered value matches the expected value.
		:param timeout: Timeout in seconds.
		"""
		await self.run(False, timeout)

	async def wait_for_state_match(self, timeout: int = None):
		"""
		Waits for state to match the expected value.
		:param timeout: Timeout in seconds.
		"""
		await self.run(True, timeout)

	async def run(self, wait_for_state_match, timeout_seconds: int = None):
		"""
		Run the check.
		:param timeout_seconds:      Timeout in seconds.
		:param wait_for_state_match: True to wait for the state to match the expected value. False to check if the first result matches the expected value.
		"""
		print(self.get_run_string(wait_for_state_match))
		self.option_wait_for_state_match = wait_for_state_match
		subId = BleEventBus.subscribe(BleTopics.advertisement, self.handle_advertisement)
		if timeout_seconds is None:
			timeout_seconds = self.default_timeout

		# Check via command first.
		if await core.ble.is_connected(self.address):
			self.result = await self.check_via_command()
			if self.result == True:
				print("Check passed via connection.")
				return
			if self.result == False and not self.option_wait_for_state_match:
				raise Exception(self.get_error_string())

		# Check via advertisements
		await core.ble.scan(duration=timeout_seconds)
		BleEventBus.unsubscribe(subId)
		if self.result == False:
			raise Exception(self.get_error_string())
		if self.result is None:
			print(self.get_error_string())
			raise Exception("Timeout")
		print("Check passed via service data advertisement,")



class PowerUsageChecker(StateChecker):
	def __init__(self, address: str, min_power: float, max_power: float):
		super().__init__(address)
		self.default_timeout = 10
		self.min_power = min_power
		self.max_power = max_power
		self.received_value = None

	async def check_via_command(self) -> bool or None:
		self.received_value = core.state.getPowerUsage()
		return (self.min_power <= self.received_value <= self.max_power)

	def check_advertisement(self, scan_data: ScanData) -> bool or None:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE, AdvType.CROWNSTONE_ERROR]:
			return None
		self.received_value = scan_data.payload.powerUsageReal
		return (self.min_power <= self.received_value <= self.max_power)

	def get_error_string(self) -> str:
		return f"Expected power usage between {self.min_power}W and {self.max_power}W, got {self.received_value}W"

	def get_run_string(self, wait_for_state_match: bool) -> str:
		if wait_for_state_match:
			return f"Waiting for power usage to be between {self.min_power}W and {self.max_power}W ..."
		return f"Checking if power usage is between {self.min_power}W and {self.max_power}W ..."


class SwitchStateChecker(StateChecker):
	def __init__(self, address: str, dimmer_value: int, relay_on: bool):
		super().__init__(address)
		# There is no constructor yet that creates a switch state from dimmer value and relay, so we store both.
		self.expected_dimmer_value = dimmer_value
		self.expected_relay_value = relay_on
		self.received_dimmer_value = None
		self.received_relay_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool or None:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE]:
			return None
		self.received_dimmer_value = scan_data.payload.switchState.dimmer
		self.received_relay_value = scan_data.payload.switchState.relay
		return (self.received_dimmer_value == self.expected_dimmer_value and self.received_relay_value == self.expected_relay_value)

	async def check_via_command(self) -> bool or None:
		switch_state = await core.state.getSwitchState()
		self.received_dimmer_value = switch_state.dimmer
		self.received_relay_value = switch_state.relay
		return (self.received_dimmer_value == self.expected_dimmer_value and self.received_relay_value == self.expected_relay_value)

	def get_error_string(self) -> str:
		return f"Expected dimmer value {self.expected_dimmer_value} and relay {self.expected_relay_value}, " \
		       f"got dimmer {self.received_dimmer_value} and relay {self.received_relay_value}"

	def get_run_string(self, wait_for_state_match: bool) -> str:
		return f"Checking if dimmer value is {self.expected_dimmer_value} and relay is {self.expected_relay_value} ..."


class ErrorStateChecker(StateChecker):
	def __init__(self, address: str, error_bitmask: int):
		super().__init__(address)
		self.expected_value = error_bitmask
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool or None:
		if self.expected_value == 0:
			# We want to be sure there is _no_ error. This means the error type is likely not being advertised.
			if scan_data.payload.type in [AdvType.CROWNSTONE_ERROR, AdvType.SETUP_STATE]:
				self.received_value = scan_data.payload.errorsBitmask
				return (scan_data.payload.errorsBitmask == 0)
			if scan_data.payload.type == AdvType.CROWNSTONE_STATE:
				return (scan_data.payload.flags.hasError == False)
			return None
		if scan_data.payload.type in [AdvType.CROWNSTONE_ERROR, AdvType.SETUP_STATE]:
			self.received_value = scan_data.payload.errorsBitmask
			return (self.received_value == self.expected_value)
		return None

	async def check_via_command(self) -> bool or None:
		self.received_value = core.state.getErrors().bitMask
		return (self.received_value == self.expected_value)

	def get_error_string(self) -> str:
		return f"Expected error bitmask {self.expected_value}, got {self.received_value}"

	def get_run_string(self, wait_for_state_match: bool) -> str:
		if wait_for_state_match:
			return f"Waiting for error bitmask to be {self.expected_value} ..."
		return f"Checking if error bitmask is {self.expected_value} ..."


class DimmerReadyChecker(StateChecker):
	def __init__(self, address: str, dimmer_ready: bool):
		super().__init__(address)
		self.default_timeout = 70
		self.expected_value = dimmer_ready
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool or None:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE, AdvType.CROWNSTONE_ERROR]:
			return None
		self.received_value = scan_data.payload.flags.dimmerReady
		return (self.received_value == self.expected_value)

	async def check_via_command(self) -> bool or None:
		# There is no command for this.
		return None

	def get_error_string(self) -> str:
		return f"Expected dimmer ready to be {self.expected_value}, got {self.received_value}"

	def get_run_string(self, wait_for_state_match: bool) -> str:
		if wait_for_state_match:
			return f"Waiting for dimmer ready to be {self.expected_value} ..."
		return f"Checking if dimmer ready is {self.expected_value} ..."



class ChipTempChecker(StateChecker):
	def __init__(self, address: str, chip_temp_min: float, chip_temp_max: float):
		super().__init__(address)
		self.chip_temp_min = chip_temp_min
		self.chip_temp_max = chip_temp_max
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool or None:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE, AdvType.CROWNSTONE_ERROR]:
			return None
		self.received_value = scan_data.payload.temperature
		return (self.chip_temp_min <= self.received_value <= self.chip_temp_max)

	async def check_via_command(self) -> bool or None:
		self.received_value = core.state.getChipTemperature()
		return (self.chip_temp_min <= self.received_value <= self.chip_temp_max)

	def get_error_string(self) -> str:
		return f"Expected chip temperature to be between {self.chip_temp_min} and {self.chip_temp_max}, got {self.received_value}"

	def get_run_string(self, wait_for_state_match: bool) -> str:
		if wait_for_state_match:
			return f"Waiting for chip temperature to be between {self.chip_temp_min} and {self.chip_temp_max} ..."
		return f"Checking if chip temperature is between {self.chip_temp_min} and {self.chip_temp_max} ..."




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

def print_title(text: str):
	print("=" * len(text))
	print(text)
	print("=" * len(text))

def user_action_request(text: str):
	a = input(text + "\n<press enter when done>")

def user_question(text: str) -> str:
	a = input(text)
	return a

class user_question_option:
	def __init__(self, return_value, matches: [str] = None, description: str = None):
		"""
		:param return_value: The value to return when this option is selected.
		:param matches: A list op strings that, when given as input, will select this option.
		:param description: The description of this option.
		"""
		self.matches = matches
		self.return_value = return_value
		self.description = description

def user_question_options(question: str, options: [user_question_option] = None, default_return_value = None):
	"""
	Ask the user to pick an option.
	:param question: The question to ask.
	:param options: A list of user question option.
	:param default_return_value: The return value if none of the options was selected.
	:return: The return value of the selected option, or the default otherwise.
	"""
	if options is None:
		options = [
			user_question_option(True, ["yes", "y"]),
			user_question_option(False, ["no", "n"])
		]
	explanation = False
	i = 1
	for option in options:
		if option.description is not None:
			explanation = True
		if option.matches is None:
			option.matches = [str(i)]
		i += 1

	text = f"{question}\n  Please select:"
	if explanation:
		text += "\n"
		for option in options:
			text += f"    {option.matches[0]} {option.description}\n"
	else:
		for option in options:
			text += f" {option.matches[0]} /"
		text = text[0:-2] + "\n"

	answer = input(text)
	for option in options:
		if answer in option.matches:
			return option.return_value
	return default_return_value




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

async def setup(broken_crownstone = False):
	"""
	Perform setup if the stone is in setup mode.
	"""
	address = args.crownstone_address if not broken_crownstone else args.broken_crownstone_address
	op_mode = await core.getMode(address)
	if op_mode == CrownstoneOperationMode.SETUP:
		print("Crownstone is in setup mode, performing setup ...")
		await core.setup.setup(address,
	                       sphere_id,
	                       crownstone_id if not broken_crownstone else broken_crownstone_id,
	                       crownstone_mesh_device_key if not broken_crownstone else broken_crownstone_mesh_device_key,
	                       ibeacon_uuid,
	                       crownstone_ibeacon_major if not broken_crownstone else broken_crownstone_ibeacon_major,
	                       crownstone_ibeacon_minor if not broken_crownstone else broken_crownstone_ibeacon_minor)

async def reset_errors(address: str):
	"""
	Reset errors and check if the errors are reset indeed.
	"""
	await core.connect(address)
	await core.control.resetErrors()
	await ErrorStateChecker(address, 0).check()
	await core.disconnect()



async def test_dimmer_current_holds(dim_value=100, load_min=120, load_max=160):
	"""
	Check if a high load on the dimmer, but within allowed specs, does not lead to an error.
	:param dim_value: The dim value to use (0-100).
	:param load_min:  The minimum load in Watt.
	:param load_max:  The maximum load in Watt.
	"""
	print_title("Test if dimmer gives no error for high load.")
	await setup()
	await DimmerReadyChecker(args.crownstone_address, True).wait_for_state_match()
	await core.connect(args.crownstone_address)
	print(f"Turn relay off, set dimmer at {dim_value}%")
	await core.control.setRelay(False)
	await core.control.allowDimming(True)
	await core.control.setDimmer(dim_value)
	await SwitchStateChecker(args.crownstone_address, dim_value, False).check()
	await core.disconnect()
	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")
	await PowerUsageChecker(args.crownstone_address, int(load_min * dim_value / 100), int(load_max * dim_value / 100)).wait_for_state_match()
	await ErrorStateChecker(args.crownstone_address, 0).check()
	user_action_request("Place a phone next to the crownstone.")
	for i in range(0, 10):
		user_action_request("Call the phone.")
		await ErrorStateChecker(args.crownstone_address, 0).check()
		print("Waiting 1 minute ...")
		await asyncio.sleep(1 * 60)




async def test_dimmer_current_overload(dim_value=100, load_min=300, load_max=500):
	"""
	Overload the dimmer (too much current), which should turn on the relay, and disable dimming.
	:param dim_value: The dim value to use (0-100).
	:param load_min:  The minimum load in Watt.
	:param load_max:  The maximum load in Watt.
	"""
	print_title("Test overloading the dimmer.")
	await setup()
	await DimmerReadyChecker(args.crownstone_address, True).wait_for_state_match()
	await core.connect(args.crownstone_address)
	await core.control.setRelay(False)
	await core.control.allowDimming(True)
	await core.control.setDimmer(dim_value)
	await core.control.lockSwitch(True)
	await SwitchStateChecker(args.crownstone_address, dim_value, False).check()
	await core.disconnect()
	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")

	# Expected error: current overload dimmer
	error_bitmask = 1 << 1
	await ErrorStateChecker(args.crownstone_address, error_bitmask).wait_for_state_match()

	# Relay should be turned on.
	await SwitchStateChecker(args.crownstone_address, 0, True).check()

	# Now we can check for the correct power usage.
	await PowerUsageChecker(args.crownstone_address, load_min, load_max).check()

	await core.connect(args.crownstone_address)
	await core.control.lockSwitch(False)
	await core.control.setRelay(False)

	dimming_allowed = await core.state.getDimmingAllowed()
	if dimming_allowed:
		raise Exception(f"Dimming allowed is {dimming_allowed}")

	await core.control.allowDimming(True)
	await core.control.setDimmer(dim_value)

	# Relay should still be turned on, and dimmer turned off.
	await SwitchStateChecker(args.crownstone_address, 0, True).check()

	await reset_errors(args.crownstone_address)
	await core.disconnect()


async def test_chip_temperature_overheat(setup_mode: bool):
	"""
	Overheat the chip, which should turn off the relay.
	:param setup_mode: Whether to perform the test in setup mode.
	"""
	print_title("Test overheating the chip.")
	if setup_mode:
		await factory_reset(args.crownstone_address)
	else:
		await setup()
	print("Waiting for chip to cool off ...")
	await ChipTempChecker(args.crownstone_address, 0, 50).wait_for_state_match(1 * 60)
	await DimmerReadyChecker(args.crownstone_address, True).wait_for_state_match()
	await core.connect(args.crownstone_address)
	await core.control.setRelay(True)
	await core.control.allowDimming(True)
	await core.control.setDimmer(0)
	await core.control.lockSwitch(True)
	await SwitchStateChecker(args.crownstone_address, 0, True).check()
	await core.disconnect()

	user_action_request(f"Heat up the chip, by blowing hot air on it.")

	# Expected error: chip temp overload
	error_bitmask = 1 << 2
	await ErrorStateChecker(args.crownstone_address, error_bitmask).wait_for_state_match(5 * 60)

	# Temperature should still be close to the threshold.
	await ChipTempChecker(args.crownstone_address, 70, 76).check()

	# Relay should be turned off.
	await SwitchStateChecker(args.crownstone_address, 0, False).check()

	await core.connect(args.crownstone_address)
	await core.control.lockSwitch(False)
	await core.control.setRelay(True)
	await core.control.allowDimming(True)
	await core.control.setDimmer(0)
	await SwitchStateChecker(args.crownstone_address, 0, False).check()
	await reset_errors(args.crownstone_address)
	await core.disconnect()


async def dimmer_temperature_init():
	await setup()
	await DimmerReadyChecker(args.crownstone_address, True).wait_for_state_match()

	await core.connect(args.crownstone_address)
	current_threshold = await core._dev.getCurrentThresholdDimmer()
	if (current_threshold != 16.0):
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

		await DimmerReadyChecker(args.crownstone_address, True).wait_for_state_match()
	# await core.disconnect()

async def test_dimmer_temperature_holds(load_min=200, load_max=250):
	"""
	Check if a high load on the dimmer (somewhat above the current threshold) does not lead to overheating it.
	The current softfuse will be disabled for this test.
	:param load_min:  The minimum load in Watt.
	:param load_max:  The maximum load in Watt.
	"""
	print_title("Test if a high load on the dimmer does not lead to overheating it.")
	await dimmer_temperature_init()

	await core.connect(args.crownstone_address)
	await core.control.setRelay(False)
	await core.control.allowDimming(True)
	await core.control.setDimmer(100)
	await SwitchStateChecker(args.crownstone_address, 100, False).check()
	await core.disconnect()

	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")
	await PowerUsageChecker(args.crownstone_address, load_min, load_max).wait_for_state_match()

	print("Wait for 5 minutes")
	await asyncio.sleep(5 * 60)

	await ErrorStateChecker(args.crownstone_address, 0).check()

async def test_dimmer_temperature_overheat(load_min=300, load_max=500):
	"""
	Overheat the dimmer, which should turn on the relay, and disable dimming.
	The current softfuse will be disabled for this test.
	:param load_min:  The minimum load in Watt to be used for this test.
	:param load_max:  The maximum load in Watt.
	"""
	print_title("Test overheating the dimmer.")
	await dimmer_temperature_init()

	await core.connect(args.crownstone_address)
	await core.control.setRelay(False)
	await core.control.allowDimming(True)
	await core.control.setDimmer(100)
	await core.control.lockSwitch(True)
	await SwitchStateChecker(args.crownstone_address, 100, False).check()
	await core.disconnect()

	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")
	await PowerUsageChecker(args.crownstone_address, load_min, load_max).wait_for_state_match()

	print(f"Waiting for dimmer temperature to rise ...")
	# Expected error: dimmer temp overload
	error_bitmask = 1 << 3
	await ErrorStateChecker(args.crownstone_address, error_bitmask).wait_for_state_match(5 * 60)

	await SwitchStateChecker(args.crownstone_address, 0, True).check()

	await core.connect(args.crownstone_address)
	await core.control.lockSwitch(False)
	await core.control.setRelay(False)

	dimming_allowed = await core.state.getDimmingAllowed()
	if dimming_allowed:
		raise Exception(f"Dimming allowed is {dimming_allowed}")

	await core.control.allowDimming(True)
	await core.control.setDimmer(100)

	# Relay should still be turned on, and dimmer turned off.
	await SwitchStateChecker(args.crownstone_address, 0, True).check()

	await core.control.commandFactoryReset()
	await core.disconnect()


async def test_igbt_failure_holds(load_min=2500, load_max=3000):
	"""
	Check if power usage averaging does not lead to a false positive in IGBT on failure detection.
	:param load_min:  The minimum load in Watt to be used for this test.
	:param load_max:  The maximum load in Watt to be used for this test.
	"""
	print_title("Test if reboot or switching does not give a detected IGBT failure error.")
	await setup()

	# Make sure the load is plugged in.
	await core.connect(args.crownstone_address)
	await core.control.setDimmer(0)
	await core.control.setRelay(True)
	await core.disconnect()
	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")
	await PowerUsageChecker(args.crownstone_address, load_min, load_max).wait_for_state_match()

	# Check if the softfuse doesn't trigger right after turning off the switch.
	for i in range(0, 5):
		print(f"Check {i}")
		await core.connect(args.crownstone_address)
		await core.control.setRelay(True)
		print(f"Waiting ...")
		await asyncio.sleep(10)
		await core.control.setRelay(False)
		await ErrorStateChecker(args.crownstone_address, 0).check()
		await core.disconnect()

	# Make sure switch is off at boot.
	await core.connect(args.crownstone_address)
	await core.control.setRelay(False)
	await SwitchStateChecker(args.crownstone_address, 0, False).check()
	await core.disconnect()
	print(f"Waiting for switch state to be stored ...")
	await asyncio.sleep(10)

	# Check if the softfuse doesn't trigger at boot.
	for i in range(0, 5):
		user_action_request(f"Plug out (or power off) the crownstone. Keep the load plugged into the crownstone.")
		await asyncio.sleep(3)
		user_action_request(f"Plug in (or power on) the crownstone.")
		await ErrorStateChecker(args.crownstone_address, 0).check()


async def test_igbt_failure(setup_mode: bool, load_min=400, load_max=500):
	"""
	Check if a broken IGBT, that is always one, will be detected.
	:param setup_mode: Whether to perform the test in setup mode.
	:param load_min:   The minimum load in Watt to be used for this test.
	:param load_max:   The maximum load in Watt to be used for this test.
	"""
	print_title("Test IGBT failure detection.")
	user_action_request(f"Plug in the crownstone with 1 broken IGBT.")
	if setup_mode:
		await factory_reset(args.broken_crownstone_address)
	else:
		await setup(True)
	await DimmerReadyChecker(args.crownstone_address, True).wait_for_state_match()

	# Check if power measurement works.
	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")
	await core.connect(args.broken_crownstone_address)
	await core.control.setDimmer(0)
	await core.control.setRelay(True)
	await SwitchStateChecker(args.broken_crownstone_address, 0, True).check()
	await core.disconnect()
	await PowerUsageChecker(args.broken_crownstone_address, load_min, load_max).wait_for_state_match()

	# Turn off relay, and check if error is reported and relay is turned on.
	await core.connect(args.broken_crownstone_address)
	await core.control.lockSwitch(True)
	await core.control.setDimmer(0)
	await core.control.setRelay(False)
	await core.control.allowDimming(True)
	await core.disconnect()

	# Expected error: IGBT on failure
	error_bitmask = 1 << 5
	await ErrorStateChecker(args.broken_crownstone_address, error_bitmask).wait_for_state_match()
	await SwitchStateChecker(args.broken_crownstone_address, 0, True).check()

	# Check if relay cannot be turned off, and dimmer not turned on.
	await core.connect(args.broken_crownstone_address)
	await core.control.lockSwitch(False)
	await core.control.setDimmer(100)
	await core.control.setRelay(False)
	await SwitchStateChecker(args.broken_crownstone_address, 0, True).check()

	await reset_errors(args.broken_crownstone_address)
	await core.disconnect()


async def test_chip_overheat_and_igbt_failure(load_min=400, load_max=500):
	"""
	Tests if the dimmer soft fuse overrides the chip temp soft fuse.
	A soft fuse turning the relay on overrides turning it off.
	:param load_min:   The minimum load in Watt to be used for this test.
	:param load_max:   The maximum load in Watt to be used for this test.
	"""
	print_title("Test chip overheating and IGBT failure at the same time.")
	user_action_request(f"Plug in the crownstone with 1 broken IGBT.")
	await setup(True)
	await DimmerReadyChecker(args.crownstone_address, True).wait_for_state_match()

	# Check if power measurement works.
	user_action_request(f"Plug in a load of {load_min}W - {load_max}W.")
	await core.connect(args.broken_crownstone_address)
	await core.control.allowDimming(True)
	await core.control.setDimmer(0)
	await core.control.setRelay(True)
	await core.control.lockSwitch(False)
	await SwitchStateChecker(args.broken_crownstone_address, 0, True).check()
	await core.disconnect()
	await PowerUsageChecker(args.broken_crownstone_address, load_min, load_max).wait_for_state_match()

	print("Waiting for chip to cool off ...")
	await ChipTempChecker(args.broken_crownstone_address, 0, 50).wait_for_state_match(1 * 60)
	user_action_request(f"Heat up the chip, by blowing hot air on it.")

	print("Waiting for chip to heat up ...")
	# Expected error: chip temp overload AND igbt failure
	error_bitmask = 1 << 2
	error_bitmask += 1 << 5
	await ErrorStateChecker(args.broken_crownstone_address, error_bitmask).wait_for_state_match(5 * 60)

	# Relay should be turned on.
	await SwitchStateChecker(args.broken_crownstone_address, 0, True).check()

	# TODO: maybe we can use the switch history for this?
	answer = user_question_options("Did you hear or see the relay turn off and on again?")
	if not answer:
		raise Exception("Relay did not turn off and on again.")

	# Check if relay cannot be turned off, and dimmer not turned on.
	await core.connect(args.broken_crownstone_address)
	await core.control.lockSwitch(False)
	await core.control.setDimmer(100)
	await core.control.setRelay(False)
	await SwitchStateChecker(args.broken_crownstone_address, 0, True).check()

	await reset_errors(args.broken_crownstone_address)
	await core.disconnect()


async def test_switch_lock():
	print_title("Test switch lock.")
	await setup()

	await core.connect(args.crownstone_address)
	await core.control.allowDimming(False)
	await core.control.setDimmer(0)
	await core.control.setRelay(True)
	await core.control.lockSwitch(True)

	await SwitchStateChecker(args.crownstone_address, 0, True).check()
	await core.disconnect()


async def main():
	await factory_reset(args.crownstone_address)
	await setup()

	await test_dimmer_current_holds(100)
	await test_dimmer_current_holds(50)

	await test_dimmer_current_overload(100, 300, 500)
	await test_dimmer_current_overload(100, 2000, 3000)

	await test_chip_temperature_overheat(False)
	await test_chip_temperature_overheat(True)

	await test_dimmer_temperature_holds()
	await test_dimmer_temperature_overheat()

	await test_igbt_failure_holds()
	await test_igbt_failure(False)
	await test_igbt_failure(True)


	await core.shutDown()

try:
	# asyncio.run does not work here.
	loop = asyncio.get_event_loop()
	loop.run_until_complete(main())
except KeyboardInterrupt:
	print("Closing the test.")
