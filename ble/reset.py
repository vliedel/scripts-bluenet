#!/usr/bin/env python3

from BluenetLib.BLE import BluenetBle

# Settings
ADMIN_KEY =  "adminKeyForCrown"
MEMBER_KEY = "memberKeyForHome"
GUEST_KEY =  "guestKeyForOther"
ADDRESS =    "01:23:45:67:89:AB"
HCI_INDEX =  0

# Initialize the Bluetooth Core
core = BluenetBle(hciIndex=HCI_INDEX)
core.setSettings(ADMIN_KEY, MEMBER_KEY, GUEST_KEY)

# Connect and send command
print("Connecting to", ADDRESS)
core.connect(ADDRESS)
print("Send reset command")
core.control.reset()
print("Disconnect")
core.control.disconnect()

# Clean up
print("Done")
core.shutDown()
