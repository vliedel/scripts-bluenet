import asyncio
from state_checker import *
from ble_base_test import BleBaseTest, BleBaseTestArgs
from base_test import BaseTestException

class TestIgbtFailureDetection(BleBaseTest):
	use_crownstone_with_broken_igbt = True

	def __init__(self, args: BleBaseTestArgs):
		super().__init__(args)
		self.load_min = 2500
		self.load_max = 3000

	@staticmethod
	def get_name() -> str:
		return __class__.__name__

	@staticmethod
	def get_description() -> str:
		return "Check if a broken IGBT, that is always one, will be detected."

	async def _run_ble(self):
		await self._run_with(False)
		await self._run_with(True)

	async def _run_with(self, setup_mode: bool):
		self.user_action_request(f"Plug in the crownstone with 1 broken IGBT.")
		if setup_mode:
			await self.factory_reset()
		else:
			await self.setup()
		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()

		# Check if power measurement works.
		await self.set_switch(True, 0, True, False)
		await self.core.disconnect()

		self.user_action_request(f"Plug in a load of {self.load_min}W - {self.load_max}W.")
		await PowerUsageChecker(self.state_checker_args, self.load_min, self.load_max).wait_for_state_match()

		self.user_action_request(f"Plug out the load.")
		await PowerUsageChecker(self.state_checker_args, -10, 10).wait_for_state_match()

		# Turn off relay, and check if error is reported and relay is turned on.
		await self.set_switch(False, 0, True, True)
		await self.core.disconnect()

		self.user_action_request(f"Plug in a load of {self.load_min}W - {self.load_max}W.")
		await PowerUsageChecker(self.state_checker_args, self.load_min, self.load_max).wait_for_state_match()

		# Expected error: IGBT on failure
		error_bitmask = 1 << 5
		await ErrorStateChecker(self.state_checker_args, error_bitmask).wait_for_state_match()
		await SwitchStateChecker(self.state_checker_args, 0, True).check()

		# Check if relay cannot be turned off, and dimmer not turned on.
		await self.set_switch_should_fail(False, 100)

		await self.reset_errors()
