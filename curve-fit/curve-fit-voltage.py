#!/usr/bin/python3

"""
Use recorded data as input, and fit a curve to that.

For json: recorded data with record-voltage.py
For txt of log: recorded UART logs.
"""

import sys
sys.path.append('../record')
import parse_recorded_voltage

import numpy as np
import matplotlib.pyplot as plt
import gauss_newton

NUM_SAMPLES_FOR_FIT = 300
NUM_FIT_ITERATIONS = 10
ESTIMATED_FREQUENCY = 50

def main():
    fileNames = sys.argv[1:]

    print(fileNames)

    for fileName in fileNames:
        allTimestamps, allSamples = parse_recorded_voltage.parse(fileName)

        for i in range(0, len(allTimestamps)):
            if (len(allTimestamps[i]) < NUM_SAMPLES_FOR_FIT):
                continue

            t = np.array(allTimestamps[i][0:NUM_SAMPLES_FOR_FIT])
            y = np.array(allSamples[i][0:NUM_SAMPLES_FOR_FIT])

            guess_mean = (max(y) - min(y)) / 2 + min(y)
            guess_phase = 0
            guess_amp = max(y) - guess_mean

            optimize_func = lambda x: x[0] * np.sin(x[1] * t + x[2]) + x[3] - y
            jacobian = lambda x: [
                np.sin(x[1] * t + x[2]),
                x[0] * t * np.cos(x[1] * t + x[2]),
                x[0] * np.cos(x[1] * t + x[2]),
                np.ones(t.size)
            ]
            gn = gauss_newton.gauss_newton(optimize_func, [guess_amp, ESTIMATED_FREQUENCY / 1000.0 * 2 * np.pi, guess_phase, guess_mean],
                                           jacobian, NUM_FIT_ITERATIONS)

            gn_amp, gn_freq, gn_phase, gn_mean = gn
            gn_freq = gn_freq / (2 * np.pi)
            # gn_amp = guess_amp
            # gn_freq = 50 / 1000
            # gn_phase = guess_phase
            # gn_mean = guess_mean

            gn_data = gn_amp * np.sin(gn_freq * 2 * np.pi * t + gn_phase) + gn_mean
            print('f={:.3f} A={:.3f} ϕ={:.3f} μ={:.3f}'.format(gn_freq, gn_amp, gn_phase, gn_mean))

            plt.plot(t, y)
            plt.plot(t, gn_data, '--')
    plt.show()

main()
