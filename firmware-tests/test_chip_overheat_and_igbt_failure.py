import asyncio
from state_checker import *
from ble_base_test import BleBaseTest, BleBaseTestArgs
from base_test import BaseTestException

class TestChipOverheatAndIgbtFailure(BleBaseTest):
	def __init__(self, args: BleBaseTestArgs):
		super().__init__(args)
		self.load_min = 400
		self.load_max = 500

	def get_description(self) -> str:
		return "Tests if the dimmer soft fuse overrides the chip temp soft fuse. A soft fuse turning the relay on overrides turning it off."

	async def _run_ble(self):
		self.user_action_request(f"Plug in the crownstone with 1 broken IGBT.")
		await self.setup()
		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()

		await self.set_switch(True, 0, True, True)
		await self.core.disconnect()

		# Check if power measurement works.
		self.user_action_request(f"Plug in a load of {self.load_min}W - {self.load_max}W.")
		await PowerUsageChecker(self.state_checker_args, self.load_min, self.load_max).wait_for_state_match()

		self.logger.info("Waiting for chip to cool off ...")
		await ChipTempChecker(self.state_checker_args, 0, 50).wait_for_state_match(1 * 60)
		self.user_action_request(f"Heat up the chip, by blowing hot air on it.")

		self.logger.info("Waiting for chip to heat up ...")
		# Expected error: chip temp overload AND igbt failure
		error_bitmask = 1 << 2
		error_bitmask += 1 << 5
		await ErrorStateChecker(self.state_checker_args, error_bitmask).wait_for_state_match(5 * 60)

		# Relay should be turned on.
		await SwitchStateChecker(self.state_checker_args, 0, True).check()

		# TODO: maybe we can use the switch history for this?
		answer = self.user_question_options("Did you hear or see the relay turn off and on again?")
		if not answer:
			raise BaseTestException("Relay did not turn off and on again.")

		# Check if relay cannot be turned off, and dimmer not turned on.
		await self.set_switch_should_fail(False, 100)

		await self.reset_errors()
