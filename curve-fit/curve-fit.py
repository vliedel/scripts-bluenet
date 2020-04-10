#!/usr/bin/env python3

import numpy as np
from scipy.optimize import *
#import pylab as plt

from matplotlib import rcParams
rcParams['font.family'] = 'monospace'
import matplotlib.pyplot as plt

##########
# Options
##########

truncate = False # True to truncate bottom half of the sine wave. This simulates a load that uses 1 side of the sine.
outliers = True # True to add outliers to the data.

K = 100 # number of data points per period
M = 4.5 # Number of periods of data

mean = 1.0
f = 51.0
amp = 3.0
phase = 0.1


guess_phase = 0.0
guess_freq = 50.0
guess_amp = 1.0

####################
# Prepare test data
####################

N = int(K * M) # number of data points

t = np.linspace(0, M * 1.0 / f, N)

data = amp * np.sin(f * 2*np.pi * t + phase) + mean
truth_data = data

# Cut of half of the sine.
if truncate:
    for i in range(0, N):
       if (data[i] < mean):
           data[i] = mean

# Add noise
noise_amp = amp / 50
noise = noise_amp * np.random.randn(N)

if outliers:
    outlier_amp = amp
    numOutliers = int(N / 20)
    #numOutliers = 1
    indices = np.random.randint(0, t.size, numOutliers)
    #noise[indices] = outlier_amp * np.random.randn(numOutliers)
    noise[indices] = outlier_amp * np.abs(np.random.randn(numOutliers))

data = data + noise

# Initial guess
guess_mean = np.mean(data)
guess_data = guess_amp * np.sin(guess_freq * 2 * np.pi * t + guess_phase) + guess_mean



################################################
# Using LSQ for frequency (iterative)
################################################

optimize_func = lambda x: x[0] * np.sin(x[1] * 2*np.pi * t + x[2]) + x[3] - data
lsq = least_squares(optimize_func, [guess_amp, guess_freq, guess_phase, guess_mean], method='lm', loss='linear')

lsq_amp, lsq_freq, lsq_phase, lsq_mean = lsq.x

print("Number of function evaluations:", lsq.nfev)
print("Number of Jacobian evaluations:", lsq.njev)

lsq_data = lsq_amp * np.sin(lsq_freq * 2 * np.pi * t + lsq_phase) + lsq_mean



################################################
# Using robust LSQ for frequency (iterative)
################################################

optimize_func = lambda x: x[0] * np.sin(x[1] * 2*np.pi * t + x[2]) + x[3] - data
# Method 'lm' (Levenberg–Marquardt) only accepts linear loss function.
robust = least_squares(optimize_func, [guess_amp, guess_freq, guess_phase, guess_mean], method='trf', loss='soft_l1')
robust_amp, robust_freq, robust_phase, robust_mean = robust.x

print("Number of function evaluations:", robust.nfev)
print("Number of Jacobian evaluations:", robust.njev)

robust_data = robust_amp * np.sin(robust_freq * 2*np.pi * t + robust_phase) + robust_mean



################################################
# Using FFT for frequency
################################################

fft_freq_bins = np.fft.fftfreq(len(t), (t[1] - t[0])) # assume uniform spacing
print("fft freq bins:", fft_freq_bins)
fft = abs(np.fft.fft(data))
fft_freq = abs(fft_freq_bins[np.argmax(fft[1:]) + 1]) # excluding the zero frequency

optimize_func = lambda x: x[0] * np.sin(fft_freq * 2*np.pi * t + x[1]) + x[2] - data
fft_amp, fft_phase, fft_mean = leastsq(optimize_func, [guess_amp, guess_phase, guess_mean])[0]

fft_data = fft_amp * np.sin(fft_freq * 2 * np.pi * t + fft_phase) + fft_mean



#############################################
# Given frequency, calculate amplitude, mean, and phase.
# Use linear regression: https://math.stackexchange.com/questions/902166/fit-sine-wave-to-data
#
# Expand with mean: y(t) = A sin(Ω*t) * cos(ϕ) + A cos(Ω*t) * sin(ϕ) + mean
# y(t) = [1, w(t), z(t)] * [mean; A1; A2]
#
# Find phi:
# A1 = A * cos(ϕ),   A2 = A * sin(ϕ)
# A / cos(ϕ) = A1,   A = A2 / sin(ϕ)
# A1 / cos(ϕ) = A2 / sin(ϕ)
# sin(ϕ) / cos(ϕ) = A2 / A1
# tan(ϕ) = A2 / A1
# ϕ = arctan(A2 / A1)
#
#############################################

num_freq = f
#num_freq = lsq_freq

Y = data
X = np.array([np.ones(len(t)),
              np.sin(num_freq * 2*np.pi * t),
              np.cos(num_freq * 2*np.pi * t)
              ]).transpose()
print("X:", X.shape, " Y:", Y.shape)
Xt = X.transpose()
print("Xt dot X:", (Xt.dot(X)).shape)
B = np.linalg.inv(Xt.dot(X)).dot(Xt).dot(Y)
print("B:", B)

num_phase = np.arctan(B[2] / B[1])
num_amp = B[1] / np.cos(num_phase)
num_mean = B[0]

num_data = num_amp * np.sin(num_freq * 2*np.pi * t + num_phase) + num_mean




#############################################
# Show results
#############################################

print("input:   mean=", mean, " frequency=", f, " amplitude=", amp, " phase=", phase)
print("lsq:     mean=", lsq_mean, " frequency=", lsq_freq, " amplitude=", lsq_amp, " phase=", lsq_phase)
print("robust:  mean=", robust_mean, " frequency=", robust_freq, " amplitude=", robust_amp, " phase=", robust_phase)
print("fft:     mean=", fft_mean, " frequency=", fft_freq, " amplitude=", fft_amp, " phase=", fft_phase)
print("num:     mean=", num_mean, " frequency=", num_freq, " amplitude=", num_amp, " phase=", num_phase)

plt.plot(t, truth_data, '-',  label='truth       f={:.3f} A={:.3f} ϕ={:.3f} μ={:.3f}'.format(f, amp, phase, mean))
plt.plot(t, data,       '.')
plt.plot(t, guess_data, '-',  label='first guess f={:.3f} A={:.3f} ϕ={:.3f} μ={:.3f}'.format(guess_freq, guess_amp, guess_phase, guess_mean))
plt.plot(t, lsq_data,   '-',  label='lsq         f={:.3f} A={:.3f} ϕ={:.3f} μ={:.3f}'.format(lsq_freq, lsq_amp, lsq_phase, lsq_mean))
plt.plot(t, robust_data,':',  label='robust lsq  f={:.3f} A={:.3f} ϕ={:.3f} μ={:.3f}'.format(robust_freq, robust_amp, robust_phase, robust_mean))
plt.plot(t, fft_data,   '-',  label='fft         f={:.3f} A={:.3f} ϕ={:.3f} μ={:.3f}'.format(fft_freq, fft_amp, fft_phase, fft_mean))
plt.plot(t, num_data,   '--', label='given freq  f={:.3f} A={:.3f} ϕ={:.3f} μ={:.3f}'.format(num_freq, num_amp, num_phase, num_mean))
plt.legend(prop={})
plt.show()