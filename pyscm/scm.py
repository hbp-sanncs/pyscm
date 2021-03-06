# -*- coding: utf-8 -*-

#   PySCM -- Python Spike Counter Model
#   Copyright (C) 2016 Christoph Jenzen, Andreas Stöckel
#
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

import numpy as np
import pyscm
import pynam
import pynam.entropy as entropy
import pynam.network
import pynnless as pynl


class SpikeCounterModel:
    def __init__(self, mat_in, mat_out, _type=pynl.TYPE_IF_COND_EXP):
        # Copy the given reference to the input and output data vectors
        self.mat_in = mat_in
        self.mat_out = mat_out
        self._type = _type

        # Train the matrices CH and CA
        self.n_bits_in = mat_in.shape[1]
        self.n_bits_out = mat_out.shape[1]
        self.mat_CH = pynam.BiNAM().train_matrix(mat_in, mat_out)
        self.mat_CA = pynam.BiNAM().train_matrix(mat_out, mat_out)

    def build(self, weights, params={}, input_params={}, delay=0.1,
              terminating_neurons=1, flag=False):
        '''
        Builds the network of the SCM
        :param weights: dict of different weights in the SCM: wCH,wCA,wCSigma,
                wCTInh, wCTExt, wAbort
        :param params: neuron params
        :param input_params: pynam.network.InputParameters
        :param terminating_neurons: Number of terminating neurons, Workaround for
                some platforms for higher weights to really terminate
        :param flag: change between SCM (False) and a single neuron in the
                CS(igma) population
        '''
        net = pynl.Network()

        # Create the input spike trains
        trains, input_indices, input_split = pynam.network.NetworkBuilder.build_spike_trains(
            self.mat_in, 100,
            input_params=input_params)

        # Create the individual cell assemblies
        pop_C = pynl.Population(count=self.n_bits_out, _type=self._type,
                                params=params, record=[pynl.SIG_SPIKES])
        if (flag):
            pop_CS = pynl.Population(count=self.n_bits_out, _type=self._type,
                                     params=params, record=[pynl.SIG_SPIKES])
        else:
            pop_CS = pynl.Population(pop_C)
        pop_CT = pynl.Population(count=terminating_neurons, _type=self._type,
                                 params=params, record=[pynl.SIG_SPIKES])
        pop_source = pynl.Population(count=self.n_bits_in,
                                     _type=pynl.TYPE_SOURCE, params=map(
                lambda train: {"spike_times": train}, trains),
                                     record=[pynl.SIG_SPIKES])

        # Create the connections
        def connections_from_matrix(mat, pSrc, pTar, w):
            connections = []
            for i in xrange(mat.shape[0]):
                for j in xrange(mat.shape[1]):
                    if mat[i, j] != 0:
                        connections.append(((pSrc, i), (pTar, j), w, delay))
            return connections

        def connections_all_to_all(m, n, pSrc, pTar, w):
            connections = map(lambda _: [], xrange(m * n))
            for i in xrange(m):
                for j in xrange(n):
                    connections[i * n + j] = (((pSrc, i), (pTar, j), w, delay))
            return connections

        wCH = weights["wCH"]
        wCA = weights["wCA"]
        wCSigma = weights["wCSigma"]
        wCTExt = weights["wCTExt"]
        wCTInh = weights["wCTInh"]
        wAbort = weights["wAbort"]
        iC = 0
        iCS = 1
        iCT = 2
        iSource = 3
        if (flag):
            connections = (
                connections_from_matrix(self.mat_CH, iSource, iC, wCH) +
                connections_from_matrix(self.mat_CA, iC, iC, wCA) +
                connections_all_to_all(self.n_bits_in, 1, iSource, iCS, wCH) +
                connections_all_to_all(self.n_bits_out, 1, iC, iCS, wCA) +

                # Sigma connections
                connections_all_to_all(1, 1, iCS, iCS, wCSigma) +
                connections_all_to_all(1, self.n_bits_out, iCS, iC, wCSigma) +

                # Connections to CT
                connections_all_to_all(self.n_bits_out, terminating_neurons, iC,
                                       iCT, wCTExt) +
                connections_all_to_all(1, terminating_neurons, iCS, iCT,
                                       wCTInh) +

                # Connections from CT to all other populations
                connections_all_to_all(terminating_neurons, self.n_bits_out,
                                       iCT, iC, wAbort) +
                connections_all_to_all(terminating_neurons, 1, iCT, iCS,
                                       wAbort) +
                connections_all_to_all(terminating_neurons, terminating_neurons,
                                       iCT, iCT, wAbort)
            )
        else:
            connections = (
                connections_from_matrix(self.mat_CH, iSource, iC, wCH) +
                connections_from_matrix(self.mat_CH, iSource, iCS, wCH) +
                connections_from_matrix(self.mat_CA, iC, iCS, wCA) +
                connections_from_matrix(self.mat_CA, iC, iC, wCA) +

                # Sigma connections
                connections_all_to_all(self.n_bits_out, self.n_bits_out, iCS,
                                       iCS, wCSigma) +
                connections_all_to_all(self.n_bits_out, self.n_bits_out, iCS,
                                       iC, wCSigma) +

                # Connections to CT
                connections_all_to_all(self.n_bits_out, terminating_neurons, iC,
                                       iCT, wCTExt) +
                connections_all_to_all(self.n_bits_out, terminating_neurons,
                                       iCS, iCT, wCTInh) +

                # Connections from CT to all other populations
                connections_all_to_all(terminating_neurons, self.n_bits_out,
                                       iCT, iC, wAbort) +
                connections_all_to_all(terminating_neurons, self.n_bits_out,
                                       iCT, iCS, wAbort) +
                connections_all_to_all(terminating_neurons, terminating_neurons,
                                       iCT, iCT, wAbort)
            )

        return pynl.Network(populations=[pop_C, pop_CS, pop_CT, pop_source],
                            connections=connections), input_indices, input_split, trains


def calc_scm_output_matrix(netw, terminate_times, delay, flag=min):
    """
    Calculate the output matrix given at the time, where the termination neuron spikes
    :param netw: a NetworkAnalysis object
    :param terminate_times: The times, where the termination neuron spikes
    :param delay: delay of the neuron weights
    :param flag: either min for the BiNAM (Spikes at the beginning) or max for spikes at the end (SCM)
    :return: The SCM output matrix
    """
    times = netw["output_times"]
    kOut = netw["output_indices"]

    # Create the output matrix
    if hasattr(netw["mat_out"], "shape"):
        N, n = netw["mat_out"].shape
    else:
        N = netw["data_params"]["n_samples"]
        n = netw["data_params"]["n_bits_out"]
    res = np.zeros((N, n))

    # Calculation of the output matrix
    for k in xrange(N):
        time = []

        # Search for the first spike in each sample
        if (flag == min):
            for l in xrange(n):
                # Spike_time index for the first Spike in this sample for neuron l
                # If l did not spike in this sample, set to -1
                m = next((i for i in xrange(len(kOut[l])) if kOut[l][i] == k),
                         -1.0)
                if (m >= 0):
                    time.append(times[l][m])
            cal_time = np.amin(time) + delay
        # Search for the last spike in each sample


        if (flag == max):
            for l in xrange(n):
                # Spike_time index for the first Spike in this sample for neuron l
                # If l did not spike in this sample, set to -1
                m = next((i for i in xrange(len(kOut[l])) if kOut[l][i] == k),
                         -1.0)
                if (m >= 0):
                    # If l spiked, take the last spike belonging to that sample
                    m += kOut[l].count(k) - 1
                    time.append(times[l][m])
            cal_time = np.amax(time)
            # TODO get sure that it is terminated
        # cal_time is the stopping time for the search for spikes beloning to sample k

        # If neuron l spikes in a certain intervall, set matrix element to 1
        # TODO 0.35 is guessed, works in this example
        for l in xrange(n):
            for m in times[l]:
                if ((cal_time - 0.35 <= m) & (m <= cal_time)):
                    res[k, l] = 1.0

    return res


def scm_analysis(netw, terminate_times, delay=0.1, flag=False):
    """
    Anaylsis of the scm and compare to normal PyNAM (first spikes after input spike)
    :param netw: Should be of NetworkAnalysis type
    :param flag: Simple model flag
    :return: Information in the SCM, output-matrix and an errors object
    """

    # Calculate the SCM  information
    mat_out_res = calc_scm_output_matrix(netw, terminate_times, delay, max)
    N, n = mat_out_res.shape
    errs = entropy.calculate_errs(mat_out_res, netw["mat_out"])
    I = entropy.entropy_hetero(errs, n, netw["data_params"]["n_ones_out"])

    # Get the spike times of the source population
    tem, _, _ = pynam.network.NetworkInstance.flatten(netw["input_times"],
                                                      netw["input_indices"])
    start_times = np.unique(tem)
    for i in xrange(len(start_times)):
        start_times = start_times + 0.98 + delay * 2.5
    # calc_scm_output_matrix needs such an array
    start_times_ar = np.zeros((2, len(start_times)))
    start_times_ar[0] = start_times

    # Finally calculate the BiNAM information from the start
    mat_out_first = calc_scm_output_matrix(netw, start_times_ar, delay)
    errs_start = entropy.calculate_errs(mat_out_first, netw["mat_out"])
    I_start = entropy.entropy_hetero(errs_start, n,
                                     netw["data_params"]["n_ones_out"])

    # Calculate non-spiking information for Reference
    I_ref, mat_ref, errs_ref = netw.calculate_max_storage_capacity()
    # Noramlized information values
    I_norm = 0.0 if I_ref == 0.0 else I / float(I_ref)
    I_norm_start = 0.0 if I_ref == 0.0 else I_start / float(I_ref)

    # The number of False Positives and Negatives for both SCM and BiNAM
    fp = sum(map(lambda x: x["fp"], errs))
    fn = sum(map(lambda x: x["fn"], errs))
    fp_start = sum(map(lambda x: x["fp"], errs_start))
    fn_start = sum(map(lambda x: x["fn"], errs_start))

    if (flag):
        print "\t\t\t\tBiNAM \t\tSimple_Net"
    else:
        print "\t\t\t\tBiNAM \t\tSCM"
    print "Information:\t\t\t", format(I_start, '.2f'), "\t", format(I, '.2f')
    print "Normalized information:\t\t", format(I_norm_start,
                                                '.2f'), "\t\t", format(I_norm,
                                                                       '.2f')
    print "False positives:\t\t", format(fp_start, '.0f'), "\t\t", format(fp,
                                                                          '.0f')
    print "False negatives:\t\t", format(fn_start, '.0f'), "\t\t", format(fn,
                                                                          '.0f')
    return I, I_norm, fp, fn, I_start, I_norm_start, fp_start, fn_start
