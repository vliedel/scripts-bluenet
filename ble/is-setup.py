#!/usr/bin/env python3

import time
import argparse
import json

from crownstone_ble import CrownstoneBle, ScanBackends

parser = argparse.ArgumentParser(description='Search for any Crownstone and print their information')
parser.add_argument('--hciIndex', dest='hciIndex', metavar='I', type=int, nargs='?', default=0,
        help='The hci-index of the BLE chip')
parser.add_argument('keyFile',
        help='The json file with key information, expected values: admin, member, guest, basic,' +
        'serviceDataKey, localizationKey, meshApplicationKey, and meshNetworkKey')
parser.add_argument('macAddress', type=str,
        help='The bluetooth MAC address of the Crownstone to connect to.')

args = parser.parse_args()

print("===========================================\n\ncsutil\n\n===========================================")

# Initialize the Bluetooth Core.
core = CrownstoneBle(hciIndex=args.hciIndex)
core.loadSettingsFromFile(args.keyFile)

address = args.macAddress

def setup_test():
    print("Is Crownstone in setup mode at address:", address)

    # Does not seem to work properly
    if core.isCrownstoneInSetupMode(address):
        print("Crownstone is in setup mode")
    else:
        print("Crownstone is not in setup mode")

    print("Sleep to be easy on the lib")
    time.sleep(10)

setup_test()

# clean up all pending processes
print("Core shutdown")
core.shutDown()