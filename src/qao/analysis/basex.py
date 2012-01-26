"""
Basis Set Expansion 
--------------------

The BAsis Set Expansion (BASEX) method is a way of approximating an unknown
function using a fixed number of known functions. The method determines
the basis set coefficients that approximate the unknown function best. Using
known functions may provide an easy way to perform analysis and transformations. 
It was shown that the method is very useful for inverse abel transformations
http://link.aip.org/link/?RSINAK/73/2634/1 .

Typically a simple function with varying parameter is used to build the basis
set, but the method does not limit the choice of the functions in any way.
Also the number of functions may be varied, although it is fixed to the number
of points to approximate in most applications. Another parameter is the
regulatization parameter 'q' that affects the approximation. You may want
to play around with it for optimal results, but q=1e-3 seems to be a good
initial choice.

A key feature of the BASEX is the way the basis coefficients are calculated.
You can analyze multiple datasets without recalculating the basis if the size is
fixed, which makes this method very fast.
"""

import numpy as np

class RadialGaussBasex:
    """
    Create a BASEX analyzer based on gaussian functions for
    radial function analysis.
    
    This class implements the BASEX method by using 1d gauss functions
    with varying width as basis set. All functions are centered at zero,
    so it works best for functions with high amplitude at zero and that
    are vanishing for large distances.
    
    An inverse abel transofmation is also implemented by using the
    BASEX coefficients from abel integrated data.
    
    :param nr: (int) Number of points to analyze.
    :param dr: (float) Distance between points to analyze
    :param q: (float) Regularization parameter.
    
    Example::
    
        # some measured abel transformed data
        data = ...
        
        # try to reconstruct function from data 
        basex = RadialGaussBasex(nr=data.size, q=1e-3)
        coeffs = basex.analyze(data)
        data_basex = basex.synthesize(coeffs)
        data_basex_inv = basex.synthesizeInvAbel(coeffs)
    
    For another example see the :func:`test_basex` method in :mod:`qao.analysis.basex`.
    """
    
    def __init__(self, nr, dr=1.0, q = 1e-3):
        # array for radial position values
        r = np.arange(nr, dtype=float) * dr
        r = r.reshape([r.size, 1])
        # array for basis function indices
        nk = r.size-1
        k  = np.arange(1, nk+1).reshape([1, nk])
        # calculate basis functions
        sig_step = 1./r.size * np.max(r)
        sig = sig_step * k
        self.sig   = sig
        self.basis = np.exp(-r**2 / (2*(sig)**2))
        
        # calculate the basis expansion matrix
        B = self.basis
        A = np.dot(B, B.transpose()) + q*np.eye(nr)
        A = np.dot(B.transpose(), np.linalg.inv(A))
        
        self.expansionMatrix = A
        self.nk = nk
        self.nr = nr
    
    def analyze(self, data):
        """
        Determine the BASEX coefficients for `data`.
        
        The data is assumed to be a linear spaced unknown function f(x),
        with the first point being at r=0. The number of points and
        the spacing is given by the parameters when instancing the class.
        
        The approximation of the unknown function is calculated by
        :func:`synthesize`.
        
        :param data: (ndarray) Data to be approximated.
        :returns: (ndarray) BASEX coefficients.
        """
        f = data.reshape([self.nr, 1])
        C = np.dot(self.expansionMatrix, f)
        return C.ravel()
    
    def synthesize(self, coeffs):
        """
        Reconstruct an approximated function from coefficients.
        
        Calculate and return the approximated function from coefficients
        determined by the :func:`analyze` method.
        
        :param coeffs: (ndarray) Array of coefficients for this basis.
        :returns: (ndarray) Reconstructed function.
        """
        B = self.basis
        f = np.dot(B, coeffs.reshape([self.nk, 1]))
        return f.ravel()

    def synthesizeInvAbel(self, coeffs):
        """
        Reconstruct the inverse abel transformation from coefficients.
        
        For an BASEX approximated unknown function, calculate the inverse
        abel transformation from coefficients.
        
        :param coeffs: (ndarray) Array of coefficients for this basis.
        :returns: (ndarray) Reconstructed inverse abel function.
        """
        # for inverse gaussian abel, we just have to change
        # the weights of the coefficients
        coeffs = coeffs * 1./np.sqrt(2*np.pi)/self.sig
        return self.synthesize(coeffs)


def test_basex():
    import pylab as p
    from matplotlib.gridspec import GridSpec
    
    # generate a radial test function
    n = 300
    Y, X = np.ogrid[-1.:1.:1j*n, 0.:1.:1j*n/2]
    dx, dy = X[0,1]-X[0,0], Y[1,0]-Y[0,0]
    R = np.sqrt(X**2 + Y**2)
    normal = lambda x, sig, amp: amp*np.exp(-.5*x**2/sig**2)
    radial_func = lambda r: normal(r, .25, 4.0) - normal(r, .1, 1.0)*(4*np.sin(r*30))
    
    # generate data from function
    data_2d = radial_func(R) + (np.random.random(R.shape)-.5)*1.0
    data_r = (radial_func(X)).ravel()
    data_abel = data_2d.sum(axis=0) * dy
    
    # try to guess data_r from data_abel
    basex = RadialGaussBasex(nr=data_abel.size, dr=dx, q=1e-3)
    coeffs = basex.analyze(data_abel)
    data_abel_s = basex.synthesize(coeffs)
    data_r_s = basex.synthesizeInvAbel(coeffs)
    
    #p.imshow(function_2d)
    x = X.ravel()
    p.figure(figsize=(10,7))
    gs = GridSpec(2, 2)
    gs.update(hspace=.4)
    ax = p.subplot(gs[0,0])
    ax.set_axis_off()
    ax.set_title("2d data from radial-func")
    ax.imshow(np.hstack((data_2d[:,::-1], data_2d)))
    
    ax = p.subplot(gs[0,1])
    ax.set_title("y-integrated data")
    ax.plot(x, data_abel, "k-", label="data")
    ax.plot(x, data_abel_s, "r-", label="basex")
    ax.set_xlabel("x position")
    ax.set_ylabel("line density")
    ax.set_ylim(ymin=0)
    ax.legend()
    
    ax = p.subplot(gs[1,0:2])
    ax.set_title("inverse abel transformation from basex coefficients")
    ax.plot(x, data_r, "b-", label="original function")
    ax.plot(x, data_r_s, "r-", label="inverse abel")
    ax.set_xlabel("radius")
    ax.set_ylabel("density")
    ax.legend()
    p.show()

if __name__ == '__main__':
    test_basex()