import asyncio
from state_checker import *
from ble_base_test import BleBaseTest, BleBaseTestArgs
from base_test import BaseTestException

class HelperDimmerTemperature(BleBaseTest):
	"""
	Helper class.
	"""
	async def dimmer_temperature_init(self):
		await self.setup()

		await self.connect()
		current_threshold = await self.core._dev.getCurrentThresholdDimmer()
		if (current_threshold != 16.0):
			await self.connect()
			await self.core._dev.setCurrentThresholdDimmer(16)
			await self.core.control.allowDimming(True)
			await self.core.control.reset()
			await self.core.disconnect()

			# Wait for reboot
			await asyncio.sleep(3)

			await self.connect()
			current_threshold = await self.core._dev.getCurrentThresholdDimmer()
			if (current_threshold != 16.0):
				raise BaseTestException(f"Current threshold is {current_threshold}, should be 16.0")

		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()



class TestDimmerTemperatureHolds(HelperDimmerTemperature):
	def __init__(self, args: BleBaseTestArgs, load_min=200, load_max=250):
		super().__init__(args)
		self.load_min = load_min
		self.load_max = load_max

	@staticmethod
	def get_name() -> str:
		return __class__.__name__

	@staticmethod
	def get_description() -> str:
		return "Check if a high load on the dimmer (somewhat above the current threshold) does not lead to overheating it."

	async def _run_ble(self):
		await self.dimmer_temperature_init()

		await self.set_switch(False, 100, True)
		await self.core.disconnect()

		self.user_action_request(f"Plug in a load of {self.load_min}W - {self.load_max}W.")
		await PowerUsageChecker(self.state_checker_args, self.load_min, self.load_max).wait_for_state_match()

		self.logger.info("Wait for 5 minutes")
		await asyncio.sleep(5 * 60)

		await ErrorStateChecker(self.state_checker_args, 0).check()

		# await self.reset_config()



class TestDimmerTemperatureOverheat(HelperDimmerTemperature):
	def __init__(self, args: BleBaseTestArgs, load_min=300, load_max=500):
		super().__init__(args)
		self.load_min = load_min
		self.load_max = load_max

	@staticmethod
	def get_name() -> str:
		return __class__.__name__

	@staticmethod
	def get_description(self) -> str:
		return "Overheat the dimmer, which should turn on the relay, and disable dimming. The current-based softfuse will be disabled for this test."

	async def _run_ble(self):
		await self.dimmer_temperature_init()

		await self.set_switch(False, 100, True, True)
		await self.core.disconnect()

		self.user_action_request(f"Plug in a load of {self.load_min}W - {self.load_max}W.")
		await PowerUsageChecker(self.state_checker_args, self.load_min, self.load_max).wait_for_state_match()

		self.logger.info(f"Waiting for dimmer temperature to rise ...")
		# Expected error: dimmer temp overload
		error_bitmask = 1 << 3
		await ErrorStateChecker(self.state_checker_args, error_bitmask).wait_for_state_match(5 * 60)

		await SwitchStateChecker(self.state_checker_args, 0, True).check()

		await self.connect()

		self.logger.info("Checking if dimming is disabled.")
		dimming_allowed = await self.core.state.getDimmingAllowed()
		if dimming_allowed:
			raise BaseTestException(f"Dimming allowed is {dimming_allowed}, should be {False}")

		await self.set_switch_should_fail(False, 100)

		# await self.reset_config()
