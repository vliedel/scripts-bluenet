import argparse
import asyncio
import datetime
import json
import logging
import os
import traceback

from ble_base_test import *
from config import load_config

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


argParser = argparse.ArgumentParser(description="Interactive script for softfuse tests")
argParser.add_argument('--list',
                       '-l',
                       dest='list',
                       action='store_true',
                       help='List all tests, and end the program.')
argParser.add_argument('--config',
                       '-c',
                       dest='config_file',
                       metavar='config file',
                       type=str,
                       default='config.yaml',
                       help='Configuration file.')
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
                       default=datetime.datetime.now().strftime("output_%Y-%m-%d_%H:%M:%S"),
                       help='The prefix sof files to write the logs and state to.')
argParser.add_argument('--debug',
                       '-d',
                       dest='debug',
                       action='store_true',
                       help='Debug output.')
argParser.add_argument('--verbose',
                       '-v',
                       dest='verbose',
                       action='store_true',
                       help='Verbose output.')
args = argParser.parse_args()

tests_list = [
	TestSwitchLock,
	TestDimmerBoot,
	TestDimmingAllowed,
	TestDimmerCurrentHolds,
	TestDimmerCurrentOverload,
	TestChipOverheat,
	TestDimmerTemperatureHolds,
	TestDimmerTemperatureOverheat,
	TestIgbtFailureDetectionHolds,
	TestIgbtFailureDetection,
	TestChipOverheatAndIgbtFailure
]

if args.list:
	for test in tests_list:
		print(f"{test.get_name()}")
	exit(0)


config = load_config(args.config_file)

# Setup the logger.
log_file_name = args.output_file_prefix + ".log"
log_format = '[%(asctime)s.%(msecs)03d] [%(filename)-20.20s:%(lineno)3d] %(levelname)-1.1s %(message)s'
log_date_format = '%Y-%m-%d %H:%M:%S'

if args.verbose:
	logging.basicConfig(format=log_format, level=logging.DEBUG, filename=log_file_name, datefmt=log_date_format)
else:
	logging.basicConfig(format=log_format, level=logging.INFO, filename=log_file_name, datefmt=log_date_format)

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


# Create the state file.
state_file_name = args.output_file_prefix + ".json"
state = {}
if os.path.exists(state_file_name):
	with open(state_file_name, 'r') as state_file:
		try:
			state = json.load(state_file)
		except:
			traceback.print_exc()
			print("Failed to parse file", state_file_name)
			exit(1)


# Create the result file.
result_file_name = args.output_file_prefix + "_result.txt"
try:
	result_file = open(result_file_name, 'w')
except:
	traceback.print_exc()
	print("Failed to open file", result_file_name)
	exit(1)


ble_base_args = BleBaseTestArgs(logger, config, args.adapter_address)



def state_set(key: str = None, val = None):
	if key is not None:
		state[key] = val
	try:
		state_file = open(state_file_name, 'w')
		json.dump(state, state_file)
		state_file.close()
	except:
		traceback.print_exc()
		print("Failed to store state to file", state_file_name)
		exit(1)

async def run_test(t):
	test = t(ble_base_args)
	logger.info("=" * 30)
	logger.info(f"Run test: {t.get_name()}")
	logger.info(f"{t.get_description()}")
	logger.info("=" * 30)
	result = await test.run()
	result_str = "passed" if result else "failed"
	logger.info("=" * 30)
	logger.info(f"Test {test.get_name()} {result_str}.")
	logger.info("=" * 30)
	result_file.write(f"{test.get_name()} {result_str}\n")
	state_set(test.get_name(), result)

async def main():
	if config.tests is not None:
		test_name_list = []
		for test_name in config.tests:
			for test in tests_list:
				if test.get_name() == test_name:
					await run_test(test)
					break
	else:
		for test in tests_list:
			await run_test(test)


try:
	loop = asyncio.get_event_loop()
	loop.run_until_complete(main())
except KeyboardInterrupt:
	print("Closing the test.")
