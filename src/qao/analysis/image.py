"""
Image
---------

Provides basic functions for analyzing 2d images.

The functions in this module are designed for general image analysis.
For specialized functions, i.e. lattice analysis, have a look at the
other :mod:`qao.analysis` modules as well.
"""


import numpy as np

def imageMoments(data, X = None, Y = None):
    """Calculate characteristic bivariate moments of an image.  
    
    The image is interpreted as 2-dimensional probability distribution, not
    necessarily normalized to one. If X and Y coordinates are not provided,
    the coordinates are assumed to be evenly spaced by one pixel.
    
    :param data: (ndarray) Image data, a 2d numpy array.
    :param X: (ndarray) Optional array of x-coordinates.
    :param Y: (ndarray) Optional array of y-coordinates.  
    :returns: (dict) Dictionary containing bivariate moments.
    
    The following quantities are calculated and returned as dictionary

    =====   ==============================
    Name    Description
    =====   ==============================
    gv      generalized variance
    b22     bivariate kurtosis
    rv      relative variance
    rk      relative kurtosis
    mx      center x
    my      center y
    mu11    central moment (1, 1)
    mu20    central moment (2, 0)
    mu02    central moment (0, 2)
    =====   ==============================
    
    An interpretation of the values gv, b22, rv, rk can be found in
    http://dx.doi.org/10.1088/0026-1394/42/5/003
    
    For example, the orientation of a density distribution may be
    determined from the central moments:
    
    .. literalinclude:: ../src/qao/analysis/image.py
        :pyobject: test_orientation
    """
    
    data = np.asfarray(data)
    data = data * (1./data.sum())
    if X == None: X = np.arange(data.shape[1], dtype = float)
    if Y == None: Y = np.arange(data.shape[0], dtype = float)
    X = np.asfarray(X).reshape([1, data.shape[1]])
    Y = np.asfarray(Y).reshape([data.shape[0], 1])
    
    # calculate center
    mx = (X*data).sum()
    my = (Y*data).sum()
    Xc = X - mx 
    Yc = Y - my
    
    # calculate central moments
    mu11 = (Xc * Yc * data).sum()
    mu20 = (Xc**2 * data).sum()
    mu02 = (Yc**2 * data).sum()
    mu22 = (Xc**2 * Yc**2 * data).sum()
    mu31 = (Xc**3 * Yc * data).sum()
    mu13 = (Xc * Yc**3 * data).sum()
    mu40 = (Xc**4 * data).sum()
    mu04 = (Yc**4 * data).sum()
    
    # calculate derived quantities
    sigx = mu20**.5; sigy = mu02**.5
    ga40 = mu40/sigx**4; ga04 = mu04/sigy**4
    ga31 = mu31/sigx**3/sigy; ga13 = mu13/sigx/sigy**3
    ga22 = mu22/sigx**2/sigy**2
    rhoxy = mu11/sigx/sigy
    
    # bivariate varianve
    gv = mu20*mu02 - mu11**2
    # bivariate kurtosis
    b22 = (ga40 + ga04 + 2*ga22 + 4*rhoxy*(rhoxy*ga22-ga13-ga31)) / (1-rhoxy**2)**2
    # relative univariate variance difference
    rv = abs(mu20 - mu02) / min(mu20, mu02)
    # relative univariate kurtosis difference
    rk = abs(ga40 - ga04) / min(ga40, ga04)
    
    return dict(gv=gv, b22=b22, rv=rv, rk=rk, mx=mx, my=my,
                mu11=mu11, mu20=mu20, mu02=mu02)


def test_orientation():
    # gaussian test parameters
    n = 400
    sx, sy = 50., 10.
    x0, y0 = 200., 200.
    alpha  = 51 * np.pi / 180.
    
    # calculate distribution
    Y, X = np.ogrid[:n:1.,:n:1.]    
    Xr = np.sin(alpha) * (Y-y0) + np.cos(alpha) * (X-x0)
    Yr = -np.sin(alpha) * (X-x0) + np.cos(alpha) * (Y-y0) 
    data = np.exp(- Xr**2 / (2*sx**2) - Yr**2 / (2*sy**2))
    
    # measure statistic moments
    moments = imageMoments(data)
    mu11, mu20, mu02 = moments["mu11"], moments["mu20"], moments["mu02"]
    
    # calculate angle from statistic moments
    alpha_m = .5*np.arctan2(2.*mu11, (mu20-mu02))
    print "gaussian distribution, with angle %.1fdeg" % (alpha*180./np.pi)
    print "determined angle %.1fdeg" % (alpha_m*180./np.pi)

if __name__ == '__main__':
    test_orientation()
    