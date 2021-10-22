#!/usr/bin/env python3
import argparse
import asyncio

import crownstone_core
from crownstone_ble import CrownstoneBle

# Init the Crownstone BLE lib.
from crownstone_core import Conversion
from crownstone_core.Exceptions import CrownstoneException, CrownstoneBleException
from crownstone_core.packets.BasePacket import BasePacket
from crownstone_core.protocol.BlePackets import ControlPacket
from crownstone_core.protocol.BluenetTypes import ControlType
from crownstone_core.util.BufferWriter import BufferWriter

ble = CrownstoneBle()

print("core version:", crownstone_core.__version__)
print("ble version: ", ble.__version__)





argParser = argparse.ArgumentParser(description="Test tracked devices")
argParser.add_argument('--address',
                       '-a',
                       dest='address',
                       type=str,
                       required=True,
                       help='The MAC addresses / handles of the Crownstone you want to connect to. For example: AA:BB:CC:DD:EE:FF,11:22:33:44:55:66')
argParser.add_argument('--verbose',
                       '-v',
                       dest='verbose',
                       action='store_true',
                       help='Verbose output.')
args = argParser.parse_args()


addresses = args.address.split(',')


class RegisterTrackedDevicePacket(BasePacket):
	def __init__(self):
		self.deviceId = 0
		self.locationId = 0
		self.profileId = 0
		self.rssiOffset = 0
		self.flags = 0
		self.deviceToken = 0
		self.timeToLiveMinutes = 120

	def _serialize(self, writer: BufferWriter):
		writer.putUInt16(self.deviceId)
		writer.putUInt8(self.locationId)
		writer.putUInt8(self.profileId)
		writer.putInt8(self.rssiOffset)
		writer.putUInt8(self.flags)
		writer.putBytes(Conversion.uint32_to_uint8_array(self.deviceToken)[0:3])
		writer.putUInt16(self.timeToLiveMinutes)

	def __str__(self):
		return f"RegisterTrackedDevicePacket(" \
		       f"deviceId={self.deviceId} " \
		       f"locationId={self.locationId} " \
		       f"profileId={self.profileId} " \
		       f"rssiOffset={self.rssiOffset} " \
		       f"flags={self.flags} " \
		       f"deviceToken={self.deviceToken} " \
		       f"timeToLiveMinutes={self.timeToLiveMinutes})"

class TrackedDeviceHeartbeatPacket(BasePacket):
	def __init__(self):
		self.deviceId = 0
		self.locationId = 0
		self.deviceToken = 0
		self.timeToLiveMinutes = 3

	def _serialize(self, writer: BufferWriter):
		writer.putUInt16(self.deviceId)
		writer.putUInt8(self.locationId)
		writer.putBytes(Conversion.uint32_to_uint8_array(self.deviceToken)[0:3])
		writer.putUInt8(self.timeToLiveMinutes)

	def __str__(self):
		return f"TrackedDeviceHeartbeatPacket(" \
		       f"deviceId={self.deviceId} " \
		       f"locationId={self.locationId} " \
		       f"deviceToken={self.deviceToken} " \
		       f"timeToLiveMinutes={self.timeToLiveMinutes})"


def setBit(packet: list, bit):
	index = len(packet) - 1 - int(bit / 8)
	packet[index] |= 1 << (bit % 8)

class BroadcastPacket(BasePacket):
	def __init__(self):
		self.protocol = 1
		self.deviceToken = 0
		self.packet = 16*[0]

	def _serialize(self, writer: BufferWriter):
		self.packet = 16*[0]

		part = 0
		part |= (self.protocol & 0x03) << (42 - 2)
		part |= (self.deviceToken & 0xFFFFFF) << (42 - 2 - 3*8)
		print(f"part={part}")

		for i in range(0, 42):
			if part & (1 << i):
				setBit(self.packet, i + 2)
				setBit(self.packet, i + 42 + 2)
				setBit(self.packet, i + 2*42 + 2)
		writer.putBytes(self.packet)

		print(f"packet={self.packet}")

		left = (self.packet[0] << (7*8)) + \
		       (self.packet[1] << (6*8)) + \
		       (self.packet[2] << (5*8)) + \
		       (self.packet[3] << (4*8)) + \
		       (self.packet[4] << (3*8)) + \
		       (self.packet[5] << (2*8)) + \
		       (self.packet[6] << (1*8)) + \
		       (self.packet[7] << (0*8))

		right = (self.packet[0+8] << (7*8)) + \
		        (self.packet[1+8] << (6*8)) + \
		        (self.packet[2+8] << (5*8)) + \
		        (self.packet[3+8] << (4*8)) + \
		        (self.packet[4+8] << (3*8)) + \
		        (self.packet[5+8] << (2*8)) + \
		        (self.packet[6+8] << (1*8)) + \
		        (self.packet[7+8] << (0*8))

		print(f"left={left} right={right}")

		# Divide the data into 3 parts, and do a bitwise majority vote, to correct for errors.
		# Each part is 42 bits.
		part1 = (left >> (64-42)) & 0x03FFFFFFFFFF # First 42 bits from left.
		part2 = ((left & 0x3FFFFF) << 20) | ((right >> (64-20)) & 0x0FFFFF) # Last 64-42=22 bits from left, and first 42−(64−42)=20 bits from right.
		part3 = (right >> 2) & 0x03FFFFFFFFFF # Bits 21-62 from right.
		result = ((part1 & part2) | (part2 & part3) | (part1 & part3)) # The majority vote
		print(f"part1={part1} part2={part2} part3={part3} result={result}")

		# Parse the resulting data.
		protocol = (result >> (42-2)) & 0x03
		deviceToken = 3 * [0]
		deviceToken[0] = (result >> (42-2-8)) & 0xFF
		deviceToken[1] = (result >> (42-2-8-8)) & 0xFF
		deviceToken[2] = (result >> (42-2-8-8-8)) & 0xFF
		print(f"protocol={protocol}, deviceToken={Conversion.uint8_array_to_hex_string(deviceToken)}")



broadcast_packet = BroadcastPacket()
broadcast_packet.deviceToken = 0 + 0xABCD00
print(f"broadcast_packet={Conversion.uint8_array_to_hex_string(broadcast_packet.serialize())}")




async def main():
	deviceCount = 2
	locationCount = 64

	repeats = 1000

	try:
		for i in range(0, repeats):
			try:

				# Register
				for address in addresses:
					await ble.connect(address)
					for deviceId in range(0, deviceCount):
						packet = RegisterTrackedDevicePacket()
						packet.deviceId = deviceId
						packet.locationId = 0
						packet.deviceToken = deviceId + 0xABCD00
						control_packet = ControlPacket(ControlType.REGISTER_TRACKED_DEVICE).loadByteArray(packet.serialize())
						result = await ble.control._writeControlAndGetResult(control_packet.serialize())
						print(f"Register ret_code={result.resultCode} packet={packet}")
					await ble.disconnect()

				# Heartbeat
				for address in addresses:
					await ble.connect(address)
					for locationId in range(0, locationCount):
						for deviceId in range(0, deviceCount):
							packet = TrackedDeviceHeartbeatPacket()
							packet.deviceId = deviceId
							packet.locationId = locationId
							packet.deviceToken = deviceId + 0xABCD00
							control_packet = ControlPacket(ControlType.TRACKED_DEVICE_HEARTBEAT).loadByteArray(packet.serialize())
							result = await ble.control._writeControlAndGetResult(control_packet.serialize())
							print(f"Heartbeat ret_code={result.resultCode} packet={packet}")
					await ble.disconnect()
			except (CrownstoneException, CrownstoneBleException) as e:
				print(e)

			# Wait
			await asyncio.sleep(10)

	except KeyboardInterrupt:
		pass
	finally:
		await ble.shutDown()

asyncio.run(main())
