import argparse
import asyncio
import datetime
import logging

from crownstone_ble import CrownstoneBle

from test_chip_overheat import TestChipOverheat
from test_chip_overheat_and_igbt_failure import TestChipOverheatAndIgbtFailure
from test_dimmer_boot import TestDimmerBoot
from test_dimmer_current_holds import TestDimmerCurrentHolds
from test_dimmer_current_overload import TestDimmerCurrentOverload
from test_dimmer_temperature import TestDimmerTemperatureHolds, TestDimmerTemperatureOverheat
from test_dimming_allowed import TestDimmingAllowed
from test_igbt_failure_detection import TestIgbtFailureDetection
from test_igbt_failure_detection_holds import TestIgbtFailureDetectionHolds
from test_switch_lock import TestSwitchLock

from ble_base_test import *


argParser = argparse.ArgumentParser(description="Interactive script for softfuse tests")
argParser.add_argument('--crownstoneAddress',
                       dest='crownstone_address',
                       metavar='MAC address',
                       type=str,
                       required=True,
                       help='The MAC address of the Crownstone to test.')
argParser.add_argument('--brokenCrownstoneAddress',
                       dest='broken_crownstone_address',
                       metavar='MAC address',
                       type=str,
                       required=True,
                       help='The MAC address of the Crownstone with broken IGBT (always on) to test.')
argParser.add_argument('--adapterAddress',
                       '-a',
                       dest='adapter_address',
                       metavar='MAC address',
                       type=str,
                       default=None,
                       help='Adapter MAC address of the bluetooth chip you want to use (linux only). You can get a list by running: hcitool dev')
argParser.add_argument('--outputFilePrefix',
                       '-o',
                       dest='output_file_prefix',
                       metavar='output file',
                       type=str,
                       default=datetime.datetime.now().strftime("output_%Y-%m-%d"),
                       help='The prefix sof files to write the logs and state to.')
argParser.add_argument('--verbose',
                       '-v',
                       dest='verbose',
                       action='store_true',
                       help='Verbose output')
argParser.add_argument('--debug',
                       '-d',
                       dest='debug',
                       action='store_true',
                       help='Debug output')
args = argParser.parse_args()


# Setup the logger.
log_file_name = args.output_file_prefix + ".log"
log_format = '[%(asctime)s.%(msecs)03d] [%(filename)-20.20s:%(lineno)3d] %(levelname)-1.1s %(message)s'
log_date_format = '%Y-%m-%d %H:%M:%S'

if args.verbose:
	logging.basicConfig(format=log_format, level=logging.DEBUG, filename=log_file_name, datefmt=log_date_format)
else:
	logging.basicConfig(format=log_format, level=logging.WARNING, filename=log_file_name, datefmt=log_date_format)

# Also output to console, but with a simpler format, and no debug logs.
console = logging.StreamHandler()
console.setLevel(logging.INFO)
log_format = '[%(asctime)s] %(message)s'
console.setFormatter(logging.Formatter(log_format, "%H:%M:%S"))
# Add the handler to the root logger
logging.getLogger('').addHandler(console)

logger = logging.getLogger("firmware-tests")
if args.debug:
	logger.setLevel(logging.DEBUG)


# Create the BLE library instance.
logger.info(f'Initializing with adapter address={args.adapter_address}')
core = CrownstoneBle(bleAdapterAddress=args.adapter_address)
core.setSettings("adminKeyForCrown", "memberKeyForHome", "basicKeyForOther", "MyServiceDataKey", "aLocalizationKey", "MyGoodMeshAppKey", "MyGoodMeshNetKey")


# Fill required arguments.
setup_args = BleBaseTestSetupArgs(
	crownstone_id=230,
	mesh_device_key="mesh_device_key1",
	ibeacon_major=1234,
	ibeacon_minor=5678)

ble_base_args = BleBaseTestArgs(
	core,
	args.crownstone_address,
	logger,
	setup_args)

broken_crownstone_setup_args = BleBaseTestSetupArgs(
	crownstone_id=231,
	mesh_device_key="mesh_device_key2",
	ibeacon_major=1234,
	ibeacon_minor=5679)

broken_crownstone_args = BleBaseTestArgs(
	core,
	args.broken_crownstone_address,
	logger,
	broken_crownstone_setup_args)

async def main():
	await TestSwitchLock(ble_base_args).run()
	await TestDimmerBoot(ble_base_args).run()
	await TestDimmingAllowed(ble_base_args).run()
	await TestDimmerCurrentHolds(ble_base_args).run()
	await TestDimmerCurrentOverload(ble_base_args).run()
	await TestChipOverheat(ble_base_args).run()
	await TestDimmerTemperatureHolds(ble_base_args).run()
	await TestDimmerTemperatureOverheat(ble_base_args).run()
	await TestIgbtFailureDetectionHolds(ble_base_args).run()

	await TestIgbtFailureDetection(broken_crownstone_args).run()
	await TestChipOverheatAndIgbtFailure(broken_crownstone_args).run()

try:
	loop = asyncio.get_event_loop()
	loop.run_until_complete(main())
except KeyboardInterrupt:
	print("Closing the test.")
finally:
	core.shutDown()
