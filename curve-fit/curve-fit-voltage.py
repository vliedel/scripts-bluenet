#!/usr/bin/python3

"""
Use recorded data as input, and fit a curve to that.

For json: recorded data with record-voltage.py
For txt of log: recorded UART logs.
"""

import sys
from enum import Enum

sys.path.append('../record')
import parse_recorded_voltage

import numpy as np
import matplotlib.pyplot as plt

from scipy.optimize import *
import gauss_newton

NUM_SAMPLES_FOR_FIT = 300
NUM_FIT_ITERATIONS = 10
ESTIMATED_FREQUENCY = 50

class algoName(Enum):
    gn = 0
    lsq = 1
    robust = 2

def print_beta(prefix, beta):
    print(prefix, 'f={:.3f} A={:.3f} ϕ={:.3f} μ={:.3f}'.format(beta[1], beta[0], beta[2], beta[3]))

def get_error(y, curve):
    err = (y - curve)
    return err.dot(err.transpose())

def get_curve(t, beta):
    amp, freq, phase, mean = beta
    return amp * np.sin(freq * 2 * np.pi * t + phase) + mean

def fit_lsq(t, y, beta0):
    optimize_func = lambda x: x[0] * np.sin(x[1] * t + x[2]) + x[3] - y
    lsq = least_squares(optimize_func,
                        [beta0[0], beta0[1] * 2 * np.pi, beta0[2], beta0[3]],
                        method='lm',
                        loss='linear')
    amp, freq, phase, mean = lsq.x
    freq = freq / (2 * np.pi)
    return [amp, freq, phase, mean]

def fit_gn(t, y, beta0):
    optimize_func = lambda x: x[0] * np.sin(x[1] * t + x[2]) + x[3] - y
    jacobian = lambda x: [
        np.sin(x[1] * t + x[2]),
        x[0] * t * np.cos(x[1] * t + x[2]),
        x[0] * np.cos(x[1] * t + x[2]),
        np.ones(t.size)
    ]
    gn = gauss_newton.gauss_newton(optimize_func,
                                   [beta0[0], beta0[1] * 2 * np.pi, beta0[2], beta0[3]],
                                   jacobian, NUM_FIT_ITERATIONS)

    amp, freq, phase, mean = gn
    freq = freq / (2 * np.pi)
    return [amp, freq, phase, mean]

def fit_robust(t, y, beta0):
    optimize_func = lambda x: x[0] * np.sin(x[1] * t + x[2]) + x[3] - y
    # Method 'lm' (Levenberg–Marquardt) only accepts linear loss function.
    robust = least_squares(optimize_func,
                           [beta0[0], beta0[1] * 2 * np.pi, beta0[2], beta0[3]],
                           method='trf',
                           loss='soft_l1')
    amp, freq, phase, mean = robust.x
    freq = freq / (2 * np.pi)
    return [amp, freq, phase, mean]

def main():
    fileNames = sys.argv[1:]

    print(fileNames)

    betas = {}
    errors = {}
    algo_labels = [algoName.gn.name, algoName.lsq.name, algoName.robust.name]
    NUM_ALGOS = len(algo_labels)
    for i in range(0, NUM_ALGOS):
        betas[algo_labels[i]] = []
        errors[algo_labels[i]] = []


    plt.figure(0)

    for fileName in fileNames:
        allTimestamps, allSamples = parse_recorded_voltage.parse(fileName)

        prevLastTime = 0

        for i in range(0, len(allTimestamps)):
            if (len(allTimestamps[i]) < NUM_SAMPLES_FOR_FIT):
                continue

            t = np.array(allTimestamps[i][0:NUM_SAMPLES_FOR_FIT])
            t /= 1000 # Change to seconds.
            y = np.array(allSamples[i][0:NUM_SAMPLES_FOR_FIT])

            guess_mean = (max(y) - min(y)) / 2 + min(y)
            guess_phase = 0
            guess_amp = max(y) - guess_mean
            beta0 = [guess_amp, ESTIMATED_FREQUENCY, guess_phase, guess_mean]

            gn_beta = fit_gn(t, y, beta0)
            gn_curve = get_curve(t, gn_beta)

            lsq_beta = fit_lsq(t, y, beta0)
            lsq_curve = get_curve(t, lsq_beta)

            robust_beta = fit_robust(t, y, beta0)
            robust_curve = get_curve(t, robust_beta)

            # print_beta(algoName.gn.name, gn_beta)
            # print_beta(algoName.lsq.name, lsq_beta)
            # print_beta(algoName.robust.name, robust_beta)

            betas[algoName.gn.name].append(gn_beta)
            betas[algoName.lsq.name].append(lsq_beta)
            betas[algoName.robust.name].append(robust_beta)

            errors[algoName.gn.name].append(get_error(y, gn_curve))
            errors[algoName.lsq.name].append(get_error(y, lsq_curve))
            errors[algoName.robust.name].append(get_error(y, robust_curve))

            # Plot
            plt.figure(0)

            # Remove gaps between curves, for a better plot.
            t -= t[0] - prevLastTime
            prevLastTime = t[-1]

            plt.plot(t, y)
            if i == 0:
                plt.plot(t, gn_curve, '--', label=algoName.gn.name)
                plt.plot(t, lsq_curve, ':', label=algoName.lsq.name)
                plt.plot(t, robust_curve, '-.', label=algoName.robust.name)
            else:
                plt.plot(t, gn_curve, '--')
                plt.plot(t, lsq_curve, ':')
                plt.plot(t, robust_curve, '-.')

            if i > 800:
                break
    plt.legend()

    fig, axs = plt.subplots(5, sharex=True)
    for i in range(0, NUM_ALGOS):
        plotBetas = np.array(betas[algo_labels[i]]).transpose()
        for j in range(0, 4):
            axs[j].plot(plotBetas[j], '-o', label=algo_labels[i])
            axs[j].legend()
        axs[4].plot(errors[algo_labels[i]], '-o', label=algo_labels[i])
        axs[4].legend()

        axs[0].set_ylabel('Amplitude')
        axs[1].set_ylabel('Frequency')
        axs[2].set_ylabel('Phase')
        axs[3].set_ylabel('Mean')
        axs[4].set_ylabel('Error')

    plt.show()

main()
