import asyncio
from state_checker import *
from ble_base_test import BleBaseTest, BleBaseTestArgs
from base_test import BaseTestException

class TestChipOverheat(BleBaseTest):

	def get_description(self) -> str:
		return "Overheat the chip, which should turn off the relay."

	async def _run(self):
		await self._run_with(True)
		await self._run_with(False)

	async def _run_with(self, setup_mode: bool):
		if setup_mode:
			await self.factory_reset()
		else:
			await self.setup()
		self.logger.info("Waiting for chip to cool off ...")
		await ChipTempChecker(self.state_checker_args, 0, 50).wait_for_state_match(1 * 60)
		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()

		await self.set_switch(True, 0, True, True)
		await self.core.disconnect()

		self.user_action_request(f"Heat up the chip, by blowing hot air on it.")

		# Expected error: chip temp overload
		error_bitmask = 1 << 2
		await ErrorStateChecker(self.state_checker_args, error_bitmask).wait_for_state_match(5 * 60)

		# Temperature should still be close to the threshold.
		await ChipTempChecker(self.state_checker_args, 70, 76).check()

		# Relay should be turned off.
		await SwitchStateChecker(self.state_checker_args, 0, False).check()

		await self.set_switch_should_fail(True, 100)

		await self.reset_errors()
