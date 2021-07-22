import asyncio
from state_checker import *
from ble_base_test import BleBaseTest, BleBaseTestArgs
from base_test import BaseTestException

class TestDimmerBoot(BleBaseTest):

	def get_description(self) -> str:
		return "Test dimmer boot."

	async def _run_ble(self):
		await self.setup()

		# ====================================================================
		await self.dimmer_boot_dimmed()

		self.logger.info("Checking if setting a dimmed value has no effect.")
		await self.connect()
		await self.core.control.setDimmer(10)
		await SwitchStateChecker(self.state_checker_args, 0, True).check()
		await DimmerReadyChecker(self.state_checker_args, False).check()
		await self.core.disconnect()
		await DimmerReadyChecker(self.state_checker_args, False).check()  # Also check service data.

		self.logger.info("Checking if changing the dim value has no effect either.")
		await self.connect()
		await self.core.control.setDimmer(15)
		await SwitchStateChecker(self.state_checker_args, 0, True).check()

		# TODO: this test currently fails.
		self.logger.info("Checking if dimmed value will be set once the dimmer is ready.")
		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()
		await SwitchStateChecker(self.state_checker_args, 15, False).check()

		# ====================================================================
		await self.dimmer_boot_dimmed()
		self.logger.info("Checking if stored dimmed value is not set once the dimmer is ready after boot.")
		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()
		await SwitchStateChecker(self.state_checker_args, 0, True).check()

		# ====================================================================
		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()
		self.logger.info("Checking if you can use dimmer immediately after boot.")
		await self.set_switch(False, 100, True, False)

		load_min = 10
		load_max = 30
		self.user_action_request(f"Plug in a dimmable load of {load_min}W - {load_max}W.")
		await PowerUsageChecker(self.state_checker_args, load_min, load_max).check()

		self.logger.info("Waiting for switch state to be stored.")
		await asyncio.sleep(10)

		self.user_action_request(f"Plug out the crownstone.")
		await asyncio.sleep(1)
		self.user_action_request(f"Plug in the crownstone.")

		self.logger.info("Checking if dimmer stays turned on.")
		for i in range(0, 20):
			await SwitchStateChecker(self.state_checker_args, 100, False).check()
			await asyncio.sleep(3)

	async def dimmer_boot_dimmed(self):
		self.logger.info("Checking if you can't use dimmer immediately after boot.")
		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()
		await self.set_switch(False, 100, True, False)

		load_min = 0
		load_max = 20
		self.user_action_request(f"Plug in a dimmable load of {load_min}W - {load_max}W.")
		await PowerUsageChecker(self.state_checker_args, load_min, load_max).check()

		await self.set_switch(False, 10)
		self.logger.info("Waiting for switch state to be stored.")
		await asyncio.sleep(10)

		self.user_action_request(f"Plug out the crownstone.")
		await asyncio.sleep(1)
		self.user_action_request(f"Plug in the crownstone.")

		self.logger.info("Waiting for power check to be finished.")
		await asyncio.sleep(5)

		self.logger.info("Checking if relay was turned on instead of dimmer.")
		await SwitchStateChecker(self.state_checker_args, 0, True).check()