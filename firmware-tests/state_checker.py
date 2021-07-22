import asyncio
import logging
from crownstone_ble import CrownstoneBle, BleEventBus, BleTopics
from crownstone_ble.core.container.ScanData import ScanData
from crownstone_ble.topics.SystemBleTopics import SystemBleTopics
from crownstone_core.packets.serviceDataParsers.containers.elements.AdvTypes import AdvType


class StateCheckerException(Exception):
	pass

class StateCheckerArgs:
	def __init__(self, core: CrownstoneBle, address: str, logger: logging.Logger, debug = False):
		self.core = core
		self.logger = logger
		self.address = address.lower()
		self.debug = debug

class StateChecker:
	"""
	Base class for checking the state of a crownstone.
	Either checks first result, or waits until the state matches the expected value.
	When already connected, will first check the state via a command.
	Afterwards, will check via service data.
	"""
	def __init__(self, args: StateCheckerArgs):
		self.debug = args.debug
		self.core = args.core
		self.address = args.address
		self.logger = args.logger
		self.result = None
		self.default_timeout = 5
		self.option_wait_for_state_match = True

	def handle_advertisement(self, scan_data: ScanData):
		if self.debug:
			self.logger.debug(scan_data)
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
		self.logger.info(self.get_run_string(wait_for_state_match))
		self.option_wait_for_state_match = wait_for_state_match

		# Check via command first.
		if await self.core.ble.is_connected(self.address):
			self.result = await self.check_via_command()
			if self.result == True:
				self.logger.info("Check passed via connection.")
				return
			if self.result == False and not self.option_wait_for_state_match:
				raise StateCheckerException(self.get_error_string())

		# First wait 1s, because service data is only updated every second.
		await asyncio.sleep(1)

		if timeout_seconds is None:
			timeout_seconds = self.default_timeout

		# Check via advertisements
		subId = BleEventBus.subscribe(BleTopics.advertisement, self.handle_advertisement)
		await self.core.ble.scan(duration=timeout_seconds)
		BleEventBus.unsubscribe(subId)
		if self.result == False:
			raise StateCheckerException(self.get_error_string())
		if self.result is None:
			self.logger.error(self.get_error_string())
			raise StateCheckerException("Timeout")
		self.logger.info("Check passed via service data advertisement.")



class PowerUsageChecker(StateChecker):
	def __init__(self, args: StateCheckerArgs, min_power: float, max_power: float):
		super().__init__(args)
		self.default_timeout = 10
		self.min_power = min_power
		self.max_power = max_power
		self.received_value = None

	async def check_via_command(self) -> bool or None:
		self.received_value = await self.core.state.getPowerUsage()
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
	def __init__(self, args: StateCheckerArgs, dimmer_value: int, relay_on: bool):
		super().__init__(args)
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
		switch_state = await self.core.state.getSwitchState()
		self.received_dimmer_value = switch_state.dimmer
		self.received_relay_value = switch_state.relay
		return (self.received_dimmer_value == self.expected_dimmer_value and self.received_relay_value == self.expected_relay_value)

	def get_error_string(self) -> str:
		return f"Expected dimmer value {self.expected_dimmer_value}% and relay {self.expected_relay_value}, " \
		       f"got dimmer {self.received_dimmer_value}% and relay {self.received_relay_value}"

	def get_run_string(self, wait_for_state_match: bool) -> str:
		return f"Checking if dimmer value is {self.expected_dimmer_value}% and relay is {self.expected_relay_value} ..."



class ErrorStateChecker(StateChecker):
	def __init__(self, args: StateCheckerArgs, error_bitmask: int):
		super().__init__(args)
		self.expected_value = error_bitmask
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool or None:
		if self.expected_value == 0:
			# We want to be sure there is _no_ error. This means the error type is likely not being advertised.
			if scan_data.payload.type in [AdvType.CROWNSTONE_ERROR, AdvType.SETUP_STATE]:
				self.received_value = scan_data.payload.errorsBitmask.bitMask
				return (scan_data.payload.errorsBitmask.bitMask == 0)
			if scan_data.payload.type == AdvType.CROWNSTONE_STATE:
				return (scan_data.payload.flags.hasError == False)
			return None
		if scan_data.payload.type in [AdvType.CROWNSTONE_ERROR, AdvType.SETUP_STATE]:
			self.received_value = scan_data.payload.errorsBitmask.bitMask
			return (self.received_value == self.expected_value)
		return None

	async def check_via_command(self) -> bool or None:
		self.received_value = await self.core.state.getErrors().bitMask
		return (self.received_value == self.expected_value)

	def get_error_string(self) -> str:
		return f"Expected error bitmask {self.expected_value}, got {self.received_value}"

	def get_run_string(self, wait_for_state_match: bool) -> str:
		if wait_for_state_match:
			return f"Waiting for error bitmask to be {self.expected_value} ..."
		return f"Checking if error bitmask is {self.expected_value} ..."



class DimmerReadyChecker(StateChecker):
	def __init__(self, args: StateCheckerArgs, dimmer_ready: bool):
		super().__init__(args)
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



class SwitchLockChecker(StateChecker):
	def __init__(self, args: StateCheckerArgs, switch_locked: bool):
		super().__init__(args)
		self.expected_value = switch_locked
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool or None:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE, AdvType.CROWNSTONE_ERROR]:
			return None
		self.received_value = scan_data.payload.flags.switchLocked
		return (self.received_value == self.expected_value)

	async def check_via_command(self) -> bool or None:
		self.received_value = await self.core.state.getSwitchLocked()
		return (self.received_value == self.expected_value)

	def get_error_string(self) -> str:
		return f"Expected switch lock to be {self.expected_value}, got {self.received_value}"

	def get_run_string(self, wait_for_state_match: bool) -> str:
		if wait_for_state_match:
			return f"Waiting for switch lock to be {self.expected_value} ..."
		return f"Checking if switch lock is {self.expected_value} ..."



class DimmingAllowedChecker(StateChecker):
	def __init__(self, args: StateCheckerArgs, dimming_allowed: bool):
		super().__init__(args)
		self.expected_value = dimming_allowed
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool or None:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE, AdvType.CROWNSTONE_ERROR]:
			return None
		self.received_value = scan_data.payload.flags.dimmingAllowed
		return (self.received_value == self.expected_value)

	async def check_via_command(self) -> bool or None:
		self.received_value = await self.core.state.getDimmingAllowed()
		return (self.received_value == self.expected_value)

	def get_error_string(self) -> str:
		return f"Expected dimming allowed to be {self.expected_value}, got {self.received_value}"

	def get_run_string(self, wait_for_state_match: bool) -> str:
		if wait_for_state_match:
			return f"Waiting for dimming allowed to be {self.expected_value} ..."
		return f"Checking if dimming allowed is {self.expected_value} ..."



class ChipTempChecker(StateChecker):
	def __init__(self, args: StateCheckerArgs, chip_temp_min: float, chip_temp_max: float):
		super().__init__(args)
		self.chip_temp_min = chip_temp_min
		self.chip_temp_max = chip_temp_max
		self.received_value = None

	def check_advertisement(self, scan_data: ScanData) -> bool or None:
		if scan_data.payload.type not in [AdvType.CROWNSTONE_STATE, AdvType.SETUP_STATE, AdvType.CROWNSTONE_ERROR]:
			return None
		self.received_value = scan_data.payload.temperature
		return (self.chip_temp_min <= self.received_value <= self.chip_temp_max)

	async def check_via_command(self) -> bool or None:
		self.received_value = await self.core.state.getChipTemperature()
		return (self.chip_temp_min <= self.received_value <= self.chip_temp_max)

	def get_error_string(self) -> str:
		return f"Expected chip temperature to be between {self.chip_temp_min} and {self.chip_temp_max}, got {self.received_value}"

	def get_run_string(self, wait_for_state_match: bool) -> str:
		if wait_for_state_match:
			return f"Waiting for chip temperature to be between {self.chip_temp_min} and {self.chip_temp_max} ..."
		return f"Checking if chip temperature is between {self.chip_temp_min} and {self.chip_temp_max} ..."
