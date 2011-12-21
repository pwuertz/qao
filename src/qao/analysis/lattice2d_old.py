#
# This module is deprecated and should not be used anymore
#

import numpy
from scipy import optimize, interpolate, polyfit
import utils
from fitpack import gauss1d

def findEnvelope(data, length, interpolation="linear"):
   """
   if data describes a periodic function with length being
   the periode length, return 2 functions enveloping the
   periodic function by finding the minima and maxima

   returns [minima, maxima]

   interpolation may be "linear" or "cubic"
   """

   # calculate number of periods (n) in data
   n = int(data.size / length)
   X = numpy.arange(data.size)
   mins = numpy.zeros([n + 1, 2])
   maxs = numpy.zeros([n + 1, 2])

   # find minimum/maximum for n blocks
   for i in range(n):
      # x and data values of the current block

      x_block = X[i * length:(i + 1) * length]
      d_block = data[i * length:(i + 1) * length]

      # find min/max
      bmin = d_block.min()
      bmax = d_block.max()

      # save min/max position and value
      mins[i, 0] = x_block[d_block == bmin][0]
      maxs[i, 0] = x_block[d_block == bmax][0]
      mins[i, 1] = bmin
      maxs[i, 1] = bmax

   # correct min/max for the first block
   mins[0, 0] = 0 ; maxs[0, 0] = 0
   # correct min/max for the last block
   mins[ - 1, 0] = X[ - 1] ; maxs[ - 1, 0] = X[ - 1]
   mins[ - 1, 1] = data[ - length * 0.7:].min()
   maxs[ - 1, 1] = data[ - length * 0.7:].max()

   # setup interpolation
   mins_interp = interpolate.interp1d(mins[:, 0], mins[:, 1], kind=interpolation)
   maxs_interp = interpolate.interp1d(maxs[:, 0], maxs[:, 1], kind=interpolation)

   # return min and max function
   return [mins_interp(X), maxs_interp(X)]

def analyzeFFT(data):
   """
   calculate the FFT of data
   try to eliminate the zero order peak
   try to fit the most prominent residual peak

   returns [length, data_fft, data_fft_nozero, peak]
   """

   # calculate fft and frequencies
   data_fft = numpy.abs(numpy.fft.rfft(data))
   data_fft /= data_fft.sum()
   freqs = numpy.arange(data_fft.size)

   # try to fit zero order peak
   fitfunc1 = lambda p: data_fft - p[0] * 1.0 / (p[1] * freqs + 1) + p[2]
   pars, return_val = optimize.leastsq(fitfunc1, [data_fft[0], 1, 0])
   data_fft_nozero = fitfunc1(pars)

   # try to find / fit a peak
   data_fft_nozero2 = data_fft_nozero.copy()
   data_fft_nozero2[:3] = 0
   freqmax = freqs[data_fft_nozero2 == data_fft_nozero2.max()][0]
   fitfunc2 = lambda p: data_fft_nozero2 - p[0] * numpy.exp(-((p[1] - freqs) ** 2) / (2 * p[2] ** 2))
   pars, return_val = optimize.leastsq(fitfunc2, [data_fft_nozero2[freqmax], freqmax, 1])

   # return fit results and data
   length = float(data.size) / pars[1]
   data_peak = data_fft_nozero2 - fitfunc2(pars)
   fftrel = data_peak.sum() / (data_fft - data_fft_nozero).sum()
   return [length, fftrel, data_fft, data_fft_nozero, data_peak]

def autocorrelate(data):
   """
   calculate autocorrelation function (normalized)
   """
   autocorr = numpy.correlate(data, data, "same")
   maximum = autocorr.max()
   autocorr = autocorr[autocorr.size / 2 : 0 : - 1]
   autocorr /= maximum
   return autocorr

def analyzeAutocorrelation(data, lat_spacing_guess_px):
   """
   return [length, amplitude, autocorr, autocorr_fit]
   """

   autocorr = autocorrelate(data)
   
   # new method
   
   # flatten, step1 (polyfit 2nd order)
   X = numpy.arange(len(autocorr), dtype=float)
   (p2, p1, p0) = polyfit(X, autocorr, 2)
   autocorr_corse = (p2*X**2 + p1*X + p0)
   autocorr_flat = autocorr - autocorr_corse
   
   # flatten, step2 (find envelope) # envelope works better with reduced spacing length
   autocorr_flat_min, autocorr_flat_max = findEnvelope(autocorr_flat, lat_spacing_guess_px*0.94, "linear")
   autocorr_flat_amp = autocorr_flat_max - autocorr_flat_min
   autocorr_flat_off = .5 * (autocorr_flat_max + autocorr_flat_min)
   
   # cos fit autocorrelation
   X = 2 * numpy.pi * numpy.arange(autocorr.size, dtype=float)
   fitfunc = lambda freq: (0.5*autocorr_flat_amp * numpy.cos(X * freq)) + autocorr_flat_off + autocorr_corse
   errfunc = lambda freq: autocorr - fitfunc(freq)
   freq, return_val = optimize.leastsq(errfunc, 1.0 / lat_spacing_guess_px)

   # old method
   
   # flatten autocorrelation
   #autocorr_min, autocorr_max = findEnvelope(autocorr, length_guess, "linear")
   #offset = 0.5 * (autocorr_max + autocorr_min)
   #autocorr_flat = autocorr - offset

   # find envelope via flat autocorrelation
   #autocorr_flat_min, autocorr_flat_max = findEnvelope(autocorr_flat, length_guess, "linear")
   #autocorr_min, autocorr_max = [autocorr_flat_min + offset, autocorr_flat_max + offset]
   #autocorr_amp = autocorr_max - autocorr_min

   # cos fit autocorrelation
   #X = 2 * numpy.pi * numpy.arange(autocorr.size, dtype=numpy.float)
   #fitfunc = lambda freq: (0.5 * numpy.cos(X * freq) + 0.5) * autocorr_amp + autocorr_min
   #errfunc = lambda freq: autocorr - fitfunc(freq)
   #freq, return_val = optimize.leastsq(errfunc, 1.0 / length_guess)

   # return results
   amp = autocorr_flat_amp.sum() / autocorr.size # average amplitude
   return [1.0 / freq, amp, autocorr, fitfunc(freq)]

def analyzeLinescan(linescan, length, phi_guess=0.0, type="hanning"):
    """
    Analyze the linescan of a lattice structure. The exact lattice spacing is required
    for this operation. The linescan is convolved with the 'hanning' function by default,
    or hanning, blackman, hamming, bartlett, none if specified by type. 
    
    Returns:
      [linescan, linescan_smooth, fitfunc(phase), phase, linescan_min, linescan_max]
    """
	# smooth periodic data (convolution)
    def smooth_lin(data, n):
        F = numpy.concatenate((numpy.arange(n)[:: - 1], numpy.arange(n)[1:]))
        F /= F.sum()
        return numpy.convolve(data, F, "same")
    def smooth_cos(data, periodeLen):
        n = round(periodeLen)
        F = 1 - numpy.cos(numpy.arange(0, n + 1) * numpy.pi / n) ** 2
        F /= F.sum()
        return numpy.convolve(data, F, "same")
    def smooth_ncos(data, periodeLen):
        n = round(periodeLen)
        F = numpy.cos(numpy.arange(0, n + 1) * numpy.pi / n) ** 2
        F /= F.sum()
        return numpy.convolve(data, F, "same")
    def smooth_sin(data, periodeLen):
        n = round(periodeLen)
        F = numpy.sin(numpy.arange(0, n + 1) * numpy.pi / n)
        F /= F.sum()
        return numpy.convolve(data, F, "same")

    def smooth(data, periodeLen, type):
    	if type != "None":
            window = eval("numpy.%s(%d)" % (type, periodeLen))
            return numpy.convolve(data, window / window.sum(), "same")
        else:
            return data

    # smooth linescan
    linescan_smooth = smooth(linescan, length * 0.65, type)
    linescan_min, linescan_max = findEnvelope(linescan_smooth, length, "linear")
    linescan_amp = linescan_max - linescan_min

    # fit smoothed linescan
    X = 2 * numpy.pi * numpy.arange(linescan_smooth.size, dtype=numpy.float)

    # fit phase, length
    #fitfunc = lambda p: 0.5 * (1+numpy.sin(X/p[0] + p[1])) * linescan_amp + linescan_min
    #errfunc = lambda p: linescan_smooth - fitfunc(p)
    #pars, return_val = optimize.leastsq(errfunc, [length, phi_guess])

    fitfunc = lambda phi: 0.5 * (1 + numpy.cos(X / length + phi)) * linescan_amp + linescan_min
    errfunc = lambda phi: linescan_smooth - fitfunc(phi)
    phase, return_val = optimize.leastsq(errfunc, phi_guess)

    return [linescan, linescan_smooth, fitfunc(phase), phase, linescan_min, linescan_max]

def findAngle(data, length_guess, scan_range=(-12, - 4)):
   """
   Finds the angle phi in scan_range, under which the image in "data" is rotated with
   respect to the imaging coordinates.
   The image must contain at least one lattice structure in one direction for this to work.
   """
   breiten_neu = []
   breiten_alt = []
   x = numpy.arange(scan_range[0], scan_range[1], .1)

   for phi in x:
     temp = data.copy()
     temp = utils.rotate(temp, phi)

     linescan_neu = temp.sum(axis=0)
     linescan_alt = temp.sum(axis=1)
     breiten_neu.append(analyzeAutocorrelation(linescan_neu, length_guess)[1])
     breiten_alt.append(analyzeAutocorrelation(linescan_alt, length_guess)[1])

   def fitfunction(p, xachse):
     return (p[0] * numpy.exp(-((xachse - p[1]) / p[2]) ** 2) + p[3])

   def errorfunction(p, xachse, data):
     return data - fitfunction(p, xachse)

   (pars_neu, success_neu) = optimize.leastsq(errorfunction, [0.15, scan_range[len(scan_range) // 2], 5, 0], args=(x, breiten_neu))
   (pars_alt, success_alt) = optimize.leastsq(errorfunction, [0.15, scan_range[len(scan_range) // 2], 5, 0], args=(x, breiten_alt))

   (neu, alt) = (True, True)
   if pars_neu[0] < 0.12: neu = False
   if pars_alt[0] < 0.12: alt = False
   if not alt and not neu:
      raise Exception, "No lattice structure found"

   phi = (pars_neu[1] * neu + pars_alt[1] * alt) / (alt + neu)

   return phi

def findAngle2(data, lat_spacing_guess_px, rot_angle_scan_range_deg=(-10,-5)):
    """
    Find the angle phi (degrees) in scan_range for each lattice axis, under
    which the image "data" is rotated with respect to the imaging coordinates.
    
    Returns [[xphi, xamp, xrchisq, yphi, yamp, yrchisq], [x, xamps, yamps]]
    """
    xamps = []
    yamps = []
    dx = .1
    x = numpy.arange(rot_angle_scan_range_deg[0], rot_angle_scan_range_deg[1], dx)
    
    for phi in x:
        temp = data.copy()
        temp = utils.rotate(temp, phi)
        
        xlinescan = temp.sum(axis=0)
        ylinescan = temp.sum(axis=1)
        xamps.append(analyzeAutocorrelation(xlinescan, lat_spacing_guess_px)[1])
        yamps.append(analyzeAutocorrelation(ylinescan, lat_spacing_guess_px)[1])

    xfit,xpars = gauss1d(xamps)
    yfit,ypars = gauss1d(yamps)
    
    xchisq = ((xamps-xfit)**2).sum() / 0.003**2
    ychisq = ((yamps-yfit)**2).sum() / 0.003**2
    xrchisq = xchisq/(len(xamps)-4)
    yrchisq = ychisq/(len(yamps)-4)
    
    xphi = x[0] + xpars[1] * dx
    yphi = x[0] + ypars[1] * dx
    return [[xphi, xpars[0], xrchisq, yphi, ypars[0], yrchisq], [x, xamps, yamps]]
