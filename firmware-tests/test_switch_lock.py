import asyncio
from state_checker import *
from ble_base_test import BleBaseTest, BleBaseTestArgs
from base_test import BaseTestException

class TestSwitchLock(BleBaseTest):
	@staticmethod
	def get_name() -> str:
		return __class__.__name__

	@staticmethod
	def get_description() -> str:
		return "Test switch lock."

	async def _run_ble(self):
		await self.setup()
		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()

		self.logger.info("Testing if relay remains on when locked.")
		await self.set_switch(True, 0, False, True)
		await self.core.disconnect()  # Disconnect, so advertisement is checked.
		await SwitchLockChecker(self.state_checker_args, True).check()

		await self.set_switch_should_fail(False, 0, unlock_switch=False)

		await self.set_switch_lock(False)
		await self.core.disconnect()  # Disconnect, so advertisement is checked.
		await SwitchLockChecker(self.state_checker_args, False).check()

		self.logger.info("Testing if relay remains off when locked.")
		await self.set_switch(False, 0, False, True)
		await self.set_switch_should_fail(True, 0, unlock_switch=False)

		# # TODO: this test currently fails.
		# self.logger.info("Testing if dimming allowed overrides switch lock.")
		# await self.set_switch_lock(True)
		# await self.set_allow_dimming(True)
		# await SwitchLockChecker(self.state_checker_args, False).check()
		# await self.set_switch(False, 50)
		#
		# # TODO: this test currently fails.
		# self.logger.info("Testing if you can't lock switch when dimming is allowed.")
		# await self.set_switch(False, 50, True, False)
		# await self.set_switch_lock(True, False)
		# await SwitchLockChecker(self.state_checker_args, False).check()
		# await self.set_switch(False, 0)
