"""
Deconvolve
---------

Algorithms for the deconvolution of ion signals and images.

The measured signals are affected by multiply charges. As the point spread
function of this effect is known (ion time of flight spectrum), an estimate
of the original signal can be calculated by deconvolution. This module provides
the necessary implementations.
"""

import numpy as np
from scipy.special import erf

def ion_tof_spectrum(dwell_time, n):
    """Calculate a pixel based spectrum based on the multipeak fit parameters
    of the ion time of flight measurement.
    
    :param dwell_time: (float) Dwell time of the pixels in micrometers.
    :param n: (int) Length of the spectrum in pixels.
    :returns: (ndarray) Normalized time of flight spectrum for given parameters.
    """
    
    gauss_pars = [[17.31395979720519, 63112.69760492675, 0.03123937437419509],
             [12.290841184555568, 6701.023533805622, 0.040793741078493824],
             [10.060823913081139, 7150.302486228399, 0.04562454121523191],
             [8.727893992574595, 2282.387336822463, 0.0470714790645937],
             [7.829032989499102, 697.6137824761323, 0.04166911964137886]]

    # gauss integral
    def gaussint(t1, t2, peaks):
        s = np.zeros_like(t1)
        sqrt2 = 2.**.5
        for t0, amp, sig in peaks:
            int_t2 = erf( (t2-t0) / (sqrt2*sig) )
            int_t1 = erf( (t1-t0) / (sqrt2*sig) )
            s = s + amp * sig * (np.pi/2.0)**.5 * (int_t2-int_t1)
        return s
        
    # calculate centered, pixel based spectrum
    T = (np.arange(0, n)-n*.5) * dwell_time + gauss_pars[0][0]
    spec = gaussint(T-dwell_time/2, T + dwell_time/2, gauss_pars)
    spec *= 1./spec.sum()    
    return spec

def ion_wien_deconvolve(data, dwell_time, f=.7):
    """Deconvolve the time resolved ion signal given by data using the
    Wien deconvolution technique.
    
    :param data: (ndarray) Ion signal to be deconvolved.
    :param dwell_time: (float) Dwell time of the pixels in micrometers.
    :param f: (float) Effectively smoothens the result for higher values.
    :returns: (ndarray) Deconvolved ion signal.
    """
    
    data = np.asfarray(data)
    d_signal = np.concatenate([np.zeros(data.size/2), data.ravel(), np.zeros(data.size/2)])
    d_psf = ion_tof_spectrum(dwell_time, d_signal.size)
    
    # fourier transforms
    D_signal = np.fft.fft(d_signal)
    D_signal_power = np.abs(D_signal)**2
    D_psf = np.fft.fft(d_psf)
    D_psf_power = np.abs(D_psf)**2
    D_noise_power = ( (data.max()*f)**.5 * d_signal.size**.5 )**2
    
    # wien filter
    #W = D_psf.conjugate() * D_meas_power/(D_psf_power*D_meas_power+D_noise_power)
    W = D_signal_power/(D_signal_power+D_noise_power) / D_psf
    d_estimate = np.abs(np.fft.fftshift(np.fft.ifft(D_signal * W)))
    
    return d_estimate[data.size/2:data.size/2+data.size].reshape(data.shape)

def ion_direct_unfold(data, dwell_time):
    """Deconvolve the time resolved ion signal given by data using a
    direct deconvolution method.
    
    :param data: (ndarray) Ion signal to be deconvolved.
    :param dwell_time: (float) Dwell time of the pixels in micrometers.
    :returns: (ndarray) Deconvolved ion signal.
    """

    # calculate a pixel based spectrum from the tof-multipeak fit
    
    # gaussint fit
    gauss_pars = [[17.31395979720519, 63112.69760492675, 0.03123937437419509],
             [12.290841184555568, 6701.023533805622, 0.040793741078493824],
             [10.060823913081139, 7150.302486228399, 0.04562454121523191],
             [8.727893992574595, 2282.387336822463, 0.0470714790645937],
             [7.829032989499102, 697.6137824761323, 0.04166911964137886]]

    # gauss integral
    def gaussint(t1, t2, peaks):
        s = np.zeros_like(t1)
        sqrt2 = 2.**.5
        for t0, amp, sig in peaks:
            int_t2 = erf( (t2-t0) / (sqrt2*sig) )
            int_t1 = erf( (t1-t0) / (sqrt2*sig) )
            s = s + amp * sig * (np.pi/2.0)**.5 * (int_t2-int_t1)
        return s

    # calculate some values from gauss_pars
    norm = gaussint(0, 20, gauss_pars) # norm of the multipeak gauss integral
    rb1_frac = gaussint(0, 20, [gauss_pars[0]]) * (1./norm) # fraction of rb+ ions
    t0 = gauss_pars[0][0]            # times are relative to rb+ peak
    gauss_pars = gauss_pars[1:]           # exclude rb+ peak from calculations

    # calculate pixel based spectrum
    n_bins = int(t0 / dwell_time)
    T = np.arange(1, n_bins) * dwell_time
    spec = gaussint(t0 - T, t0 - T + dwell_time, gauss_pars)[::-1] * (1./norm)

    # use spectrum to unfold the measured ion numbers
    # prepare source and destination arrays
    shape = data.shape
    source = np.asfarray(data.ravel().copy())
    result = np.zeros_like(source)

    for i in range(spec.size, source.size)[::-1]:
        n_atoms = source[i] / rb1_frac
        result[i] = n_atoms
        source[i - spec.size:i] -= spec * n_atoms

    return result.reshape(shape)
    
