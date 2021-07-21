import asyncio
from state_checker import *
from ble_base_test import BleBaseTest, BleBaseTestArgs
from base_test import BaseTestException

class TestIgbtFailureDetectionHolds(BleBaseTest):
	def __init__(self, args: BleBaseTestArgs):
		super().__init__(args)
		self.load_min = 2500
		self.load_max = 3000

	def get_description(self) -> str:
		return "Check if power usage averaging does not lead to a false positive in IGBT on failure detection."

	async def _run(self):
		await self.setup()

		# Make sure the load is plugged in.
		await self.set_switch(True, 0)
		await self.core.disconnect()

		self.user_action_request(f"Plug in a load of {self.load_min}W - {self.load_max}W.")
		await PowerUsageChecker(self.state_checker_args, self.load_min, self.load_max).wait_for_state_match()

		self.logger.info("Check if the softfuse doesn't trigger right after turning off the switch.")
		for i in range(0, 5):
			self.logger.info(f"Check {i}")
			await self.connect()
			await self.core.control.setRelay(True)
			self.logger.info(f"Waiting ...")
			await asyncio.sleep(10)
			await self.core.control.setRelay(False)
			await ErrorStateChecker(self.state_checker_args, 0).check()
			await self.core.disconnect()

		# Make sure switch is off at boot.
		await self.connect()
		await self.core.control.setRelay(False)
		await SwitchStateChecker(self.state_checker_args, 0, False).check()
		await self.core.disconnect()
		self.logger.info(f"Waiting for switch state to be stored ...")
		await asyncio.sleep(10)

		self.logger.info("Check if the softfuse doesn't trigger at boot.")
		for i in range(0, 5):
			self.user_action_request(f"Plug out (or power off) the crownstone. Keep the load plugged into the crownstone.")
			await asyncio.sleep(3)
			self.user_action_request(f"Plug in (or power on) the crownstone.")
			await ErrorStateChecker(self.state_checker_args, 0).check()
