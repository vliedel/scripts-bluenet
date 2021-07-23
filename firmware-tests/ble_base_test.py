import asyncio
import logging

from crownstone_core.Enums import CrownstoneOperationMode
from state_checker import *
from base_test import BaseTest, BaseTestException
from config import CrownstoneConfig, TestConfig
from crownstone_ble import CrownstoneBle

class BleBaseTestArgs:
	def __init__(self, logger: logging.Logger, config: TestConfig, ble_adapter_address: str = None):
		self.logger = logger
		self.config = config
		self.ble_adapter_address = ble_adapter_address

class BleBaseTest(BaseTest):
	# Search parameters for crownstone selection.
	use_crownstone_with_broken_igbt = False

	def __init__(self, args: BleBaseTestArgs):
		super().__init__(args.logger)
		self.config = args.config

		self.logger.info(f'Initializing with adapter address={args.ble_adapter_address}')
		self.core = CrownstoneBle(bleAdapterAddress=args.ble_adapter_address)
		self.core.setSettings(
			self.config.keys.admin,
			self.config.keys.member,
			self.config.keys.basic,
			self.config.keys.service_data,
			self.config.keys.localization,
			self.config.keys.mesh_app,
			self.config.keys.mesh_net
		)

		self.crownstone: CrownstoneConfig = None
		for cs in self.config.crownstones:
			if cs.igbt_broken == self.use_crownstone_with_broken_igbt:
				self.crownstone = cs
				break
		if self.crownstone is None:
			BaseTestException("No crownstone config found.")

		self.address = self.crownstone.address
		self.state_checker_args = StateCheckerArgs(self.core, self.address, self.logger)



	async def _run(self):
		await self.reset_config()
		await self._run_ble()
		await self.core.shutDown()

	async def _run_ble(self):
		"""
		Run the test, raise exception when it fails.

		To be implemented by derived class.
		"""
		raise BaseTestException("Not implemented: _run_ble()")

	async def factory_reset(self):
		"""
		Perform factory reset if the stone is in normal mode.
		"""
		op_mode = await self.core.getMode(self.address)
		if op_mode == CrownstoneOperationMode.NORMAL:
			self.logger.info("Crownstone is in normal mode, attempting to factory reset ...")
			await self.connect()
			await self.core.control.commandFactoryReset()
			await self.core.disconnect()
			await asyncio.sleep(3.0)

	async def setup(self):
		"""
		Perform setup if the stone is in setup mode.
		"""
		op_mode = await self.core.getMode(self.address)
		if op_mode == CrownstoneOperationMode.SETUP:
			self.logger.info("Crownstone is in setup mode, performing setup ...")
			await self.core.setup.setup(self.address,
			                       self.config.sphere.id,
			                       self.crownstone.id,
			                       self.crownstone.mesh_device_key,
			                       self.config.sphere.ibeacon_uuid,
			                       self.crownstone.ibeacon_major,
			                       self.crownstone.ibeacon_minor)

	async def reset_config(self):
		"""
		Reset the config of the crownstone, by making sure a factory reset is performed.
		"""
		self.logger.info("Resetting crownstone config ...")
		op_mode = await self.core.getMode(self.address)
		if op_mode == CrownstoneOperationMode.NORMAL:
			await self.factory_reset()
		else:
			await self.setup()
			await self.factory_reset()

	async def reset_errors(self):
		"""
		Reset errors and check if the errors are reset indeed.
		"""
		await self.connect()
		await self.core.control.resetErrors()
		await ErrorStateChecker(self.state_checker_args, 0).check()
		await self.core.disconnect()

	async def connect(self):
		"""
		Connect to device.
		Also works when already connected.
		"""
		connected = await self.core.ble.is_connected(self.address)
		if connected:
			# Already connected to this address.
			return
		connected = await self.core.ble.is_connected()
		if connected:
			raise Exception("Already connected to another device.")
		self.logger.info(f"Connecting to {self.address}")
		await self.core.connect(self.address)

	async def set_switch(self, relay_on: bool, dim_value: int, allow_dimming: bool = None, switch_lock: bool = None):
		"""
		Set switch, dimming allowed, and lock.
		Checks if setting was successful.
		:param relay_on:      Whether to turn on the relay.
		:param dim_value:     Dim value as percentage.
		:param allow_dimming: True or False to set allow dimming. None to leave it as it is.
		:param switch_lock:   True or False to set switch lock. None to leave it as it is.
		"""
		await self.connect()

		if switch_lock == False:
			await self.set_switch_lock(switch_lock)

		if allow_dimming is not None:
			await self.set_allow_dimming(allow_dimming)

		relay_str = "on" if relay_on else "off"
		self.logger.info(f"Turning relay {relay_str}, setting dimmer at {dim_value}%.")
		await self.core.control.setRelay(relay_on)
		await self.core.control.setDimmer(dim_value)
		await SwitchStateChecker(self.state_checker_args, dim_value, relay_on).check()

		if switch_lock == True:
			# Don't check, since allow dimming overrides switch lock.
			await self.set_switch_lock(switch_lock, False)

	async def set_switch_should_fail(self, relay_on: bool, dim_value: int, unlock_switch: bool = True):
		"""
		Try setting the switch, but expect the switch state to remain unchanged.
		:param relay_on:      Whether to turn on the relay.
		:param dim_value:     Dim value as percentage.
		:param unlock_switch: Whether to unlock the switch before setting the switch.
		"""
		relay_str = "on" if relay_on else "off"
		self.logger.info(f"Trying to set relay {relay_str}, and dimmer to {dim_value}. This should not be allowed.")
		await self.connect()
		switch_state_before = await self.core.state.getSwitchState()
		if unlock_switch:
			await self.set_switch_lock(False)
		await self.set_allow_dimming(True)
		await self.core.control.setRelay(relay_on)
		await self.core.control.setDimmer(dim_value)
		switch_value = dim_value
		if relay_on:
			switch_value = 100
		await self.core.control.setSwitch(switch_value)
		switch_state_after = await self.core.state.getSwitchState()
		if switch_state_before.raw != switch_state_after.raw:
			raise BaseTestException(f"Switch state changed from {switch_state_before} to {switch_state_after}")

	async def set_allow_dimming(self, allow: bool):
		"""
		Set allow dimming, and check the result.
		:param allow: True to allow dimming.
		"""
		self.logger.info(f"Setting allow dimming {allow}.")
		await self.connect()
		await self.core.control.allowDimming(allow)
		await DimmingAllowedChecker(self.state_checker_args, allow).check()

	async def set_switch_lock(self, lock: bool, check: bool = True):
		"""
		Set switch lock.
		:param lock:  True to lock the switch.
		:param check: True to check the result.
		"""
		self.logger.info(f"Setting switch lock {lock}.")
		await self.connect()
		await self.core.control.lockSwitch(lock)
		if check:
			await SwitchLockChecker(self.state_checker_args, lock).check()
