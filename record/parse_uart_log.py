
import re
import datetime
import numpy as np

# Config
RTC_CLOCK_FREQ = 32768
MAX_RTC_COUNTER_VAL = 0x00FFFFFF
SAMPLE_TIME_US = 200

# Expected number of samples per buffer.
NUM_SAMPLES = 100

# [timeFormat] Voltage: 1 2 3 4 5 .. NUM_SAMPLES
samplesPattern      = re.compile("\[.*\] ([cC]urrent|[vV]oltage): ([0-9\- ]*)")

timePattern         = re.compile("^\[([^\]]+)\]")
temperaturePattern  = re.compile(".* T=(-?\d+)")
currentPattern      = re.compile(".* Crms=(-?\d+)")
voltagePattern      = re.compile(".* Vrms=(-?\d+)")
powerPattern        = re.compile(".* P=(-?\d+)")
currentZeroPattern  = re.compile(".* C0=(-?\d+)")
forceRelayOnPattern = re.compile(".* forceRelayOn")
timeFormat = "%Y-%m-%d %H:%M:%S.%f"


def parse(fileName):
    # Read the log file and store in a string array
    with open(fileName, 'r') as file:
        data = file.readlines()

        # Start parsing
        currentSamples = []
        currentSamplesTime = []
        voltageSamples = []
        voltageSamplesTime = []
        temperatures = []
        temperaturesTime = []
        relays = []
        relaysTime = []
        currents = []
        currentsTime = []
        voltages = []
        voltagesTime = []
        powers = []
        powersTime = []
        currentZeros = []
        currentZerosTime = []

        timestamp = 0
        firstTimestamp = None
        temperature = 0
        relay = 0
        current = 0
        voltage = 0
        power = 0
        currentZero = 0
        voltageZero = 0
        powerCalc = 0.0
        currentMean = 0.0
        voltageMean = 0.0

        for line in data:

            match = timePattern.match(line)
            if (match):
                time = datetime.datetime.strptime(match.group(1), timeFormat)
                timestamp = time.timestamp()
                if (firstTimestamp is None):
                    firstTimestamp = timestamp
                timestamp -= firstTimestamp

            match = samplesPattern.match(line)
            if (match):
                samples = []
                sampleTypeStr = match.group(1).lower()
                sampleStrings = match.group(2).strip().split(' ')

                if (len(sampleStrings) == NUM_SAMPLES):
                    for s in sampleStrings:
                        try:
                            sample = int(s)
                        except:
                            print("Invalid sample value:", s, "in line:", line)
                            exit(1)
                        samples.append(sample)
                    timestamps = timestamp + np.array(range(0, len(samples))) * SAMPLE_TIME_US / 1000 / 1000

                    if (sampleTypeStr == "current"):
                        currentSamples.append(samples)
                        currentSamplesTime.append(timestamps)
                    else:
                        voltageSamples.append(samples)
                        voltageSamplesTime.append(timestamps)

            match = temperaturePattern.match(line)
            if (match):
                temperature = int(match.group(1).strip())
                temperatures.append(temperature)
                temperaturesTime.append(timestamp)

            match = forceRelayOnPattern.match(line)
            if (match):
                relay = 1
                relays.append(relay)
                relaysTime.append(timestamp)
                relays.append(0)
                relaysTime.append(timestamp)

            match = currentPattern.match(line)
            if (match):
                current = int(match.group(1).strip())
                currents.append(current)
                currentsTime.append(timestamp)

            match = voltagePattern.match(line)
            if (match):
                voltage = int(match.group(1).strip())
                voltages.append(voltage)
                voltagesTime.append(timestamp)

            match = powerPattern.match(line)
            if (match):
                power = int(match.group(1).strip())
                powers.append(power)
                powersTime.append(timestamp)

            match = currentZeroPattern.match(line)
            if (match):
                currentZero = int(match.group(1).strip()) / 1000.0
                currentZeros.append(currentZero)
                currentZerosTime.append(timestamp)

    # Only return current and voltage for now.
    return {
        'current': (currentSamplesTime, currentSamples),
        'voltage': (voltageSamplesTime, voltageSamples),
    }