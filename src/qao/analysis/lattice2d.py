#
# conventions
#
# data: a numpy 2d array 
# linescan: a numpy 1d array
# callback: a callable function with args (string msg, int i, int n)
# length_guess: a spacing or wavelength measured in pixel units
# k1, k2, k_vec: wave vectors
# l1, l1: lattice vectors
# qmi_list: a list of qmi images
#

import qao.utils as utils
from plainwave import plainwaveCorrelation

import numpy as np
from scipy import optimize

def findWaveVectorsFromDataList(data_list, length_guess):
    """
    Find the wave vectors of the plain waves forming a 2d lattice.
    data_list must be a list of numpy 2d-arrays.
    
    A wavelength guess in units of pixels is required for the search.
    An interval of +/- 10% of the wavelength guess will be searched.   
    
    returns: k1, k2
    """
    
    # calculate the 2d autocorrelation with correct zero padding
    autocorr2d = utils.autocorr2d_sum(data_list)
    
    # calculate fft and fft frequencies
    fft_data = np.fft.fftshift(np.abs(np.fft.fft2(autocorr2d)))
    kx = 2*np.pi * np.fft.fftshift(np.fft.fftfreq(autocorr2d.shape[1]))
    ky = 2*np.pi * np.fft.fftshift(np.fft.fftfreq(autocorr2d.shape[0]))
    dkx, dky = kx[1]-kx[0], ky[1]-ky[0]
    
    # clip to frequencies < kmax
    k_min = 2*np.pi / (length_guess*1.1)
    k_max = 2*np.pi / (length_guess*0.9)
    ix1_clip = kx.size/2 - k_max/dkx - 1
    ix2_clip = kx.size/2 + k_max/dkx + 1
    iy1_clip = ky.size/2 - k_max/dky - 1
    iy2_clip = ky.size/2 + k_max/dky + 1
    kx = kx[ix1_clip: ix2_clip]
    ky = ky[iy1_clip: iy2_clip]
    fft_data = fft_data[iy1_clip: iy2_clip, ix1_clip: ix2_clip]
    
    # calculate |k| and angle maps
    kr = np.sqrt(kx.reshape([1,kx.size])**2 + ky.reshape([ky.size,1])**2)
    kphi = np.arctan2(ky.reshape([ky.size,1]), kx.reshape([1,kx.size]))
    
    # create masks for 2 peaks
    kr_mask = (kr < k_max) * (kr > k_min)
    dphi = lambda phi: abs(((kphi-phi)+np.pi)%(2*np.pi) - np.pi)
    kphi_mask1 = dphi(0) < np.pi/4
    kphi_mask2 = dphi(np.pi/2) < np.pi/4
    
    # key out data outside the masks
    peak1 = fft_data * kr_mask * kphi_mask1
    peak2 = fft_data * kr_mask * kphi_mask2
    
    # find and interpolate the maximum for each peak
    # return the interpolated maximum position in k-space
    def findmax(data):
        i_max = data.argmax()
        ix_max = int(i_max % data.shape[1])
        iy_max = int(i_max / data.shape[1])
        x0, y0, z0 = utils.parab_interpolation(data, ix_max, iy_max)
        return np.array([kx[0]+x0*dkx, ky[0]+y0*dky])
    
    return [findmax(peak1), findmax(peak2)]

def findPhasesFromDataList(data_list, k_vec):
    """
    Assuming the image in data contains a plain wave represented by
    wave vector k_vec, find the phase phi of the plain wave.
    Phi=0 represents a maximum at the center of the image.
    A signal amplitude normalized to the data.sum is also given.
    
    returns: phi_array, rel_amplitude_array
    """
    
    # create a centered plain wave defined by k_vec 
    h, w = data_list[0].shape
    X = np.arange(w, dtype=float).reshape([1,w]) - .5*(w-1)
    Y = np.arange(h, dtype=float).reshape([h,1]) - .5*(h-1)
    k_wave = np.exp(1j*(X*k_vec[0]+Y*k_vec[1]))
    
    # calculate the fourier component for k_vec, normalize to data.sum
    fk = np.array([(k_wave*data).sum() / data.sum() for data in data_list])
    # return the complex phase and relative amplitude
    return np.angle(fk), np.abs(fk)

def findWaveVectors(autocorr2d_data, length_guess):
    """
    Assume that autocorr2d_data is the autocorrelation of an
    image that contains a lattice formed by two plain waves.
    Find the wave vectors of the plain waves.
    
    returns: k1, k2
    """   
    # create search grid for phi and length
    data = autocorr2d_data
    
    # rough check for all angles
    dphi = 0.5
    phi_list = np.arange(-90., 90., dphi)
    phi_f = lambda ip: phi_list[0] + ip*dphi
    # rough check length +- 10%, 20 samples total 
    length_interval = length_guess*0.2
    dlength = float(length_interval) / 20
    length_list = np.arange(length_guess-length_interval/2,
                            length_guess+length_interval/2,
                            dlength)
    length_f = lambda il: length_list[0] + il*dlength
    
    #####################################################################
    
    # calculate map
    corrs_map = np.zeros([len(phi_list), len(length_list)], dtype=float)
    for ip, phi in enumerate(phi_list):
        for il, length in enumerate(length_list):
            corrs_map[ip, il] = plainwaveCorrelation(data, phi, length)
    
    #####################################################################
            
    # find first maximum
    length_max = length_f(corrs_map.argmax() % corrs_map.shape[1])
    phi_max = phi_f(corrs_map.argmax() / corrs_map.shape[1])
    # refine first maximum
    func = lambda pars: -plainwaveCorrelation(data, pars[0], pars[1])
    phi1_max, length1_max = optimize.fmin(func, [phi_max, length_max], disp=0)
    
    #####################################################################
    
    # find second maximum
    # search at +90deg, +-45deg
    
    # enlarge map
    corrs_map = np.concatenate([corrs_map,corrs_map], axis=0)
    # clip map to new search interval
    search_ip = int((phi1_max+90-phi_list[0])/dphi)
    search_ip1 = search_ip - int(45./dphi)
    search_ip2 = search_ip + int(45./dphi)
    corrs_map2 = corrs_map[search_ip1:search_ip2, :]
    
    # find second maximum
    length_max = length_f(corrs_map2.argmax() % corrs_map2.shape[1])
    phi_max = phi_f(search_ip1 + corrs_map2.argmax() / corrs_map2.shape[1])
    # refine second maximum
    func = lambda pars: -plainwaveCorrelation(data, pars[0], pars[1])
    phi2_max, length2_max = optimize.fmin(func, [phi_max, length_max], disp=0)
    
    #####################################################################
    
    # calculate wave vectors
    k1 = (2*np.pi/length1_max) * np.array([np.cos(phi1_max*np.pi/180), np.sin(phi1_max*np.pi/180)])
    k2 = (2*np.pi/length2_max) * np.array([np.cos(phi2_max*np.pi/180), np.sin(phi2_max*np.pi/180)])
    
    # ensure our conventions
    # k1 is the wave in horizontal direction
    if abs(k1[0]/k1[1]) < abs(k2[0]/k2[1]): k1, k2 = k2, k1
    # k1 shall point to positive x
    if k1[0] < 0: k1 *= -1
    # k2 shall point to positive y
    if k2[1] < 0: k2 *= -1
        
    return [k1, k2]

def reciprocalLattice2D(a1, a2):
    """
    Calculate the reciprocal lattice vectors from lattice
    vectors a1 and a2, assuming that a3 is (0,0,1).
    
    returns: b1, b2
    """
    V = a1[0]*a2[1] - a1[1]*a2[0]
    b1 = (2*np.pi)/V * np.array([ a2[1],-a2[0]])
    b2 = (2*np.pi)/V * np.array([-a1[1], a1[0]])
    return b1, b2

def polarCoords(vec):
    """
    Return angle and length of a vector.
    
    returns: phi, r
    """
    return np.arctan2(vec[1],vec[0]), np.sqrt((np.array(vec)**2).sum())

def findPhase(data, k_vec):
    """
    Assuming the image in data contains a plain wave represented by
    wave vector k_vec, find the phase phi of the plain wave.
    Phi=0 represents a maximum at the center of the image.
    
    returns: phi, rel. correlation amplitude 
    """
    
    # rotate image so k points to (1,0)
    angle, k = polarCoords(k_vec)
    data = utils.rotate(data, angle*180./np.pi)
    # project wavefronts down to the x-axis, normalized
    linescan = data.sum(axis=0)
    linescan /= linescan.sum()
    # normalized cos(kx-phi) wave
    X = np.arange(len(linescan))
    phi0 = k * X[-1] * 0.5
    def wave(phi):
        w = 1+np.cos(k*X-phi-phi0)
        return w/w.sum()
    
    # calculate correlation between the linescan and a cos wave
    correlation = lambda phi: (wave(phi)*linescan).sum()
    
    # check 40 phases, determine phase of maximum correlation
    phi_range = 2*np.pi*np.arange(40)/40
    corrs = np.array([correlation(phi) for phi in phi_range])
    phi_max = phi_range[corrs.argmax()]
    # determine the relative amplitude of the correlation signal
    offs = corrs.min()
    ampl = corrs.max() - offs
    ampl_rel = ampl/offs

    # fine tune the phase maximum
    pars_max = optimize.fmin(correlation, [phi_max-np.pi], disp=0) + np.pi
    phi_max = pars_max[0]
    
    # return phase to image center
    return phi_max, ampl_rel

def findWaveVectorsFromQmiList_new(qmi_list, spacing_guess_nm=600, limit=None, callback=None):
    """
    Run findWaveVectors on the sum of all autocorrelated images in qmi_list.
    Returns the two wave vectors from findWaveVectors.
    
    spacing_guess_nm: Approximate wavelength of the plainwaves in nm.
    limit: Stop accumulating autocorrelations after the first <limit> images.
    callback: Report the current status by calling callback(message, i, n).
    
    returns: k1, k2
    """
    
    # estimated wavelength nm->px
    nm_per_px = float(qmi_list[0].image_parameters["PixelDistanceX"])
    length_guess_px = float(spacing_guess_nm) / nm_per_px
        
    # return the result from findWaveVectors
    assert(len(qmi_list[:limit]) != 0)
    data_list = [image.image_data for image in qmi_list[:limit]]
    if callback: callback("determining wave vectors", 0, 1)
    result = findWaveVectorsFromDataList(data_list, length_guess_px)
    if callback: callback("determining wave vectors", 1, 1)
    return result

def findWaveVectorsFromQmiList(qmi_list, spacing_guess_nm=600, limit=None, callback=None):
    """
    Run findWaveVectors on the sum of all autocorrelated images in qmi_list.
    Returns the two wave vectors from findWaveVectors.
    
    spacing_guess_nm: Approximate wavelength of the plainwaves in nm.
    limit: Stop accumulating autocorrelations after the first <limit> images.
    callback: Report the current status by calling callback(message, i, n).
    
    returns: k1, k2
    """
    
    # estimated wavelength nm->px
    nm_per_px = float(qmi_list[0].image_parameters["PixelDistanceX"])    
    length_guess = float(spacing_guess_nm) / nm_per_px
    
    # sum of all (limit) single image autocorrelations
    autocorr2d_data = np.zeros(qmi_list[0].image_data.shape, dtype=float)    
    assert(len(qmi_list[:limit]) != 0)
    for i,image in enumerate(qmi_list[:limit]):
        if callback: callback("calculating autocorrelation", i, len(qmi_list[:limit]))
        autocorr2d_data += autocorr2d(image.image_data)
    
    # return the result from findWaveVectors
    if callback: callback("determining wave vectors", 0, 1)
    result = findWaveVectors(autocorr2d_data, length_guess)
    if callback: callback("determining wave vectors", 1, 1)
    return result

def findPhasesFromQmiList_new(qmi_list, k_vec, callback=None):
    """
    Assuming the image in data contains a plain wave represented by
    wave vector k_vec, find the phase phi of the plain wave.
    Phi=0 represents a maximum at the center of the image.
    A signal amplitude normalized to the data.sum is also given.
    
    returns: phi_array, rel_amplitude_array
    """
    
    # return the result from findWaveVectors
    if callback: callback("determining wave vectors", 0, 1)
    result = findPhasesFromDataList([image.image_data for image in qmi_list], k_vec)
    if callback: callback("determining wave vectors", 1, 1)
    return result

def findPhasesFromQmiList(qmi_list, k_vec, callback=None):
    """
    Run findPhase on each image in qmi_list and return lists of the results.

    callback: Report the current status by calling callback(message, i, n).
    
    returns: phi_list, amp_list
    """
    phi_list = np.zeros(len(qmi_list), dtype=float)
    amp_list = np.zeros(len(qmi_list), dtype=float)
    # run findPhase for each qmi image
    if callback: callback("determining phases", 0, len(qmi_list))
    for i,image in enumerate(qmi_list):
        phi, amp = findPhase(image.image_data, k_vec)
        phi_list[i] = phi
        amp_list[i] = amp
        if callback: callback("determining phases", i+1, len(qmi_list))
        
    # return results from findPhase
    return phi_list, amp_list

def corrector2d(qmi_list,
                k1, k2,
                phi1_ref=None, phi2_ref=None,
                threshold_ions_fact = 1./3,
                rphase_delta_accept = 2*np.pi,
                callback=None):
    
    # determine phases
    phi1, amp1 = findPhasesFromQmiList(qmi_list, k1, callback)
    phi2, amp2 = findPhasesFromQmiList(qmi_list, k2, callback)
    
    # determine mean phase
    phi1_mean, stability1 = utils.angle_mean(phi1)
    phi2_mean, stability2 = utils.angle_mean(phi2)
    
    # shall we use mean phase?
    if phi1_ref == None: phi1_ref = phi1_mean
    if phi2_ref == None: phi2_ref = phi2_mean
    
    # determine phase offsets from reference, shift to [-pi,+pi]
    dphi1 = ((phi1-phi1_ref+np.pi)%(2*np.pi))-np.pi
    dphi2 = ((phi2-phi2_ref+np.pi)%(2*np.pi))-np.pi
    
    # calculate lattice vectors from wave vectors
    l1, l2 = reciprocalLattice2D(k1, k2)
    
    # shift images to reference phase
    """
    if callback: callback("shifting images", 0, 1)
    for i, image in enumerate(qmi_list):
        shift = l1 * dphi1[i]/(2*np.pi) + l2 * dphi2[i]/(2*np.pi)
        image.shift(*shift)
    if callback: callback("shifting images", 1, 1)
    
    # post selection: calculate phase offset distance
    rdphi = np.sqrt(dphi1**2 + dphi2**2)
    mask_rdphi = rdphi < rphase_delta_accept
    # post selection: calculate ion number
    nions = np.array([image.image_data.sum() for image in qmi_list])
    mask_nions = nions > (nions.mean() * threshold_ions_fact)
    
    # do post selection
    qmi_masked = []
    mask_combined = mask_rdphi * mask_nions
    for i,image in enumerate(qmi_list):
        if mask_combined[i]: qmi_masked.append(image)
    
    qmi_sum = qmi.sum(qmi_masked)
    """
    
    qmi_sum = filter_correct_sum([image.image_data for image in qmi_list],
                       k1, k2, phi1, phi2, phi1_ref, phi2_ref,
                       rphase_delta_accept, callback=callback)
    
    # return sum of remaining images
    return qmi_sum, phi1_ref, phi2_ref
    
def filter_correct_sum(data_list, k1, k2, phi1, phi2,
                       phi1_ref, phi2_ref,
                       rdphi_min = 0,
                       rdphi_max = np.inf,
                       callback=None, noshift=False):
    # sum = 0
    data_sum = np.zeros(data_list[0].shape, dtype=float)
    # filter and correct data_list
    data_list = filter_correct(data_list, k1, k2, phi1, phi2,
                   phi1_ref, phi2_ref,
                   rdphi_min, rdphi_max,
                   callback, noshift)
    # sum
    for data in data_list:
        data_sum += data
    return data_sum
        
def filter_correct(data_list, k1, k2, phi1, phi2,
                   phi1_ref, phi2_ref,
                   rdphi_min = 0,
                   rdphi_max = np.inf,
                   callback=None, noshift=False):
    
    # determine phase offsets from reference, shift to [-pi,+pi]
    dphi1 = ((phi1-phi1_ref+np.pi)%(2*np.pi))-np.pi
    dphi2 = ((phi2-phi2_ref+np.pi)%(2*np.pi))-np.pi
    
    # create rdphi mask
    rdphi = np.sqrt(dphi1**2 + dphi2**2)
    mask_rdphi = (rdphi <= rdphi_max)*(rdphi >= rdphi_min)
    mask_indices = np.arange(len(mask_rdphi))[mask_rdphi]

    # calculate lattice vectors from wave vectors
    l1, l2 = reciprocalLattice2D(k1, k2)
    # calculate shift vectors
    l1_shifts = np.outer(dphi1/(2*np.pi), l1)
    l2_shifts = np.outer(dphi2/(2*np.pi), l2)
    shifts = l1_shifts + l2_shifts
    
    # shift & filter images, build new list
    if callback: callback("shifting images", 0, 1)
    data_list_new = []
    if not noshift:
        for i in mask_indices:
            data_list_new.append(utils.shift(data_list[i], *(shifts[i])))
    else:
        for i in mask_indices:
            data_list_new.append(data_list[i])
    if callback: callback("shifting images", 1, 1)
    
    return data_list_new
