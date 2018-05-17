#!/usr/bin/env python3

from BluenetLib.BLE import BluenetBle

ADMIN_KEY =  "adminKeyForCrown"
MEMBER_KEY = "memberKeyForHome"
GUEST_KEY =  "guestKeyForOther"
ADDRESS =    "01:23:45:67:89:AB"

# Initialize the Bluetooth Core
core = BluenetBle()
core.setSettings(ADMIN_KEY, MEMBER_KEY, GUEST_KEY)

# Connect and send command
core.connect(ADDRESS)
core.control.reset()
core.control.disconnect()

# Clean up
core.shutDown()