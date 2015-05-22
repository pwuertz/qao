import numpy as np
from scipy.signal import fftconvolve

def g2(meas, startRunIndex = None, stopRunIndex = None, verbose = False, mode="full"):
    """
    Calculate the g2 correlation function for a list of N-dimensional input data.
    This method can be used to calculate the temporal (1-dim) and spatial (n-dim)
    g2 correlation function. Under the hood the fftconvolve from scipy is used to
    calculate the n-dim autocorrelation function.

    .. math::

        g^{(2)} = \frac{\bigl<\mathrmrm{autocorr}(I(\vec{x}))\bigr>_\mathrm{runs}}{\mathrm{autocorr}(\bigl<I(\vec{x}\bigr>_\mathrm{runs})} \frac{1}{1 + \frac{\sigma^2 - N}{N^2}}

    :param meas: (list) list of n-dim ndarrays containing the binned data.
    :param startRunIndex: (int) first list entry to consider for g2 calculation.
    :param stopRunIndex: (int) last list entry to consider for g2 calculation.
    :param verbose: (bool) toggle progress output to stdout.
    :returns: (ndarray) n-dim g2 correlation function.
    """
    shape = meas.shape
    if startRunIndex != None and stopRunIndex != None:
        shape[0] = stopRunIndex-startRunIndex
    else:
        startRunIndex = 0
        stopRunIndex = shape[0]
        
    # calculate the mean of individual autocorrelations
    if mode == "full":
        autocorr_shape = tuple([ 2*dim-1 for dim in shape[1:]])
    else:
        autocorr_shape = meas.shape[1:]
    autocorr_mean = np.zeros(autocorr_shape)
    for i in range(meas.shape[0]):
        if verbose: print "autocorrelating %d/%d" % (i, shape[0])
        autocorr_mean += fftconvolve(meas[i], meas[i][[slice(None, None, -1)]*(len(meas.shape)-1)], mode=mode)
    autocorr_mean *= 1.0 / shape[0]

    # calculate autocorrelation for mean of data
    autocorr_all_mean = fftconvolve(meas.mean(axis=0), meas.mean(axis=0)[[slice(None, None, -1)]*(len(meas.shape)-1)], mode=mode)
    
    # calculate g2 contribution from total atom number fluctuations
    N_total = meas.sum(axis=tuple(range(1,len(shape))))
    
    n = N_total.mean()
    s = N_total.std()
    
    g2_offset = 1 + (s**2 - n)/n**2
    
    # return normalized g2 by mean autocorrelation and g2_offset
    return autocorr_mean / autocorr_all_mean / g2_offset
    
def g2_timeDiffs(timeDiffArray, bins):
    """
    Alternative method to calculate the temporal (1-dim) g2 function.
    This approach calculates all occuring time differences in the input
    signal and creates a binned histogram over those. Normalizing this
    to the average number of counts per histogram bin size squared and to
    the number of possibilities for each time difference.

    .. math::

        g^{(2)} = \frac{\bigl<\mathrmrm{hist}(\Delta t)\bigr>_\mathrm{runs}}{\bigl<N_\mathrm{counts}/N_\mathrm{bins}\bigr>_\mathrm{runs}^2} \frac{1}{1 - \frac{\tau}{\tau_\mathrm{max}}}

    :param timeDiffArray: (list) list of n-dim ndarrays containing the binned data.
    :param bins: (ndarray) bin edges.
    :returns: (ndarray tau, ndarray g2) 1-dim g2 correlation function.
    """
    meanCountsPerBin = 0
    difflist = []
    for timeDiffs in timeDiffArray:
        meanCountsPerBin += len(timeDiffs)/float(len(bins))
        difflist += [timeDiffs[i+1:]-timeDiffs[i] for i in xrange(0,len(timeDiffs)-1)]
    
    difflist = np.hstack(difflist)
    h, edges = np.histogram(difflist,bins)
    runs = float(len(timeDiffArray))
    h = h/runs
    meanCountsPerBin = meanCountsPerBin/runs
    
    tau = edges[:-1]
    g2 = h/meanCountsPerBin**2/(len(bins)*(1-tau/edges[-1]))
    
    return tau, g2
