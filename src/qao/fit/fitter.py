import numpy as np

##########################################################################

# default values for approx jacobian
DELTA_REL = 1.5e-8
DELTA_ABS = 1.5e-8

DEFAULT_TYPE_NPY = np.double
DEFAULT_TYPE_C = "double"

class Fitter(object):
    """
    Base class for fitting data.
    Fitter should be subclassed for new fit model functions.
    
    :param par_names: (list) List of fit parameter names.
    :param data: (ndarray) Data to be fitted.
    """
    def __init__(self, pars_name, data):
        self.pars_name = pars_name
        self.pars_fit = np.zeros(len(pars_name), dtype = DEFAULT_TYPE_NPY)
        self.data = np.asfarray(data, dtype = DEFAULT_TYPE_NPY)
        self._f = np.empty(self.data.size, dtype = DEFAULT_TYPE_NPY)
        self._J = np.empty([self.pars_fit.size, self._f.size], dtype = DEFAULT_TYPE_NPY)
        
        self.verbose = False
    
    def setData(self, data):
        """
        Change the data to be fitted. The shape of data must not change.
        """
        data = np.asfarray(data, dtype = DEFAULT_TYPE_NPY)
        if self.data.shape != data.shape:
            raise ValueError("Shape mismatch. Expected dimensions %s." % self.data.shape) 
        self.data = data
    
    def fit(self, pars_guess = None):
        """
        Run a fit to the given data.
        :param par_guess: (ndarray) Start parameters for fitting. If None, guess from data.  
        """
        if pars_guess is None:
            pars_guess = self.guess()
        
        pars_fit = self.__LM(pars_guess, verbose = self.verbose)
        self.pars_fit[:] = pars_fit[:]
        return pars_fit
    
    def __JACapprox(self, pars):
        
        pars = np.asfarray(pars, dtype = DEFAULT_TYPE_NPY).copy()
        
        for i in range(pars.size):
            delta = max(DELTA_ABS, DELTA_REL*abs(pars[i]))
            pars[i] += delta
            self.f(pars)
            self._J[i, :] = self._f.ravel()
            pars[i] -= 2*delta
            self.f(pars)
            self._J[i, :] -= self._f.ravel()
            self._J[i, :] *= 1./(2*delta)
    
    def __LM(self, pars, tau = 1e-2, eps1 = 1e-6, eps2 = 1e-6, kmax = 50,
           verbose = False):
        """Implementation of the Levenberg-Marquardt algorithm in pure
        Python. Solves the normal equations."""
        
        # get pars, create cache
        pars = np.asfarray(pars, dtype = DEFAULT_TYPE_NPY)
        
        # calculate f and J
        self.fJ(pars)
        if self.data is not None: self._f -= self.data.ravel()
        
        A = np.inner(self._J, self._J)
        g = np.inner(self._J, self._f)
        I = np.eye(pars.size)
    
        k = 0; nu = 2
        mu = tau * max(np.diag(A))
        stop = np.linalg.norm(g, np.Inf) < eps1
        while not stop and k < kmax:
            k += 1
    
            try:
                d = np.linalg.solve( A + mu*I, -g)
            except np.linalg.LinAlgError:
                print "Singular matrix encountered in LM"
                stop = True
                reason = 'singular matrix'
                break
    
            if np.linalg.norm(d) < eps2*(np.linalg.norm(pars) + eps2):
                stop = True
                reason = 'small step'
                break
    
            pars_new = pars + d
            errsq = np.linalg.norm(self._f)**2
            
            # recalculate f and J for new pars
            self.fJ(pars_new)
            if self.data is not None: self._f -= self.data.ravel()
            
            errsq_new = np.linalg.norm(self._f)**2
            rho = (errsq - errsq_new)/np.inner(d, mu*d - g)
            if rho > 0:
                pars = pars_new
                A = np.inner(self._J, self._J)
                g = np.inner(self._J, self._f)
                if (np.linalg.norm(g, np.Inf) < eps1): # or norm(fnew) < eps3):
                    stop = True
                    reason = "small gradient"
                    break
                mu = mu * max([1.0/3, 1.0 - (2*rho - 1)**3])
                nu = 2.0
            else:
                mu = mu * nu
                nu = 2*nu
    
            if verbose:
                print "step %2d: |f|: %9.6g mu: %8.3g rho: %8.3g"%(k, np.linalg.norm(self._f), mu, rho)
    
        else:
            reason = "max iter reached"
    
        if verbose:
            print reason
        
        self.fit_log = {"iter": k, "reason": reason}
        
        return pars
    
    def guess(self):
        """
        Determine a guess of fit parameters for given data.
        """
        raise NotImplementedError("Fitter must be subclassed")
    
    def f(self, pars):
        """
        Calculate the model function for given parameters.
        :param pars: (ndarray) Fit parameters.
        """
    
    def fJ(self, pars):
        """
        Calculate the model function and the jacobian for given parameters.
        :param pars: (ndarray) Fit parameters.
        """
        self.__JACapprox(pars)
        self.f(pars)
    
    def getFitPars(self):
        """
        Return the best fit parameter values as array.
        """
        return self.pars_fit
    
    def getFitDict(self):
        """
        Return the best fit parameters as dictionary.
        """
        return dict(zip(self.pars_name, self.pars_fit))

    