#!/usr/bin/env python3

import numpy as np
from scipy.optimize import leastsq
import pylab as plt

N = 250 # number of data points
M = 2.5 # Number of periods

mean = 1.0
f = 51.0
amp = 3.0
phase = 0.1

truncate = False # True to truncate bottom half of the sine wave. This simulates a load that uses 1 side of the sine.

t = np.linspace(0, M * 1.0 / f, N)

data = amp * np.sin(f * 2*np.pi * t + phase) + mean

# Cut of half of the sine.
if truncate:
    for i in range(0, N):
       if (data[i] < mean):
           data[i] = mean

# Add noise
data = data + 0.1 * np.random.randn(N)

guess_mean = np.mean(data)
guess_phase = 0.0
guess_freq = 50.0
guess_amp = 1.0
#guess_amp = 3 * np.std(data) / (2**0.5) / (2**0.5)

# we'll use this to plot our first estimate. This might already be good enough for you
data_first_guess = guess_amp * np.sin(guess_freq * 2*np.pi * t + guess_phase) + guess_mean


################################################
# Using LSQ for frequency (iterative)
################################################

# Define the function to optimize, in this case, we want to minimize the difference
# between the actual data and our "guessed" parameters
optimize_func = lambda x: x[0] * np.sin(x[1] * 2*np.pi * t + x[2]) + x[3] - data
lsq = leastsq(optimize_func, [guess_amp, guess_freq, guess_phase, guess_mean], full_output=1)
lsq_amp, lsq_freq, lsq_phase, lsq_mean = lsq[0]

print("number of function calls:", lsq[2]['nfev'])
print("The function evaluated at the output:", lsq[2]['fvec'])
print("  Len:", len(lsq[2]['fvec']))

# recreate the fitted curve using the optimized parameters
#fine_t = np.arange(0, max(t), 0.1)
#data_fit = est_amp * np.sin(est_freq * fine_t + est_phase) + est_mean
data_lsq = lsq_amp * np.sin(lsq_freq * 2*np.pi * t + lsq_phase) + lsq_mean


################################################
# Using FFT for frequency
################################################

fft_freq_bins = np.fft.fftfreq(len(t), (t[1] - t[0])) # assume uniform spacing
print("fft freq bins:", fft_freq_bins)
fft = abs(np.fft.fft(data))
fft_freq = abs(fft_freq_bins[np.argmax(fft[1:]) + 1]) # excluding the zero frequency



# Define the function to optimize, in this case, we want to minimize the difference
# between the actual data and our "guessed" parameters
optimize_func = lambda x: x[0] * np.sin(fft_freq * 2*np.pi * t + x[1]) + x[2] - data
fft_amp, fft_phase, fft_mean = leastsq(optimize_func, [guess_amp, guess_phase, guess_mean])[0]

# recreate the fitted curve using the optimized parameters
data_fft = fft_amp * np.sin(fft_freq * 2*np.pi * t + fft_phase) + fft_mean



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

print("input: mean=", mean, " frequency=", f, " amplitude=", amp, " phase=", phase)
print("lsq:   mean=", lsq_mean, " frequency=", lsq_freq, " amplitude=", lsq_amp, " phase=", lsq_phase)
print("fft:   mean=", fft_mean, " frequency=", fft_freq, " amplitude=", fft_amp, " phase=", fft_phase)
print("num:   mean=", num_mean, " frequency=", num_freq, " amplitude=", num_amp, " phase=", num_phase)

plt.plot(t, data, '.')
plt.plot(t, data_first_guess, label='first guess')
#plt.plot(fine_t, data_fit, label='after fitting')
plt.plot(t, data_lsq, label='lsq')
plt.plot(t, data_fft, label='fft')
plt.plot(t, num_data, label='num')
plt.legend()
plt.show()