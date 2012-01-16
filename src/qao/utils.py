"""
Utility functions
=================
"""

import bz2
import numpy as np
from PyQt4 import QtCore, QtGui
from scipy import ndimage

def drawPolygonMask(width, height, points):
    """
    Draw a convex polygon defined by a list of points.
    
    A polygon is drawn into a zeroed numpy array with
    dimensions (height, width), so the pixel value inside
    the polygon is 1.0, else 0.0.
    
    The points are given by a list of (x, y) coordinate
    tuples.
    
    :param width: Width of the 2d array.
    :param height: Height of the 2d array.
    :param points: List of (x, y) coordinates.
    :returns: (ndarray) Polygon mask.
    
    Example::
    
        points = [(10, 10), (100, 20), (110, 50), (20, 40)]
        mask = drawPolygonMask(300, 100, points)
        
    .. plot::
    
        import pylab as p
        from qao.utils import drawPolygonMask
        points = [(10, 10), (100, 20), (110, 50), (20, 40)]
        mask = drawPolygonMask(300, 100, points)
        
        p.figure(figsize=(4,1.6))
        p.gray()
        p.imshow(mask)
        p.show()
    """
    # convert points to QPointF
    points = [QtCore.QPointF(x,y) for x,y in points]
    
    # create qimage and paint polygon
    qi = QtGui.QImage(width, height, QtGui.QImage.Format_RGB32)
    qi.fill(0)
    p = QtGui.QPainter(qi)
    p.setRenderHint(p.Antialiasing)
    p.setPen(QtGui.QPen(QtCore.Qt.NoPen))
    p.setBrush(QtGui.QBrush(QtCore.Qt.white))
    p.drawConvexPolygon(*points)
    p.end()
    
    # if this is correct we don't have to care about strides
    assert qi.numBytes() == (4*height*width)
    
    # create numpy array from qimage data
    data = qi.bits().asstring(qi.numBytes())
    array = np.fromstring(data, dtype=np.int32).reshape(height,width)
    # select one channel from RGB -> map to [0:1] 
    # TODO: is this true for both little and big endian?
    return (array & 0xff) * (1./0xff)

def angle_mean(angle_list_rad):
    """
    Calculate the mean angle from a list of angles in radians.
    
    A list of unity vectors, with the direction given by the
    list of angles is created and the sum is calculated. The
    resulting direction is the mean angle, the length of the
    vector sum may be interpreted as measure of spread.
    
    :returns: (mean, length) Mean angle in rad, Length.
    
    .. seealso:: :func:`angle_mean_std`
    
    Example::
    
        >>> angle_list = [0., 1., 2.]
        >>> angle_mean(angle_list)
        (1.0, 0.69353487057875984)
    """
    angle_list = np.array(angle_list_rad)
    xmean = np.cos(angle_list).sum()
    ymean = np.sin(angle_list).sum()
    phi_mean = np.arctan2(ymean,xmean)
    rel_length = np.sqrt(xmean**2+ymean**2) / len(angle_list)
    return (phi_mean, rel_length)

def angle_mean_deg(angle_list_deg):
    """
    Convenience function for calculating the mean angle from
    a list of angles in degrees.
    
    :returns: (mean, length) Mean angle in deg, Length.
    
    .. seealso:: :func:`angle_mean_std`
    """
    angle_list_rad = np.array(angle_list_deg) * np.pi / 180
    phi_rad, rel_length = angle_mean(angle_list_rad)
    return [phi_rad * 180. / np.pi, rel_length]

def angle_mean_std(angles_rad):
    """
    Calculate the mean angle and the standard deviation from a
    list of angles in radians.
    
    :returns: (mean, std) Mean angle and standard deviation in rad.
    
    Example::
    
        >>> angles_rad = [0., 1., -1.]
        >>> angle_mean_std(angles_rad)
        (0.0, 0.81649658092772603)
    """
    angles_rad = np.asfarray(angles_rad)
    mean_angles = np.angle(np.exp(1j*angles_rad).sum())
    std_angles  = np.std((((angles_rad - mean_angles) + np.pi) % (2*np.pi)) - np.pi)
    return mean_angles, std_angles

def findMostFrequent(data):
    """
    Finds the most frequent element in a list.
    
    The element with the most occurrences within a list is
    returned along with the number of occurrences.
    
    :returns: (object, n) List element, number of occurrences.
    
    Example::
    
        >>> data = [1, 2, 1, 3, 5, 1]
        >>> findMostFrequent(data)
        (1, 3)
    """
    data = np.asarray(data)
    elements = np.unique(data)
    bincount = [(data==i).sum() for i in elements]
    index = bincount.index(max(bincount))
    return (elements[index],max(bincount))

def unique_mean(xdata, *ydatas):
    """
    Sort `xdata` and return only unique elements. Calculate the average
    of values in `ydata` for multiple occurrences of values in `xdata`.
    
    This is particulary useful for arranging data for analysis and plotting,
    since multiple occurrences of values in `xdata` can be interpreted as
    multiple measurements of the same data point, which you might want to
    average.
    
    :param xdata: (ndarray) x-values
    :param ydatas: (ndarray) multiple arrays of y-values
    :returns:
        * **xdata_unique** - unique, sorted x-values
        * **ydata_unique** - y-values matching the x-values output
    
    Example::
        
        >>> xdata  = [1, 2, 5, 2]
        >>> ydata1 = [9, 8, 7, 8]
        >>> ydata2 = [0, 2, 3, 4]
        >>> arrangePlotData(xdata, ydata)
        (array([1, 2, 5]), array([ 9.,  8.,  7.]), array([ 0.,  3.,  3.]))
    """
    # make sure we are using floats
    xdata_unique, indices_inverse = np.unique(xdata, return_inverse=True)
    ydatas = [np.asfarray(ydata) for ydata in ydatas]

    norm = 1. / np.bincount(indices_inverse) 
    ydatas_unique = [norm*np.bincount(indices_inverse, weights=ydata) for ydata in ydatas]  
    
    return tuple([xdata_unique] + ydatas_unique)

def add(array1, array2):
    """
    Adds two 2d-arrays of different shape.
    
    If the size of the arrays does not match, the arrays are
    zero-padded accordingly. The shape of the sum is therefore
    (max(height1,height2) , max(width1,width2)).
    
    :param array1: First 2d-array.
    :param array2: Second 2d-array.
    :returns: (ndarray) Zero-padded sum of array1 + array2.
    
    Example::
    
        >>> a = np.ones((3, 5))
        >>> b = np.ones((3, 3))
        >>> add(a, b).shape
        (3, 5)
    """
    (height1, width1) = array1.shape
    (height2, width2) = array2.shape
    
    height = max(height1,height2)
    width = max(width1, width2)
    newArray = np.zeros((height,width))
    
    newArray[0:height1,0:width1]+=array1
    newArray[0:height2,0:width2]+=array2
    
    return newArray.copy()

def shift(data, pixels_x, pixels_y):
    """
    Shift pixels of an image to the left/right or up/down.
    
    The image dimensions are not changed, pixels moving out of
    the image are lost. Pixels appearing from the corners are
    considered to be zero.
    
    :param data: (ndarray) Image to be shifted.
    :param pixels_x: (int) Move by n pixels to the left.
    :param pixels_y: (int) Move by n pixels upwards. 
    :returns: (ndarray) Shifted image.
    
    .. note::
    
        This method should be deprecated in favor of :func:`scipy.ndimage.shift`
    """
    pixels_x = round(pixels_x)
    pixels_y = round(pixels_y)
    height, width = data.shape
    
    # x axis
    zeros = np.zeros([height, abs(pixels_x)], dtype=float)
    if (pixels_x >= 0):
        data = np.concatenate((data[:, pixels_x:], zeros), axis=1)
    else:
        data = np.concatenate((zeros, data[:, :pixels_x]), axis=1)
    
    # y axis
    zeros = np.zeros([abs(pixels_y), width])
    if (pixels_y >= 0):
        data = np.concatenate((data[pixels_y:, :], zeros), axis=0)
    else:
        data = np.concatenate((zeros, data[:pixels_y, :]), axis=0)
    
    return data

def rebin(d, binsize):
    """
    Rebin an array. The length of the output array will be oldsize/binsize.
    
    The binsize must be an integer divisor of the array's size.
    
    :param d: (ndarray) Array to be binned.
    :param binsize: (int) Size of the new bins.
    :returns: (ndarray) Binned array.
    
    Example::
    
        >>> a = np.array([1,1,2,2,3,3])
        >>> rebin(a, 2)
        array([2, 4, 6])
    """
    if d.size % binsize != 0: raise Exception('invalid binsize')
    d = d.reshape([d.size/binsize, binsize])
    return d.sum(axis=1)

def autocorr2d_sum(data_list):
    """
    Calculate the sum of autocorrelations for a list of 2d-arrays.
    
    Each array in the list is zero-padded and fast fourier transformed.
    The inverse fourier transform of all power spectra is equivalent
    to the 2d autocorrelation function.
    
    The width and height of the result is twice as large due to the zero
    padding, preventing circular convolution. The origin of the autocorrelation
    is in the center of the returned array. 
    
    :param data_list: ([ndarray]) List of 2d arrays to be autocorrelated.
    :returns: (ndarray) Sum of all autocorrelations from `data_list`.
    """
    h, w = data_list[0].shape
    
    # data must be zero padded, as the signal is not periodic
    zero_padded_data = np.zeros([2*h, 2*w], dtype = float)
    rfft_accum_data = np.zeros([2*h, w+1], dtype = float)
    # sum all |fft|^2 images
    for data in data_list:
        zero_padded_data[h/2:h/2+h, w/2:w/2+w] = data
        rfft_data = np.fft.rfft2(zero_padded_data)
        rfft_accum_data += (rfft_data * rfft_data.conjugate()).real
    # inverse transform and shift
    autoc = np.fft.irfft2(rfft_accum_data).real
    autoc = np.fft.fftshift(autoc)
    return autoc

def parab_interpolation(data, xi, yi):
    """
    Interpolate a peak maximum position within a 2d-image
    using paraboloid approximation.
    
    For a given `data` array and given coordinates, perform
    a parabolic interpolation of the highest value within the 3x3
    pixel box centered at (xi, yi).
    
    .. math::
    
        z(x,y) = a_x (x-x0)^2 + a_y (y-y0)^2 + z0
    
    :param data: (ndarray) 2d-array containing the image data. 
    :param xi: (int) Index of the 3x3 interpolation box center.
    :param yi: (int) Index of the 3x3 interpolation box center. 
    :returns: (x0, y0, z0) Paraboloid center according to formula.
    """
    
    # get the maximum and the 4 neighbouring points 
    z1, z2, z3 = data[yi-1:yi+2,xi] #@UnusedVariable
    z4, z2, z5 = data[yi,xi-1:xi+2]
    
    # parabolic interpolation at point (xi, yi)
    x0 = (z5-z4)/(4*z2 - 2*z4 - 2*z5)
    y0 = (z3-z1)/(4*z2 - 2*z1 - 2*z3)
    z0 = z2 + (z1-z3)**2 / (16*z2-8*z1-8*z3) + (z4-z5)**2 / (16*z2-8*z4-8*z5)
    
    return xi+x0, yi+y0, z0

def npsavebz(fname, d):
    """
    Save a numpy array to a bz2 compressed file.
    
    :param fname: (str) Filename for saving.
    :param d: (ndarray) Array to be saved.
    """
    f = bz2.BZ2File(fname, "w")
    np.save(f, d)
    f.close()
    
def nploadbz(fname):
    """
    Load an array from a bz2 compressed numpy file.
    
    :param fname: (str) Filename to load the array from.
    :returns: (ndarray) Array loaded from file.
    """
    f = bz2.BZ2File(fname, "r")
    d = np.load(f)
    f.close()
    return d
    
def rotate(data, degrees):
    """
    .. note::
    
        This function is just an alias to :func:`scipy.ndimage.rotate` now.
    """
    return ndimage.rotate(data, degrees)

if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)
