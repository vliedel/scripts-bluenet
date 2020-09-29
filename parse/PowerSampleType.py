from enum import Enum

class PowerSampleType(Enum):
	TriggeredSwitchcraft = 0
	NonTriggeredSwitchcraft = 1
	Filtered = 2
	Unfiltered = 3
	SoftFuse = 4

class BufferType(Enum):
	Voltage = 0
	Current = 1

def hasBothVoltageAndCurrentBuffers(samplesType: PowerSampleType):
	""" Returns true when there are both voltage and current buffers. """
	if samplesType == PowerSampleType.TriggeredSwitchcraft or samplesType == PowerSampleType.NonTriggeredSwitchcraft:
		return False
	if samplesType == PowerSampleType.Filtered or samplesType == PowerSampleType.Unfiltered:
		return True
	if samplesType == PowerSampleType.SoftFuse:
		return False
	print("Unknown type:", samplesType)
	return False

def getBufferType(samplesType: PowerSampleType, bufIndex):
	""" Returns buffer type. """
	if samplesType == PowerSampleType.TriggeredSwitchcraft or samplesType == PowerSampleType.NonTriggeredSwitchcraft:
		return BufferType.Voltage
	if samplesType == PowerSampleType.Filtered or samplesType == PowerSampleType.Unfiltered:
		if bufIndex % 2 == 0:
			return BufferType.Voltage
		else:
			return BufferType.Current
	if samplesType == PowerSampleType.SoftFuse:
		return BufferType.Current
	print("Unknown type:", samplesType)
	return BufferType.Voltage