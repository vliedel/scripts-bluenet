#!/usr/bin/env python3

import argparse
from crownstone_ble import CrownstoneBle
from crownstone_core.protocol.BluenetTypes import PowerSamplesType
import traceback
import numpy as np
import select
import sys
import json

parser = argparse.ArgumentParser(description='Search for any Crownstone and print their information')
parser.add_argument('-H', '--hciIndex', dest='hciIndex', type=int, nargs='?', default=0,
        help='The hci-index of the BLE chip')
parser.add_argument('-V', '--voltage', dest='voltageGroundTruth', type=float, nargs='?', default=0.0,
        help='The ground truth RMS voltage')
parser.add_argument('-C', '--current', dest='currentGroundTruth', type=float, nargs='?', default=0.0,
        help='The ground truth RMS current')
parser.add_argument('-P', '--power', dest='powerGroundTruth', type=float, nargs='?', default=0.0,
        help='The ground truth RMS real power')
parser.add_argument('-O', '--outputPrefix', dest='outputPrefix', type=str, nargs='?', default="output",
        help='Output filename prefix')
parser.add_argument('keyFile',
        help='The json file with key information, expected values: admin, member, guest, basic,' +
        'serviceDataKey, localizationKey, meshApplicationKey, and meshNetworkKey')
parser.add_argument('bleAddress', type=str,
        help='The BLE address of Crownstone to switch')

args = parser.parse_args()

MULTIPLIER_VOLTAGE = -0.2547
#MULTIPLIER_CURRENT = 0.0071
MULTIPLIER_CURRENT = 0.01486

class CalculatedPower:
    voltageZero = 0.0
    currentZero = 0.0
    currentRms = 0.0
    voltageRms = 0.0
    powerReal = 0.0


def calcPower(powerSamplesList, voltageMultiplier, currentMultiplier):
    voltageSamples = np.array(powerSamplesList[0].samples)
    currentSamples = np.array(powerSamplesList[1].samples)
#    voltageSamples = powerSamplesList[0].samples
#    currentSamples = powerSamplesList[1].samples
    voltageZero = calcZero(voltageSamples)
    currentZero = calcZero(currentSamples)
    voltageSamplesCorrected = (voltageSamples - voltageZero) * voltageMultiplier
    currentSamplesCorrected = (currentSamples - currentZero) * currentMultiplier
#    voltageSamplesCorrected = []
#    for v in voltageSamples:
#        voltageSamplesCorrected.append((v - voltageZero) * voltageMultiplier)
#    currentSamplesCorrected = []
#    for c in currentSamples:
#        currentSamplesCorrected.append((c - currentZero) * currentMultiplier)

    dt = powerSamplesList[0].sampleIntervalUs / 1000.0 / 1000.0
    powerSum = 0.0
    currentSum = 0.0
    voltageSum = 0.0
    timeSum = 0.0
    for i in range(0, len(voltageSamples)):
        powerSum += voltageSamplesCorrected[i] * currentSamplesCorrected[i] * dt
        currentSum += currentSamplesCorrected[i] * currentSamplesCorrected[i] * dt
        voltageSum += voltageSamplesCorrected[i] * voltageSamplesCorrected[i] * dt
        timeSum += dt
    powerReal = powerSum / timeSum
    currentRms = np.sqrt(currentSum / timeSum)
    voltageRms = np.sqrt(voltageSum / timeSum)
#    currentRms = (currentSum / timeSum) ** 0.5
#    voltageRms = (voltageSum / timeSum) ** 0.5

#     calculatedPower = CalculatedPower()
#     calculatedPower.voltageZero = voltageZero
#     calculatedPower.currentZero = currentZero
#     calculatedPower.voltageRms = voltageRms
#     calculatedPower.currentRms = currentRms
#     calculatedPower.powerReal = powerReal
#     return calculatedPower
    return {
        "voltageZero": voltageZero,
        "currentZero": currentZero,
        "voltageRms": voltageRms,
        "currentRms": currentRms,
        "powerReal": powerReal,
    }

def calcZero(samples):
    return np.mean(samples)
    # sumVal = 0.0
    # for s in samples:
    #     sumVal += s
    # return sumVal / len(samples)

def pollKeyboard():
    # dr, dw, de = select.select([sys.stdin], [], [], 0)
    # if not dr == []:
    #     return sys.stdin.read(1)
    return None

# Initialize the Bluetooth Core.
core = CrownstoneBle(hciIndex=args.hciIndex)
core.loadSettingsFromFile(args.keyFile)

try:
    print("Connecting to", args.bleAddress)
    core.connect(args.bleAddress)

    voltageZero = []
    currentZero = []
    powerReal = []
    currentRms = []
    voltageRms = []

    output = {}
    output["voltageGroundTruth"] = args.voltageGroundTruth
    output["currentGroundTruth"] = args.currentGroundTruth
    output["powerGroundTruth"] = args.powerGroundTruth
    output["calculated"] = []
    output["voltageSampes"] = []
    output["currentSampes"] = []

    try:
        for i in range(0, 20):
#            print("Retrieving power samples..")

#            powerSamplesUnfiltered = core.debug.getPowerSamples(PowerSamplesType.NOW_UNFILTERED)
#            power = calcPower(powerSamplesUnfiltered, MULTIPLIER_VOLTAGE, MULTIPLIER_CURRENT)
#            print("Unfiltered:", power)

            powerSamplesFiltered = core.debug.getPowerSamples(PowerSamplesType.NOW_FILTERED)
            power = calcPower(powerSamplesFiltered, MULTIPLIER_VOLTAGE, MULTIPLIER_CURRENT)
            print("Filtered:", power)

            output["calculated"].append(power)
            output["voltageSampes"].append(powerSamplesFiltered[0].samples)
            output["currentSampes"].append(powerSamplesFiltered[1].samples)

            key = pollKeyboard()
            if key is not None:
                print("Pressed:", key)

        fileName = args.outputPrefix + "_" + args.bleAddress + "_" + str(args.powerGroundTruth) + "W.txt"
        with open(fileName, 'w') as outfile:
            json.dump(output, outfile)

    except Exception as err:
        print("Failed to get power samples:", err)
        traceback.print_exc()

    print("Disconnect")
    core.control.disconnect()

except Exception as err:
    print("Failed to connect:", err)



core.shutDown()
