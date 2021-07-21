import asyncio
from state_checker import *
from ble_base_test import BleBaseTest, BleBaseTestArgs
from base_test import BaseTestException


class TestDimmerTemperatureHolds(BleBaseTest):
	def __init__(self, args: BleBaseTestArgs, load_min=120, load_max=160):
		super().__init__(args)
		self.load_min = load_min
		self.load_max = load_max

	def get_description(self) -> str:
		return "Check if a high load on the dimmer, but within allowed specs, does not lead to an error."

	async def _run(self):
		await self._run_with(100)
		await self._run_with(50)

	async def _run_with(self, dim_value: int):
		await self.setup()
		await DimmerReadyChecker(self.state_checker_args, True).wait_for_state_match()

		await self.set_switch(False, dim_value, True)
		await self.core.disconnect()

		self.user_action_request(f"Plug in a load of {self.load_min}W - {self.load_max}W.")
		await PowerUsageChecker(self.state_checker_args, int(self.load_min * dim_value / 100),
		                        int(self.load_max * dim_value / 100)).wait_for_state_match()
		await ErrorStateChecker(self.state_checker_args, 0).check()
		self.user_action_request("Place a phone next to the crownstone.")
		for i in range(0, 2):
			self.user_action_request("Call the phone.")
			await ErrorStateChecker(self.state_checker_args, 0).check()
			self.logger.info("Waiting 1 minute ...")
			await asyncio.sleep(1 * 60)
