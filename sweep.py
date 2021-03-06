#!/usr/bin/env python
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This programm sweeps over a weight given in the command line. The output is
saved in a .txt file as CSV in the analsis direction. There is also a gnuplot
script which plots the data
"""
import json
import sys

import numpy as np
import matplotlib.pyplot as plt
import pyscm
import pynam.data as data
import pynam.network as netw
import pynnless as pynl

# Number of simulation steps
n = 100

# check simulator
if len(sys.argv) != 3:
    print("Usage: " + sys.argv[0] + " <SIMULATOR>" + " <weight>")
    sys.exit(1)

check = ("wCA", "wCH", "wCSigma", "wCTExt")
if (sys.argv[2] not in check):
    print("Usage: " + sys.argv[0] + " <SIMULATOR>" + " <weight>")
    sys.exit(1)
stri = sys.argv[2]
# Read in neuron data
with open("data/neuron_data.json", 'r') as outfile:
    dict = json.load(outfile)

data_params = dict["data_params"]
params = dict["neuron_params"]
delay = dict["delay"]
terminating_neurons = dict["terminating_neurons"]
flag = dict["Simple_Network"]

# Read in neuron weights, some still have to be set manually
with open("data/optimised_weights.json", 'r') as outfile:
    weights = json.load(outfile)

# Generate BiNAM
mat_in = data.generate(data_params["n_bits_in"], data_params["n_ones_in"],
                       data_params["n_samples"])
mat_out = data.generate(data_params["n_bits_out"], data_params["n_ones_out"],
                        data_params["n_samples"])
print "Data generated!"

# set up simulator
scm = pyscm.SpikeCounterModel(mat_in, mat_out)
sim = pynl.PyNNLessIsolated(sys.argv[1])

[I, I_norm, fp, fn, I_start, I_norm_start, fp_start, fn_start] = np.zeros(
    (8, n))
values = np.linspace(0.1, 30, n)

# Workaround for negative weights
if (stri == "wCSigma"):
    values = np.linspace(-1, 0.001, n)

# The actual sweep
for i in xrange(n):
    weights[stri] = values[i]
    net, input_indices, _, input_times = scm.build(params=params,
                                                   weights=weights,
                                                   delay=delay,
                                                   terminating_neurons=terminating_neurons,
                                                   flag=flag)
    res = sim.run(net)
    # In case the max operation in analysis throws an exception, which is the
    # case for unvalid runs caused by wrong weights, e.g. no spiking at all
    try:
        output_times, output_indices = netw.NetworkInstance.match_static(
            input_times, input_indices, res[0]["spikes"])

        analysis = netw.NetworkAnalysis(input_times=input_times,
                                        input_indices=input_indices,
                                        output_times=output_times,
                                        output_indices=output_indices,
                                        data_params=data_params,
                                        mat_in=mat_in, mat_out=mat_out)
        I[i], I_norm[i], fp[i], fn[i], I_start[i], I_norm_start[i], fp_start[i], \
        fn_start[i] = pyscm.scm_analysis(analysis, res[2]["spikes"], delay)
        if (fp[i] > data_params["n_samples"] * data_params["n_bits_out"] * 0.5):
            break

        # Assure that system doesn't terminate without auto-associative spiking
        times = np.zeros(len(res[0]["spikes"]))
        for l in xrange(len(res[0]["spikes"])):
            for j in res[0]["spikes"][l]:
                if (j < 199):
                    times[l] += 1
        if (np.amax(times) <= 2):
            I[i], I_norm[i], fp[i], fn[i], I_start[i], I_norm_start[i], \
            fp_start[i], fn_start[i] = 0, 0, 0, 0, 0, 0, 0, 0
    except:
        print "except"
        I[i], I_norm[i], fp[i], fn[i], I_start[i], I_norm_start[i], fp_start[i], \
        fn_start[i] = 0, 0, 0, 0, 0, 0, 0, 0
        print I[i]

# These values are the same for every run. This is a work around to the except case above
index = np.where(I_norm_start == 1)[0][0]
I_start_ = I_start[index]
I_norm_start_ = I_norm_start[index]
fp_start_ = fp_start[index]
fn_start_ = fn_start[index]

# Write the data to the respective file
with open("analysis/" + stri + "_sweep.txt", 'w') as outfile:
    outfile.write(
        "#weight,I, I_norm, fp ,fn ,I_start , I_norm_start, fp_start, fn_start\n")
    for i in xrange(n):
        outfile.write("%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f\n" % (
            values[i], I[i], I_norm[i], fp[i], fn[i], I_start_, I_norm_start_,
            fp_start_, fn_start_))
