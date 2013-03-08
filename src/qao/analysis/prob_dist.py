"""
Probability Distributions
-----------------------------

"""

import numpy as np
from PyQt4 import QtCore, QtGui

class WithoutHistogram:
    """
    When one deals with data drawn from continuous variables, a histogram is
    often inadequate to display their probability density. It deals inefficiently
    with statistical noise, and binsizes are free parameters. In contrast to that,
    an approximation from the empirical cumulative distribution function is
    parameter free.
    
    This class is an implementation of the method presented by Berg et al. in 
    `From data to probability densities without histograms <http://dx.doi.org/10.1016/j.cpc.2008.03.010>`_.
    
    After creating an instance of this class, passing the values to be non-histogrammed,
    you can use the instance like a function and evaluate the estimated density distribution
    within the data interval.
    
    :param X: (ndarray) List of points in x.
    :param Y: (ndarray) Optional weight of each x-point.
    
    Example:
    
    .. literalinclude:: ../src/qao/analysis/prob_dist.py
        :pyobject: test_withoutHistogram
    
    """
    
    def __init__(self, X, Y=None):
        # X must be a sorted array
        X = np.asfarray(X)
        ind = X.argsort()
        X = X[ind]
        # calculate CDF from X, or XY
        if Y == None:
            cdf = np.arange(1, X.size + 1, dtype=float) * (1. / X.size)
        else:
            Y = Y[ind]; cdf = np.cumsum(Y, dtype=float); cdf /= cdf.max()
        # store input
        self.X = X
        self.cdf = cdf
        # approximation still todo
        self._approxDict = None
        
    def _kolmogorovMagic(self, delta):
        n = self.X.size
        a = -2 * (n ** .5 * delta + 12.*delta / 100. + 11.*delta / 100. / np.pi ** .5) ** 2
        i = np.arange(1, 101)
        Q = (2 * (-1) ** (i - 1) * np.exp(a * i ** 2)).sum()
        return Q

    def approx(self, order_max=20, q_threshold=0.6):
        """
        Approximate a density distribution from the given data.
        
        This method calculates the estimated distribution function and
        returns True if a solution was found. The `order_max` parameter
        may be increased to allow for finer structures, although the
        default of 20 should provide reasonable results.
        
        The method will be executed automatically if required.
        
        :param order_max: (int) Max Fourier-order for approximation.
        :param q_threshold: (float) Threshold for accepting the Kolmogorov criterion.
        :returns: (boolean) Success.
        """
        # ecdf
        X = self.X
        ecdf = (X - X[0]) / (X[-1] - X[0])
        R = self.cdf - ecdf
        
        # map X to [0,1]
        L = X[-1] - X[0]
        XN = (X - X[0]) * (1. / L)
        
        # calculate dx-es for non uniform sampling
        dx = np.empty_like(XN)
        dx[1:-1] = .5 * (XN[2:] - XN[:-2])
        dx[0] = 0.5 * (XN[1] - XN[0]); dx[-1] = 0.5 * (XN[-1] - XN[-2])
        
        # fourier approx up to order_max   
        self._approxDict = {"coeffs": []}
        for m in range(1, order_max + 1):
            coeff = 2 * (dx * R * np.sin(m * np.pi * XN)).sum()
            ecdf += coeff * np.sin(m * np.pi * XN)
            self._approxDict["coeffs"].append((m, coeff))
            # kolmogorov test
            D = np.abs(self.cdf - ecdf).max()
            Q = self._kolmogorovMagic(D)
            if Q > q_threshold:
                self._approxDict["Q"] = Q
                return True
        
        self._approxDict["Q"] = Q
        return False
    
    def __call__(self, x):
        """
        Return estimated probability distriburion at `x`.
        
        :param x: (ndarray) Calculate distribution for these points.
        :returns: (ndarray) Estimated probability distribution.
        """
        if not self._approxDict: self.approx()
        L = (self.X[-1] - self.X[0])
        xn = (x - self.X[0]) / L
        
        df = np.ones(len(x), dtype=float) * (1. / L)
        for m, coeff in self._approxDict["coeffs"]:
            df += m * np.pi * coeff / L * np.cos(m * np.pi * xn)

        return df 

def test_withoutHistogram():
    import pylab as p
    import scipy.stats
    
    # create normal distribution of points
    norm = scipy.stats.norm()
    X = norm.rvs(size=100)
    
    # approximate the distribution
    wh = WithoutHistogram(X)
    print "Success: %s" % wh.approx(q_threshold=0.7)
    print "Q reached: %f, max order: %d" % (wh._approxDict["Q"],
                                            len(wh._approxDict["coeffs"]))
    
    # plot the approximated distribution
    xf = np.linspace(X.min(), X.max(), 500)
    p.plot(xf, wh(xf), "-")
    p.hist(X, 20, normed=True)
    p.show()

if __name__ == '__main__':
    test_withoutHistogram()
