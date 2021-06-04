#!/usr/bin/env python3

import argparse
from crownstone_ble import CrownstoneBle
import time

parser = argparse.ArgumentParser(description='Search for any Crownstone and print their information')
parser.add_argument('-H', '--hciIndex', dest='hciIndex', type=int, nargs='?', default=0,
        help='The hci-index of the BLE chip')
parser.add_argument('-N', '--times', dest='numSwitches', type=int, nargs='?', default=2,
        help='Number of times to switch')
parser.add_argument('-U', '--sphere', dest='sphereUid', type=int, nargs='?', default=0,
        help='The sphere UID')
parser.add_argument('-I', '--id', dest='stoneId', type=int, nargs='?', default=0,
        help='The crownstone ID')
parser.add_argument('keyFile',
        help='The json file with key information, expected values: admin, member, guest, basic,' +
        'serviceDataKey, localizationKey, meshApplicationKey, and meshNetworkKey')

args = parser.parse_args()
print("Using hci:", args.hciIndex, ", sphere UID:", args.sphereUid, ", crownstone ID:", args.stoneId, ", key file:", args.keyFile)

# Initialize the Bluetooth Core.
core = CrownstoneBle(hciIndex=args.hciIndex)
core.loadSettingsFromFile(args.keyFile)

cmd = 0 # 0 = off, you can choose anything between [0..1]

#ids = [71, 72, 73, 74, 75, 76]
ids = [74, 76]

for i in range(0, args.numSwitches):
	cmd = 1
	print("Set switch to", cmd)
	for id in ids:
		core.broadcast.switchCrownstone(args.sphereUid, id, cmd)
	time.sleep(3)

	cmd = 0
	print("Set switch to", cmd)
	for id in ids:
		core.broadcast.switchCrownstone(args.sphereUid, id, cmd)
	time.sleep(15)



#	core.broadcast.switchCrownstone(args.sphereUid, args.stoneId, cmd)
#	time.sleep(1)
#	if cmd == 0:
#		cmd = 1
#	else:
#		cmd = 0

core.shutDown()
