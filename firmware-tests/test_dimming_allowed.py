import asyncio
from state_checker import *
from ble_base_test import BleBaseTest, BleBaseTestArgs
from base_test import BaseTestException

class TestDimmingAllowed(BleBaseTest):
	@staticmethod
	def get_name() -> str:
		return __class__.__name__

	@staticmethod
	def get_description() -> str:
		return "Test dimming allowed."

	async def _run_ble(self):
		await self.setup()
		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()

		self.logger.info("Checking if setting dim value while dimming is not allowed, leads to relay being turned on.")
		await self.set_switch(True, 0, False, False)
		await self.connect()
		await self.core.control.setSwitch(50)
		await SwitchStateChecker(self.state_checker_args, 0, True).check()
		await self.core.control.setDimmer(100)
		await SwitchStateChecker(self.state_checker_args, 0, True).check()

		# ==================================================================
		self.logger.info("Checking if setting dimming allowed to False, turns relay on.")
		await self.set_switch(False, 100, True, True)

		self.logger.info("Checking if service data says dimming allowed is True.")
		await self.core.disconnect()
		await DimmingAllowedChecker(self.state_checker_args, True).check()

		await self.set_allow_dimming(False)
		# TODO: this test currently fails.
		await SwitchStateChecker(self.state_checker_args, 0, True).check()

		self.logger.info("Checking if service data says dimming allowed is False.")
		await self.core.disconnect()
		await DimmingAllowedChecker(self.state_checker_args, False).check()

		# ===================================================================
		self.logger.info("Checking if setting dimming allowed to False, turns relay on at boot.")
		await self.set_switch(False, 100, True, True)
		await self.set_allow_dimming(False)
		await self.core.control.reset()
		await self.core.disconnect()

		self.logger.info("Waiting for reboot...")
		await asyncio.sleep(2)
		await SwitchStateChecker(self.state_checker_args, 0, True).check()
