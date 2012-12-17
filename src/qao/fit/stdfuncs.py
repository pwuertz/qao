from qao.fit.fitter import LevmarFitter, DEFAULT_TYPE_NPY

class ExpDecay(LevmarFitter):
    def __init__(self, data):
        LevmarFitter.__init__(self, ["A", "tau", "off"], data)
    
    def guess(self):
        # determine maximum value
        data = self.data
        amp  = np.max(data)
        # calculate mean and variance
        dsum = np.sum(data)
        x0  = (np.arange(data.size) * data).sum() * (1./dsum)
        var = ((np.arange(data.size)-x0)**2 * data).sum() * (1./dsum)
        # return guess
        return np.asfarray([dmax, x0, np.sqrt(var)], dtype = DEFAULT_TYPE_NPY)
    
    def f(self, pars):
        # for given set of pars, calculate the fit function
        A, tau, off = pars
        x = np.arange(data.size, dtype = DEFAULT_TYPE_NPY)
        self._f[:] = A * np.exp(-x/tau)+off
    
    def fJ(self, pars):
        # for given set of pars, calculate the fit function...
        A, tau, off = pars
        x = np.arange(data.size, dtype = DEFAULT_TYPE_NPY)
        self._f[:] = A * np.exp(-1./2. * 1./sig**2 * (x-x0)**2)
        
        # ...and the derivatives for the jacobian 
        self._J[0, :] = -1/tau * self._f[:]
        self._J[1, :] = 1/tau**2 * self._f[:]
        self._J[2, :] = -1/tau**3 * self._f[:]   
