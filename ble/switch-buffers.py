#!/usr/bin/env python3

import argparse
from crownstone_ble import CrownstoneBle
from crownstone_core.protocol.BluenetTypes import PowerSamplesType
import traceback
import numpy as np
import select
import sys
import json
import time
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Search for any Crownstone and print their information')
parser.add_argument('-H', '--hciIndex', dest='hciIndex', type=int, nargs='?', default=0,
        help='The hci-index of the BLE chip')
parser.add_argument('-O', '--outputPrefix', dest='outputPrefix', type=str, nargs='?', default="switchSamples",
        help='Output filename prefix')
parser.add_argument('keyFile',
        help='The json file with key information, expected values: admin, member, guest, basic,' +
        'serviceDataKey, localizationKey, meshApplicationKey, and meshNetworkKey')
parser.add_argument('bleAddress', type=str,
        help='The BLE address of Crownstone to switch')

args = parser.parse_args()


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

    output = {}
    output["voltageSampes"] = []
    output["currentSampes"] = []

    voltageMultiplier = 1.0
    currentMultiplier = 1.0

    try:
        switchCmd = 1
        for i in range(0, 2):
#            print("Retrieving power samples..")

#            powerSamplesUnfiltered = core.debug.getPowerSamples(PowerSamplesType.NOW_UNFILTERED)
#            power = calcPower(powerSamplesUnfiltered, MULTIPLIER_VOLTAGE, MULTIPLIER_CURRENT)
#            print("Unfiltered:", power)

            core.control.setSwitchState(switchCmd)
            if switchCmd == 0:
                switchCmd = 1
            else:
                switchCmd = 0

            powerSamples = core.debug.getPowerSamples(PowerSamplesType.SWITCH)

            voltageSamples = []
            currentSamples = []
            for k in range(0, int(len(powerSamples) / 2)):
                voltageSamples.extend(powerSamples[2 * k].samples)
                currentSamples.extend(powerSamples[2 * k + 1].samples)
            voltageMultiplier = powerSamples[0].multiplier
            currentMultiplier = powerSamples[1].multiplier

            print(voltageSamples)
            print(currentSamples)
            output["voltageSampes"].append(voltageSamples)
            output["currentSampes"].append(currentSamples)

            time.sleep(3)

        fileName = args.outputPrefix + "_" + args.bleAddress + ".txt"
        with open(fileName, 'w') as outfile:
            json.dump(output, outfile)
            outfile.write("")

    except Exception as err:
        print("Failed to get power samples:", err)
        traceback.print_exc()

    print("Disconnect")
    core.control.disconnect()

    fig, (ax1, ax2) = plt.subplots(2, sharex=True)


    # voltageSamples = np.array(output["voltageSampes"]).transpose()
    # currentSamples = np.array(output["currentSampes"]).transpose()
    for i in range(0, len(output["voltageSampes"])):
        voltageSamples = np.array(output["voltageSampes"][i]) * voltageMultiplier
        currentSamples = np.array(output["currentSampes"][i]) * currentMultiplier
        t = np.array(range(i * len(voltageSamples), (1+i) * len(voltageSamples)))
        ax1.plot(t, voltageSamples)
        ax2.plot(t, currentSamples)
    plt.show()

except Exception as err:
    print("Failed to connect:", err)



core.shutDown()
