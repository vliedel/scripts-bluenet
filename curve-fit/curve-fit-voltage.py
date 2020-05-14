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

# Limit number of curves, too many will take too long, and make the plot slow anyway.
MAX_CURVES_TO_FIT = 5000

PLOT_CURVES = False

# Whether to limit the y axis of the results (amplitude, frequency, phase, mean, error).
PLOT_LIMIT_Y_RESULTS = False

# Whether to plot the guess as well.
PLOT_GUESS = False

NUM_SAMPLES_FOR_FIT = 300
ESTIMATED_FREQUENCY = 50
MIN_FREQ = 40
MAX_FREQ = 60

NUM_FIT_ITERATIONS_GN = 10

class algoName(Enum):
    guess = 0
    gn = 1
    lm = 2
    bound = 3

def print_beta(prefix, beta):
    print(prefix, 'f={:.3f} A={:.3f} ϕ={:.3f} μ={:.3f}'.format(beta[1] / (2*np.pi), beta[0], beta[2], beta[3]))

def get_error(y, curve):
    err = (y - curve)
    return err.dot(err.transpose())

def get_curve(t, beta):
    amp, ang_freq, phase, mean = beta
    return amp * np.sin(ang_freq * t + phase) + mean

def get_phase_estimate(t, y, y_mean):
    # Determine phase by first zero crossing
    below = y[0] < y_mean
#    print("below=", below)
    guess_phase = 0.0
    for k in range(1, len(y)):
        if (below and y[k] > y_mean):
            # Upward crossing found
            # Phase = - t / T * 2*pi
            guess_phase = -t[k] / (1 / ESTIMATED_FREQUENCY) * 2 * np.pi
#            print("Upward crossing at k=", k, " periods=", t[k] / (1 / ESTIMATED_FREQUENCY))
#            print("phase=", guess_phase / np.pi, "pi")
            break
        if (not below and y[k] < y_mean):
            # Downward crossing found
            # Should be at t = T * pi
            # Phase = pi - t / T * 2pi
            guess_phase = np.pi - t[k] / (1 / ESTIMATED_FREQUENCY) * 2 * np.pi
#            print("Downward crossing at k=", k, " periods=", t[k] / (1 / ESTIMATED_FREQUENCY))
#            print("phase=", guess_phase / np.pi, "pi")
            break
    # Make sure phase is in range [-pi, pi]
    while (guess_phase > np.pi):
        guess_phase -= 2 * np.pi
    while (guess_phase < -np.pi):
        guess_phase += 2 * np.pi
    return guess_phase

def fit_lm(t, y, beta0, boundaries):
    optimize_func = lambda x: x[0] * np.sin(x[1] * t + x[2]) + x[3] - y
    lsq = least_squares(optimize_func,
                        beta0,
                        method='lm',
                        loss='linear')
    if (not lsq.success):
        print("lm status:", lsq.message)
    return lsq.x

def fit_gn(t, y, beta0, boundaries):
    optimize_func = lambda x: x[0] * np.sin(x[1] * t + x[2]) + x[3] - y
    jacobian = lambda x: [
        np.sin(x[1] * t + x[2]),
        x[0] * t * np.cos(x[1] * t + x[2]),
        x[0] * np.cos(x[1] * t + x[2]),
        np.ones(t.size)
    ]
    gn = gauss_newton.gauss_newton(optimize_func,
                                   beta0,
                                   jacobian, NUM_FIT_ITERATIONS_GN)
    return gn

def fit_bound(t, y, beta0, boundaries):
    optimize_func = lambda x: x[0] * np.sin(x[1] * t + x[2]) + x[3] - y
    jacobian = lambda x: np.array([
        np.sin(x[1] * t + x[2]),
        x[0] * t * np.cos(x[1] * t + x[2]),
        x[0] * np.cos(x[1] * t + x[2]),
        np.ones(t.size)
    ]).transpose()

    lsq = least_squares(optimize_func,
                           beta0,
                           method='trf',
                           # method='dogbox',
                           # loss='soft_l1',
                           loss='linear',
                           bounds=boundaries,
                           verbose=0)

    if (not lsq.success):
        print("bound status:", lsq.message)
    return lsq.x

def main():
    fileNames = sys.argv[1:]

    print(fileNames)

    betas = {}
    errors = {}
    algo_labels = [algoName.guess.name, algoName.gn.name, algoName.lm.name, algoName.bound.name]
    NUM_ALGOS = len(algo_labels)
    for i in range(0, NUM_ALGOS):
        betas[algo_labels[i]] = []
        errors[algo_labels[i]] = []


    for fileName in fileNames:
        allTimestamps, allSamples = parse_recorded_voltage.parse(fileName)

        prevLastTime = 0
        numCurves = 0

        for i in range(0, len(allTimestamps)):
            if (len(allTimestamps[i]) < NUM_SAMPLES_FOR_FIT):
                continue
            print("i", i)

            t = np.array(allTimestamps[i][0:NUM_SAMPLES_FOR_FIT])

            # Change to seconds.
            t /= 1000

            # Let time start at 0, else we run into some numerical issues,
            # probably cos(large_number) doesn't work too well?
            t = t - t[0]
            y = np.array(allSamples[i][0:NUM_SAMPLES_FOR_FIT])

            guess_mean = (max(y) - min(y)) / 2 + min(y)
            guess_amp = max(y) - guess_mean
            guess_angular_frequency = 2 * np.pi * ESTIMATED_FREQUENCY
            guess_phase = get_phase_estimate(t, y, guess_mean)

            boundaries = ([guess_amp * 0.5, 2 * np.pi * MIN_FREQ, -1 * np.pi, guess_mean * 0.5],
                          [guess_amp * 1.5, 2 * np.pi * MAX_FREQ,  1 * np.pi, guess_mean * 1.5])

            beta0 = [guess_amp, guess_angular_frequency, guess_phase, guess_mean]
            guess_curve = get_curve(t, beta0)

            gn_beta = fit_gn(t, y, beta0, boundaries)
            gn_curve = get_curve(t, gn_beta)

            lm_beta = fit_lm(t, y, beta0, boundaries)
            lm_curve = get_curve(t, lm_beta)

            bound_beta = fit_bound(t, y, beta0, boundaries)
            bound_curve = get_curve(t, bound_beta)

            print_beta(algoName.guess.name, beta0)
            print_beta(algoName.gn.name, gn_beta)
            print_beta(algoName.lm.name, lm_beta)
            print_beta(algoName.bound.name, bound_beta)

            betas[algoName.guess.name].append(beta0)
            betas[algoName.gn.name].append(gn_beta)
            betas[algoName.lm.name].append(lm_beta)
            betas[algoName.bound.name].append(bound_beta)

            errors[algoName.guess.name].append(get_error(y, guess_curve))
            errors[algoName.gn.name].append(get_error(y, gn_curve))
            errors[algoName.lm.name].append(get_error(y, lm_curve))
            errors[algoName.bound.name].append(get_error(y, bound_curve))

            # Plot curves
            if PLOT_CURVES:
                plt.figure(0)

                # Plot all curves after each other.
                t += prevLastTime
                prevLastTime = t[-1]

                plt.plot(t, y, '-o')
                if i == 0:
                    plt.plot(t, guess_curve, ',', label=algoName.guess.name)
                    plt.plot(t, gn_curve, '--', label=algoName.gn.name)
                    plt.plot(t, lm_curve, ':', label=algoName.lm.name)
                    plt.plot(t, bound_curve, '-.', label=algoName.bound.name)
                else:
                    plt.plot(t, guess_curve, ',')
                    plt.plot(t, gn_curve, '--')
                    plt.plot(t, lm_curve, ':')
                    plt.plot(t, bound_curve, '-.')

            numCurves += 1
            if numCurves >= MAX_CURVES_TO_FIT:
                break

    if PLOT_CURVES:
        plt.ylim([min(y) * 0.9, max(y) * 1.1])
        plt.legend()

    # Just use last boundaries for plotting limits.
    # Convert to frequency though.
    boundaries[0][1] /= 2 * np.pi
    boundaries[1][1] /= 2 * np.pi

    # Use error of guess as error plot bound
    maxPlotError = max(errors[algoName.guess.name])

    if PLOT_LIMIT_Y_RESULTS:
        line_styles = ['-o', '-x', '-+', '-1']
    else:
        line_styles = ['.', 'x', '+', '1']

    fig, axs = plt.subplots(5, sharex=True)
    for i in range(0, NUM_ALGOS):
        if ((not PLOT_GUESS) and (algo_labels[i] is algoName.guess.name)):
            continue

        plotBetas = np.array(betas[algo_labels[i]]).transpose()
        for j in range(0, 4):
            if (j == 1):
                plotBetas[j] /= 2 * np.pi # Angular frequency to frequency.
            axs[j].plot(plotBetas[j], line_styles[i], label=algo_labels[i])
            axs[j].legend()
            if PLOT_LIMIT_Y_RESULTS:
                axs[j].set_ylim([boundaries[0][j], boundaries[1][j]])

        axs[4].plot(errors[algo_labels[i]], line_styles[i], label=algo_labels[i])

    axs[4].legend()
    if PLOT_LIMIT_Y_RESULTS:
        axs[4].set_ylim([0, maxPlotError])

    axs[0].set_ylabel('Amplitude')
    axs[1].set_ylabel('Frequency')
    axs[2].set_ylabel('Phase')
    axs[3].set_ylabel('Mean')
    axs[4].set_ylabel('Error')

    plt.show()

main()
