"""
Utility functions
=================
"""

import os, bz2
import numpy as np
from PyQt4 import QtCore, QtGui
from scipy import ndimage

def drawPolygonMask(width, height, points):
    """
    Draw a convex polygon defined by points into a numpy array.
    The pixel value inside the polygon is 1.0, else 0.0.   
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
    Length is a measure of spreading (0 = full spread).
    Returns [mean, length]
    """
    angle_list = np.array(angle_list_rad)
    xmean = np.cos(angle_list).sum()
    ymean = np.sin(angle_list).sum()
    phi_mean = np.arctan2(ymean,xmean)
    rel_length = np.sqrt(xmean**2+ymean**2) / len(angle_list)
    return [phi_mean, rel_length]

def angle_mean_deg(angle_list_deg):
    """
    Calculate the mean angle from a list of angles in degrees.
    Length is a measure of spreading (0 = full spread).
    Returns [mean, length]
    """
    angle_list_rad = np.array(angle_list_deg) * np.pi / 180
    phi_rad, rel_length = angle_mean(angle_list_rad)
    return [phi_rad * 180. / np.pi, rel_length]

def angle_mean_std(angles_rag):
    """
    Calculate the mean angle and the standard deviation from a
    list of angles in radians.
    Returns [mean, std]
    """
    angles_rag = np.asfarray(angles_rag)
    mean_angles = np.angle(np.exp(1j*angles_rag).sum())
    std_angles  = np.std((((angles_rag - mean_angles) + np.pi) % (2*np.pi)) - np.pi)
    return mean_angles, std_angles

def findMostFrequent(data):
    """
    finds the most frequent element in a list
    returns tuple (element, number of occurrences)
    """
    
    if not isinstance(data, np.ndarray):
        try:
            data = np.array(data)
        except:
            print "Error converting data to numpy array"
    elements = np.unique(data)
    haufigkeit = [(data==i).sum() for i in elements]
    index = haufigkeit.index(max(haufigkeit))
    return (elements[index],max(haufigkeit))

def add(array1, array2):
    """
    adds two arrays of different shape.
    returns array with shape=(max(height1,height2),max(width1,width2))
    
    Example:
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
    move all pixels by pixels_x to the left (-x) and pixels_y upwards (-y)
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
    Rebin a numpy array d. The length of the output array will be d.size/binsize. 
    """
    if d.size % binsize != 0: raise Exception('invalid binsize')
    d = d.reshape([d.size/binsize, binsize])
    return d.sum(axis=1)

def autocorr2d_sum(data_list):
    """
    Calculate the 2d autocorrelation of each numpy 2d-array in data_list.
    Return the sum of all autocorrelations.
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
    Calculate the center of a paraboloid defined at (xi,yi).
    z(x,y) = ax(x-x0)^2 + ay(y-y0)^2 + z0
    
    Returns: x0, y0, z0
    """
    
    # get the maximum and the 4 neighbouring points 
    z1, z2, z3 = data[yi-1:yi+2,xi]
    z4, z2, z5 = data[yi,xi-1:xi+2]
    
    # parabolic interpolation at point (xi, yi)
    x0 = (z5-z4)/(4*z2 - 2*z4 - 2*z5)
    y0 = (z3-z1)/(4*z2 - 2*z1 - 2*z3)
    z0 = z2 + (z1-z3)**2 / (16*z2-8*z1-8*z3) + (z4-z5)**2 / (16*z2-8*z4-8*z5)
    
    return xi+x0, yi+y0, z0

def npsavebz(fname, d):
    """
    Save a numpy array to a bz2 compressed file. 
    """
    f = bz2.BZ2File(fname, "w")
    np.save(f, d)
    f.close()
    
def nploadbz(fname):
    """
    Load an array from a bz2 compressed numpy file. 
    """
    f = bz2.BZ2File(fname, "r")
    d = np.load(f)
    f.close()
    return d
    
def rotate(data, degrees):
    return ndimage.rotate(data, degrees)

if __name__ == "__main__":
  import doctest
  doctest.testmod(verbose=True)
