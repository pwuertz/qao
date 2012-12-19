from qao.fit.fitter import LevmarFitter, DEFAULT_TYPE_NPY
import numpy as np

class ExpDecayOffs(LevmarFitter):
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
        return np.asfarray([amp, x0, 0], dtype = DEFAULT_TYPE_NPY)

    def fJ(self, pars):
        # for given set of pars, calculate the fit function...
        A, tau, off = pars
        x = np.arange(self.data.size, dtype = DEFAULT_TYPE_NPY)
        self._f[:] = A * np.exp(-x/tau)+off
        
        # ...and the derivatives for the jacobian 
        self._J[0, :] = 1/A *(self._f[:]-off)
        self._J[1, :] = x/(tau)**2  * (self._f[:]-off)
        self._J[2, :] = 1

class ExpDecay(LevmarFitter):
    def __init__(self, data):
        LevmarFitter.__init__(self, ["A", "tau"], data)
    
    def guess(self):
        # determine maximum value
        data = self.data
        amp  = np.max(data)
        # calculate mean and variance
        dsum = np.sum(data)
        x0  = (np.arange(data.size) * data).sum() * (1./dsum)
        var = ((np.arange(data.size)-x0)**2 * data).sum() * (1./dsum)
        # return guess
        return np.asfarray([amp, x0], dtype = DEFAULT_TYPE_NPY)

    def fJ(self, pars):
        # for given set of pars, calculate the fit function...
        A, tau = pars
        x = np.arange(self.data.size, dtype = DEFAULT_TYPE_NPY)
        self._f[:] = A * np.exp(-x/tau)
        
        # ...and the derivatives for the jacobian 
        self._J[0, :] = 1/A *(self._f[:])
        self._J[1, :] = x/(tau)**2  * (self._f[:])

if __name__ == "__main__":
        
    def expdec(x, pars):
        A, tau, off = pars        
        return A * np.exp(-x/tau) + off


    n = 250
    X = np.linspace(0,n,n)
    
    pars_org = np.asfarray([10,5,0])
    
    data_org = expdec(X,  pars_org)
        
    fitter = ExpDecay(data_org)
    fitter.verbose = False
    pars_ini = fitter.guess()
    data_ini = expdec(X, pars_ini)
    pars_fit = fitter.fit(pars_ini)
    print pars_fit
    print  fitter.getFitLog()
    data_fit = expdec(X, pars_fit)
    
    """
    #print pars_fit
    print "alpha: %.2f"%(fitter.getFitParsDict()['alpha']*180/np.pi)
    print "sx: %.2f"%fitter.getFitParsDict()['s_x']
    print "sy: %.2f"%fitter.getFitParsDict()['s_y']
    """
    
    import pylab as p
    
    p.plot(data_org,label="orig")
       
    p.plot(data_ini,label="init")
    
    p.plot(data_fit,label="fit")
    p.legend()
    p.show()
