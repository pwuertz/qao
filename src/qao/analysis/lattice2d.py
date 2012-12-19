"""
Lattice2d
---------

Provides utility functions for analyzing 2d lattice images.

The functions in this module are designed for easy analysis of 2d lattice
images. They are based on fast fourier transformations and fourier analysis
to extract information like orientation and phase of lattice structures
from image data.

The high-level functions analyze images directly from files, the low-level
functions operate on numpy arrays.
"""

import warnings
import numpy as np
from scipy import optimize
from scipy import ndimage

import qao.utils as utils

def mask_angles_near_kvec(phi, kvec, delta_deg=20):
    kphi  = np.arctan2(kvec[0], kvec[1])
    mask1 = np.abs(utils.angle_diff(phi, kphi))       < (delta_deg*np.pi/180.)
    mask2 = np.abs(utils.angle_diff(phi, kphi+np.pi)) < (delta_deg*np.pi/180.)
    return mask1 + mask2

def mask_radii_notnear_kvec(r, kvec, r_fraction=.2):
    kr = np.sqrt(kvec[0]**2 + kvec[1]**2)
    mask1 = (r > kr*(1.+r_fraction))
    mask2 = (r < kr*(1.-r_fraction))
    return mask1 + mask2

def maximum_position(power_masked, kx, ky):
    # estimate the maximum by parabolic->gaussian interpolation of pixels
    dkx, dky = kx[0,1]-kx[0,0], ky[1,0]-ky[0,0]
    iy_max, ix_max = ndimage.maximum_position(power_masked)
    data_roi = power_masked.data[iy_max-1:iy_max+2, ix_max-1:ix_max+2]
    x0, y0, z0 = utils.parab_interpolation(np.log(data_roi), 1, 1)
    k_vec = np.array([(x0+ix_max-1)*dkx + kx[0, 0], (y0+iy_max-1)*dky + ky[0, 0]])
    amp = np.exp(z0)
    return k_vec, amp

def power_spectra(data_list, edges = False, normalized=True):
    """
    Calculate the (normalized) power spectra for each 2d-array in data_list.
    Return a list and the sum of all power spectra.
    """
    h, w = data_list[0].shape
    
    # data must be zero padded for non periodic signals
    zero_padded_data = np.zeros([2*h, 2*w], dtype = float)
    power_spec_sum = np.zeros([2*h, 2*w], dtype = float)
    
    # calculate all |fft|^2 images
    power_list = []
    for data in data_list:
        zero_padded_data[h/2:h/2+h, w/2:w/2+w] = data
        power_spec = np.abs(np.fft.fft2(zero_padded_data))**2
        if normalized: power_spec *= 1./power_spec[0,0]
        power_spec_sum += power_spec
        power_list.append(np.fft.fftshift(power_spec))

    if normalized: power_spec_sum *= 1./power_spec_sum[0,0]    
    power_spec_sum = np.fft.fftshift(power_spec_sum)
    
    if edges: 
        #create edges from the first data set in list
        fx, fy = utils.fft2freq_padded(data_list[0])
        return power_list, power_spec_sum, fx, fy
    return power_list, power_spec_sum

def search_kvecs_in_powerspec(power_spec):
    """
    Search for two peaks with similar radii in the power spectrum. Return
    the k-vectors and and their amplitude. Also return the masks for
    selecting peak1, peak2 and the noise nearby.
    """
    nx, ny = power_spec.shape[0]/2, power_spec.shape[1]/2

    # frequency map (2*pi*f), cartesian and polar
    dkx, dky = 2*np.pi * 1./(2*nx), 2*np.pi * 1./(2*ny)
    ky, kx = np.ogrid[-ny:ny, -nx:nx]
    kx, ky = kx * dkx, ky * dky
    kr = np.sqrt(kx**2 + ky**2)
    kphi = np.arctan2(kx, ky)
    
    # filter out freqs below 3 oszillations, find global max
    kmin = 3 * 2*np.pi/min(nx,ny)
    power_spec_masked = np.ma.array(power_spec, mask=(kr < kmin))
    k1_f, amp1 = maximum_position(power_spec_masked, kx, ky)

    # mask for finding peak at same radius but different angle
    power_spec_masked.mask += mask_radii_notnear_kvec(kr, k1_f)
    power_spec_masked.mask += mask_angles_near_kvec(kphi, k1_f)
    k2_f, amp2 = maximum_position(power_spec_masked, kx, ky)
    
    # recreate masks for checking
    peak1_mask = mask_radii_notnear_kvec(kr, k1_f) + ~mask_angles_near_kvec(kphi, k1_f)
    peak2_mask = mask_radii_notnear_kvec(kr, k1_f) + ~mask_angles_near_kvec(kphi, k2_f)
    noise_mask = mask_radii_notnear_kvec(kr, k1_f) + ~peak1_mask + ~peak2_mask
    
    return (k1_f, amp1), (k2_f, amp2), (peak1_mask, peak2_mask, noise_mask)

def findWaveVectorsFromDataList(data_list, length_guess):
    """
    Find the wave vectors of the two plane waves forming a 2d lattice.
    
    Assuming the images in data_list contain the signals of two plane
    waves, determine the wave vectors k1 and k2 of these waves. The
    phase of the waves may vary for each image, but it is assumed that
    the wave vectors do not change. A wavelength guess in units of
    pixels is required for this search, the target wavelength must be
    within +/- 10% of the guess.
    
    This method searches for peaks in the sum of all power spectra to
    find the wave vectors.
    
    :param data_list: ([ndarray]) List of images to be analyzed.
    :param length_guess: (float) Wavelength guess in units of pixels.   
    :returns: (k1, k2) Wave vectors for the two plane waves found.
    """
    
    # calculate the 2d autocorrelation with correct zero padding
    autocorr2d = utils.autocorr2d_sum(data_list)
    
    # calculate fft and fft frequencies
    fft_data = np.fft.fftshift(np.abs(np.fft.fft2(autocorr2d)))
    kx = 2*np.pi * np.fft.fftshift(np.fft.fftfreq(autocorr2d.shape[1]))
    ky = 2*np.pi * np.fft.fftshift(np.fft.fftfreq(autocorr2d.shape[0]))
    dkx, dky = kx[1]-kx[0], ky[1]-ky[0]
    
    # clip to frequencies between kmin and kmax
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
    Find the phase of a known plane wave for each image in a list.
    
    Assuming the image in data contains a plane wave represented by
    wave vector k_vec, find the phase :math:`\phi` of the plane wave,
    where :math:`\phi = 0` represents a maximum at the center of the
    image. An amplitude normalized to the data is also given.
    
    :param data_list: ([ndarray]) List of images to be analyzed.
    :param k_vec: (ndarray) Wave vector for the analysis.
    :returns: (phi_array, rel_amplitude_array)
    """
    
    # create a centered plain wave defined by k_vec 
    ny, nx = data_list[0].shape
    Y, X = np.ogrid[-(ny-1)*.5:(ny-1)*.5:1j*ny, -(nx-1)*.5:(nx-1)*.5:1j*nx]
    k_wave = np.exp(1j*(X*k_vec[0]+Y*k_vec[1]))
    
    # calculate the fourier component for k_vec, normalize to data.sum
    fk = np.array([(k_wave*data).sum() / data.sum() for data in data_list])
    # return the complex phase and relative amplitude
    return np.angle(fk), np.abs(fk)

def reciprocalLattice2D(a1, a2):
    """
    Calculate the reciprocal lattice vectors from lattice vectors.
    
    The lattice vectors are assumed to be two-dimensional. For two
    lattice vectors a1 and a2, calculate the reciprocal lattice vectors b1
    and b2, assuming that the third lattice vector a3 is (0, 0, 1).
    
    :param a1: (array-like) First lattice vector.
    :param a1: (array-like) Second lattice vector.
    :returns: (b1, b2) Reciprocal lattice vectors.
    
    Example::
    
        >>> a1, a2 = (0,1), (1,0)
        >>> reciprocalLattice2D(a1, a2)
        (array([-0., 6.28318531]), array([6.28318531, -0.]))
    """
    V = a1[0]*a2[1] - a1[1]*a2[0]
    b1 = (2*np.pi)/V * np.asfarray([ a2[1],-a2[0]])
    b2 = (2*np.pi)/V * np.asfarray([-a1[1], a1[0]])
    return b1, b2

def polarCoords(vec):
    """
    Return the polar coordinates of a vector with two components.
    
    :param vec: (array-like) 2d-vector.
    :returns: (phi, r) Polar angle phi, radius r.
    
    Example::
    
        >>> polarCoords([1,0])
        (0.0, 1.0)
        >>> polarCoords([0,-1])
        (-1.5707963267948966, 1.0)
    """
    return np.arctan2(vec[1],vec[0]), np.sqrt((np.asfarray(vec)**2).sum())

def findPhase(data, k_vec):
    """
    .. warning::
    
        Deprecated, use :func:`findPhasesFromDataList` instead.
    
    Assuming the image in data contains a plain wave represented by
    wave vector k_vec, find the phase phi of the plain wave.
    Phi=0 represents a maximum at the center of the image.
    
    returns: phi, rel. correlation amplitude 
    """
    warnings.warn("findPhase deprecated in favor of findPhasesFromDataList")
    
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
    Convenience function for running :func:`findWaveVectors` on a list
    of qmi images.
    
    The guess for the lattice spacing may be given in units of nanometers, as
    the conversion from pixels to real space is determined from the qmi metadata.
    The default is a guess of 600 nm spacing.
    
    A limit may be set to shorten computation for huge lists of images. 
    
    :param spacing_guess_nm: (float) Wavelength guess in units of nanometers.
    :param limit: (int) Only take the first `limit` images into account.
    :param callback: Report the current status by calling callback(message, i, n).
    :returns: (k1, k2) Two wave vectors in units of pixels.
    """
    
    # estimated wavelength nm->px
    nm_per_px = float(qmi_list[0].image_parameters["psize_nm"])
    length_guess_px = float(spacing_guess_nm) / nm_per_px
        
    # return the result from findWaveVectors
    assert(len(qmi_list[:limit]) != 0)
    data_list = [image.image_data for image in qmi_list[:limit]]
    if callback: callback("determining wave vectors", 0, 1)
    result = findWaveVectorsFromDataList(data_list, length_guess_px)
    if callback: callback("determining wave vectors", 1, 1)
    return result

def findPhasesFromQmiList_new(qmi_list, k_vec, callback=None):
    """
    Convenience function for running :func:`findPhasesFromDataList`
    on a list of qmi images.
    
    A callback method can be set to keep a user informed about
    the progress, although only start and end of operation are
    signalled.
    
    :param qmi_list: ([qmi]) List of qmi images to be analyzed.
    :param k_vec: (ndarray) Wave vector to analyze the phase for.
    :param callback: Report status by calling callback(message, i, n).
    :returns: (phi_array, rel_amplitude_array)
    """
    
    # return the result from findWaveVectors
    if callback: callback("determining wave vectors", 0, 1)
    result = findPhasesFromDataList([image.image_data for image in qmi_list], k_vec)
    if callback: callback("determining wave vectors", 1, 1)
    return result

def findPhasesFromQmiList(qmi_list, k_vec, callback=None):
    """
    .. warning::
    
        Deprecated, use :func:`findPhasesFromQmiList_new` instead.
    
    Convenience function for running :func:`findPhase`
    on a list of qmi images.
    
    Each image in qmi_list is analyzed by :func:`findPhase` and the
    results are returned as lists. Also, a callback method can be
    set to keep a user informed about the progress.
    
    :param qmi_list: ([qmi]) List of qmi images to be analyzed.
    :param k_vec: (ndarray) Wave vector to analyze the phase for.
    :param callback: Report status by calling callback(message, i, n).
    :returns: (phi_list, amp_list) Phases, relative amplitudes.
    """
    warnings.warn("findPhasesFromQmiList is deprecated in favor of findPhasesFromQmiList_new")
    
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
    """
    High level function for filtering and correcting lattice images.
    
    This is a convenience function using :func:`filter_correct` to filter
    and correct a list of images and returning the sum of the result
    afterwards.
    
    .. seealso:: :func:`filter_correct` 
    """    
    
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
    """
    High level function for filtering and correcting lattice images.
    
    For a list of images, return a list of corrected images, shifted
    according to their phases. The list may also be filtered by phases
    so that only images within a specific phase distance interval
    [rdphi_min, rdphi_max] from a reference are included in the result.
    
    :param data_list: ([ndarray]) List of images to be processed.
    :param k1: (ndarray) First wave vector.
    :param k2: (ndarray) Second wave vector.
    :param phi1: (ndarray) Phases for the first plane wave for each image.
    :param phi2: (ndarray) Phases for the second plane wave for each image.
    :param phi1_ref: (float) Reference phase for first plane wave.
    :param phi2_ref: (float) Reference phase for second plane wave.
    :param rdphi_min: (float) Minimum difference from reference phase.
    :param rdphi_max: (float) Maximum difference from reference phase.
    :param callback: Report the current status by calling callback(message, i, n).
    :param noshift: (bool) If True, do not shift the images, only filter them.
    :returns: ([ndimage]) List containing filtered and corrected images.
    
    .. seealso:: :func:`filter_correct_sum`
    """    
    
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
