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
MIN_FREQ = 40
MAX_FREQ = 60

class algoName(Enum):
    guess = 0
    gn = 1
    lsq = 2
    bound = 3

def print_beta(prefix, beta):
    print(prefix, 'f={:.3f} A={:.3f} ϕ={:.3f} μ={:.3f}'.format(beta[1] / (2*np.pi), beta[0], beta[2], beta[3]))

def get_error(y, curve):
    err = (y - curve)
    return err.dot(err.transpose())

def get_curve(t, beta):
    amp, ang_freq, phase, mean = beta
    return amp * np.sin(ang_freq * t + phase) + mean

def fit_lsq(t, y, beta0, boundaries):
    optimize_func = lambda x: x[0] * np.sin(x[1] * t + x[2]) + x[3] - y
    lsq = least_squares(optimize_func,
                        beta0,
                        method='lm',
                        loss='linear')
    if (not lsq.success):
        print("lsq status:", lsq.message)
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
                                   jacobian, NUM_FIT_ITERATIONS)
    return gn

def fit_robust(t, y, beta0, boundaries):
    optimize_func = lambda x: x[0] * np.sin(x[1] * t + x[2]) + x[3] - y
    jacobian = lambda x: np.array([
        np.sin(x[1] * t + x[2]),
        x[0] * t * np.cos(x[1] * t + x[2]),
        x[0] * np.cos(x[1] * t + x[2]),
        np.ones(t.size)
    ]).transpose()

    # Method 'lm' (Levenberg–Marquardt) only accepts linear loss function.

    # x0 = [beta0[0], beta0[1] * 2 * np.pi, beta0[2], beta0[3]]
    # print_beta('robust init', x0)
    # for i in range(0, 30):
    #     robust = least_squares(optimize_func,
    #                            x0,
    #                            method='trf',
    #                            loss='soft_l1',
    #                            jac=jacobian,
    #                            bounds=([beta0[0] * 0.5, MIN_FREQ * 2 * np.pi, -1*np.pi, beta0[3] * 0.5],
    #                                    [beta0[0] * 1.5, MAX_FREQ * 2 * np.pi,  1*np.pi, beta0[3] * 1.5]),
    #                            max_nfev=2,
    #                            verbose=2)
    #     x0 = robust.x
    #     print_beta('robust', x0)
    #     curve = get_curve(t, [x0[0], x0[1] / (2 * np.pi), x0[2], x0[3]])
    #     err = get_error(y, curve)
    #     print("err=", err)
    # amp, freq, phase, mean = x0

    robust = least_squares(optimize_func,
                           beta0,
                           method='trf',
                           # method='dogbox',
                           # loss='soft_l1',
                           loss='linear',
                           bounds=boundaries,
                           verbose=0)

    if (not robust.success):
        print("robust status:", robust.message)
    return robust.x

def main():
    fileNames = sys.argv[1:]

    print(fileNames)

    betas = {}
    errors = {}
    algo_labels = [algoName.guess.name, algoName.gn.name, algoName.lsq.name, algoName.bound.name]
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
            print("i", i)

            t = np.array(allTimestamps[i][0:NUM_SAMPLES_FOR_FIT])
            t /= 1000 # Change to seconds.
            t_start = t[0]
            t = t - t[0] # Time starting at 0
            y = np.array(allSamples[i][0:NUM_SAMPLES_FOR_FIT])

            guess_mean = (max(y) - min(y)) / 2 + min(y)
            guess_phase = 0
            guess_amp = max(y) - guess_mean
            guess_angular_frequency = 2 * np.pi * ESTIMATED_FREQUENCY

            # Determine phase by first zero crossing
            below = y[0] < guess_mean
            # print("below=", below)
            for k in range(1, len(y)):
                if (below and y[k] > guess_mean):
                    # Upward crossing found
                    # Phase = - dt / T * 2*pi
                    dt = t[k]
                    guess_phase = -dt / (1 / ESTIMATED_FREQUENCY) * 2 * np.pi
                    # print("Upward crossing at k=", k, " periods=", dt / (1 / ESTIMATED_FREQUENCY))
                    # print("phase=", guess_phase / np.pi, "pi")
                    break
                if (not below and y[k] < guess_mean):
                    # Downward crossing found
                    # Should be at t = T * pi
                    # Phase = pi - dt / T * 2pi
                    dt = t[k]
                    guess_phase = np.pi - dt / (1 / ESTIMATED_FREQUENCY) * 2 * np.pi
                    # print("Downward crossing at k=", k, " periods=", dt / (1 / ESTIMATED_FREQUENCY))
                    # print("phase=", guess_phase / np.pi, "pi")
                    break
            # Make sure phase is in range [-pi, pi]
            while (guess_phase > np.pi):
                guess_phase -= 2 * np.pi
            while (guess_phase < -np.pi):
                guess_phase += 2 * np.pi


            boundaries = ([guess_amp * 0.5, 2 * np.pi * MIN_FREQ, -1 * np.pi, guess_mean * 0.5],
                          [guess_amp * 1.5, 2 * np.pi * MAX_FREQ,  1 * np.pi, guess_mean * 1.5])

            beta0 = [guess_amp, guess_angular_frequency, guess_phase, guess_mean]
            guess_curve = get_curve(t, beta0)

            gn_beta = fit_gn(t, y, beta0, boundaries)
            gn_curve = get_curve(t, gn_beta)

            lsq_beta = fit_lsq(t, y, beta0, boundaries)
            lsq_curve = get_curve(t, lsq_beta)

            robust_beta = fit_robust(t, y, beta0, boundaries)
            robust_curve = get_curve(t, robust_beta)

            print_beta(algoName.guess.name, beta0)
            print_beta(algoName.gn.name, gn_beta)
            print_beta(algoName.lsq.name, lsq_beta)
            print_beta(algoName.bound.name, robust_beta)

            betas[algoName.guess.name].append(beta0)
            betas[algoName.gn.name].append(gn_beta)
            betas[algoName.lsq.name].append(lsq_beta)
            betas[algoName.bound.name].append(robust_beta)

            errors[algoName.guess.name].append(get_error(y, guess_curve))
            errors[algoName.gn.name].append(get_error(y, gn_curve))
            errors[algoName.lsq.name].append(get_error(y, lsq_curve))
            errors[algoName.bound.name].append(get_error(y, robust_curve))

            # Plot
            plt.figure(0)

            # Remove gaps between curves, for a better plot.
            t += prevLastTime
            prevLastTime = t[-1]

            plt.plot(t, y)
            if i == 0:
                plt.plot(t, guess_curve, ',', label=algoName.guess.name)
                plt.plot(t, gn_curve, '--', label=algoName.gn.name)
                plt.plot(t, lsq_curve, ':', label=algoName.lsq.name)
                plt.plot(t, robust_curve, '-.', label=algoName.bound.name)
            else:
                plt.plot(t, guess_curve, ',')
                plt.plot(t, gn_curve, '--')
                plt.plot(t, lsq_curve, ':')
                plt.plot(t, robust_curve, '-.')

            # if i >= 25:
            #     break
    plt.ylim([min(y) * 0.9, max(y) * 1.1])
    plt.legend()

    # Just use last boundaries for plotting limits.
    # Convert to frequency though.
    boundaries[0][1] /= 2 * np.pi
    boundaries[1][1] /= 2 * np.pi

    # Use error of guess as error plot bound
    maxPlotError = max(errors[algoName.guess.name])

    line_styles = ['-o', '-x', '-+', '-1']
    fig, axs = plt.subplots(5, sharex=True)
    for i in range(0, NUM_ALGOS):
        plotBetas = np.array(betas[algo_labels[i]]).transpose()
        for j in range(0, 4):
            if (j == 1):
                plotBetas[j] /= 2 * np.pi # Angular frequency to frequency.
            axs[j].plot(plotBetas[j], line_styles[i], label=algo_labels[i])
            axs[j].legend()
            axs[j].set_ylim([boundaries[0][j], boundaries[1][j]])

        axs[4].plot(errors[algo_labels[i]], line_styles[i], label=algo_labels[i])
        axs[4].legend()
        axs[4].set_ylim([0, maxPlotError])

        axs[0].set_ylabel('Amplitude')
        axs[1].set_ylabel('Frequency')
        axs[2].set_ylabel('Phase')
        axs[3].set_ylabel('Mean')
        axs[4].set_ylabel('Error')

    plt.show()

main()
