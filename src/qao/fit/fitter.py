import numpy as np
import scipy.stats

import multiprocessing
from PyQt4 import QtCore

##########################################################################

# default values for approx jacobian
DELTA_REL = 1.5e-8
DELTA_ABS = 1.5e-8

DEFAULT_TYPE_NPY = np.double
DEFAULT_TYPE_C = "double"

class LevmarFitter(object):
    """
    Base fitter class implementing the Levenberg-Marquardt non-linear least squares algorithm.
    
    **Using fitters**
    
    Since all fitters are derived from this base class, the behavior is the same. You create
    an instance of a fitter for a specific dataset, run the :func:`fit` method, and retrieve
    the results using :func:`getFitPars`, :func:`getFitErr` and :func:`getFitData`.
    
    When processing multiple datasets, each having the same dimensions, you can reuse a fitter
    by setting new data using the :func:`setData` method.
    
    **Writing new fitters**
    
    The :class:`LevmarFitter` class must be subclassed for new fit model functions. For each
    new fitting class, you must provide the names for the fitting parameters and implement the
    methods calculating the fit model and guessing initial parameters.
    
    The Levenberg-Marquardt algorithm minimizes the distance between data points and the
    model function, which is to be implemented in the subclass. It does not care about positions
    or dimensionalities of the data points or the fit model, all it needs is a 1D array of
    residuals to minimize.
        
    First, you reimplement the :func:`__init__` method and provide the names for the fit parameters
    as simple list of strings when calling the parent constructor. This also determines the
    number of parameters at this point. The data argument is normally passed on to the parent
    constructor and determines the space to be allocated for computations.
    
    Second, you implement the methods :func:`f` and/or :func:`fJ`.
    The first function computes your function values for a given set of fit parameters,
    the second computes the function values and the jacobian. If only :func:`f` is given,
    the jacobian is approximated during the fit process, and you do not need to implement
    :func:`fJ`. If your implement :func:`fJ`, :func:`f` is not used by the fitter and you can
    expect a significant increase in performance, as you can optimize simultaneous calculation
    of f and J. Please refer to the method documentation for further implementation details.
    
    Third, you implement the :func:`guess` method. For implementation details, see method
    documentation.

    .. note::
    
        The constants `DEFAULT_TYPE_NPY` and `DEFAULT_TYPE_C` from :mod:`qao.fit.fitter` should be
        used to abstract the floating type for changing the precision if desired.
    
    :param par_names: (list) List of fit parameter names.
    :param data: (ndarray) Data to be fitted.
    
    This is a simple example subclass that implements a 1d gaussian
    fitter including a guess method::
        
        from qao.fit.fitter import LevmarFitter, DEFAULT_TYPE_NPY
        
        class GaussFitter(LevmarFitter):
            def __init__(self, data):
                LevmarFitter.__init__(self, ["A", "x0", "sigma"], data)
            
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
                A, x0, sig = pars
                x = np.arange(data.size, dtype = DEFAULT_TYPE_NPY)
                self._f[:] = A * np.exp(-1./2. * 1./sig**2 * (x-x0)**2)
            
            def fJ(self, pars):
                # for given set of pars, calculate the fit function...
                A, x0, sig = pars
                x = np.arange(data.size, dtype = DEFAULT_TYPE_NPY)
                self._f[:] = A * np.exp(-1./2. * 1./sig**2 * (x-x0)**2)
                
                # ...and the derivatives for the jacobian 
                self._J[0, :] = 1./A * self._f[:]
                self._J[1, :] = (x-x0)/sig**2 * self._f[:]
                self._J[2, :] = (x-x0)**2/sig**3 * self._f[:]                
    """
    def __init__(self, pars_name, data):
        """
        Provide parameter names and data for fitting. This will determine the
        amount of space allocated for computations and is not to be changed later.
        
        :param par_names: (list) List of fit parameter names.
        :param data: (ndarray) Data to be fitted.
        """
        self.pars_name = pars_name
        self.pars_fit = np.zeros(len(pars_name), dtype = DEFAULT_TYPE_NPY)
        self.data = np.asfarray(data, dtype = DEFAULT_TYPE_NPY)
        self._f = np.empty(self.data.size, dtype = DEFAULT_TYPE_NPY)
        self._J = np.empty([self.pars_fit.size, self._f.size], dtype = DEFAULT_TYPE_NPY)
        
        self.verbose = False
    
    def setVerbose(self, verbose):
        """
        Set fitter to verbose output. This will print the internal status for
        each iteration step.
        
        :param verbose: (bool) Enable/disable verbose output when fitting.
        """
        self.verbose = bool(verbose)
    
    def setData(self, data):
        """
        Change the data to be fitted. The shape of the data must not change. For
        fitting a dataset with different shape you need to create a new fitter
        instance.
        
        :param data: (ndarray) New data to be fitted.
        """
        data = np.asfarray(data, dtype = DEFAULT_TYPE_NPY)
        if self.data.shape != data.shape:
            raise ValueError("Shape mismatch. Expected dimensions %s." % self.data.shape) 
        self.data = data
    
    def fit(self, pars_guess = None, tau = 1e-2, eps1 = 1e-6, eps2 = 1e-6, kmax = 50, return_dict = False, callback = None):
        """
        Fit the data currently assigned to the fitter.
        
        If the fitting class implemented a guess function, you do not need to provide
        a initial guess of fit parameters. After completion, the best fit parameters
        are stored and returned. You can obtain the parameters using the methods
        :func:`getFitPars` and :func:`getFitDict` as well. Fitting details like the
        number of iterations and reason for stopping can be retrieved
        from :func:`getFitLog`.
        
        A callback function can be provided to monitor or cancel the fit process. It
        takes the iteration number as argument and must return a bool indicating if
        the fitter should continue its work.
        
        Simple callback function::
        
            def callback(k):
                print "Iteration at", k
                return True
        
        :param pars_guess: (ndarray) Start parameters for fitting. If None, guess from data.
        :param callback: (callable) Callback function.
        :returns: (ndarray) Fit parameters + optional fit dictionary.
        """
        if pars_guess is None:
            pars_guess = self.guess()
        
        if len(pars_guess) != len(self.pars_name):
            raise ValueError("Invalid number of guess parameters.")
        
        pars_fit, fit_dict = self.__LM(pars_guess, tau, eps1, eps2, kmax, verbose = self.verbose, return_dict = True, callback = callback)
        self.pars_fit[:] = self.sanitizePars(pars_fit)
        if return_dict:
            return self.pars_fit.copy(), fit_dict
        else:
            return self.pars_fit.copy()
    
    def sanitizePars(self, pars):
        """
        Postprocess parameters after fitting.
        
        Reimplement this function to sanitize parameters.        
        
        :param pars: (ndarray) Fit parameter results.
        :returns: (ndarray) Processed parameters.
        """
        return pars
    
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
           verbose = False, return_dict = False, callback = None):
        """Implementation of the Levenberg-Marquardt algorithm in pure
        Python. Solves the normal equations."""
        
        # if no callback was provided, provide simply True
        if callback is None:
            callback = lambda k: True
        
        # process control
        stop_reason = ""
        stop = False
        
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
        if np.linalg.norm(g, np.Inf) < eps1:
            stop = True
            stop_reason = "small gradient"

        while not stop and k < kmax and callback(k):
            k += 1
    
            try:
                d = np.linalg.solve( A + mu*I, -g)
            except np.linalg.LinAlgError:
                stop = True
                stop_reason = "singular matrix"
                break
    
            if np.linalg.norm(d) < eps2*(np.linalg.norm(pars) + eps2):
                stop = True
                stop_reason = "small step"
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
                if (np.linalg.norm(g, np.Inf) < eps1):
                    stop = True
                    stop_reason = "small gradient"
                    break
                mu = mu * max([1.0/3, 1.0 - (2*rho - 1)**3])
                nu = 2.0
            else:
                mu = mu * nu
                nu = 2*nu
    
            if verbose:
                print "step %2d: |f|: %9.6g mu: %8.3g rho: %8.3g" % (k, np.linalg.norm(self._f), mu, rho)
                
        else:
            if not stop_reason and k == kmax:
                stop_reason = "max iter reached"
            else:
                stop_reason = "user abort"
    
        if verbose:
            print stop_reason
        
        self.fit_log = {"iter": k,
                        "reason": stop_reason,
                        "success": stop_reason in ["small gradient", "small step"]}
        
        if return_dict:
            return pars, self.fit_log
        else:
            return pars

    def __estError(self, pars):
        """
        Calculate the estimated errors for best fit parameters.
        """
        self.fJ(pars)  # refresh f and J
        if self.data is not None: self._f -= self.data.ravel()
        
        alpha = 0.05            # 95%, 2sigma confidence limit
        N = self._f.size        # number of points
        m = len(pars)  # number of parameters
        
        errsq = np.linalg.norm(self._f)**2 # sum square residuum
        sigma = np.sqrt(errsq / (N - m))   # estimated standard deviation
        
        try:
            diag = np.diagonal(np.linalg.inv(np.inner(self._J, self._J)))
            pars_err = np.sqrt(diag) * sigma * scipy.stats.t.ppf(1 - alpha / 2, N - m)
        except:
            pars_err = pars * np.inf
            
        return pars_err
    
    def guess(self):
        """
        Determine a guess of fit parameters for given data.
        
        A good estimate of initial fit parameters is crucial for the fitting process.
        When subclassing, implement a method for guessing fit parameters for a given
        set of measurements `self.data`. Return set of parameters as defined in your
        implementation.
        
        :returns: (ndarray) Fit parameters guessed from data.
        """
        raise NotImplementedError("Fitter must be subclassed")
    
    def f(self, pars):
        """
        Calculate the model function for given parameters.
        
        .. note::
        
            This function is usually not called
            from the user directly.
        
        The function values are to be stored in the already allocated
        ndarray `self._f`. The array's size matches the size of `self.data`
        provided when instancing the fitter, although it is flattened.
        If the shape of data is (height, width) the shape of `self._f` is
        height*width.
        
        Implementing this function is not necessary if :func:`fJ` is
        already implemented.

        :param pars: (ndarray) Fit parameters.
        """
    
    def fJ(self, pars):
        """
        Calculate the model function and the jacobian for given parameters.
        
        .. note::
        
            This function is usually not called
            from the user directly.
       
        The function values are to be stored in the already allocated
        ndarrays `self._f` and `self._J`. If the number of fit
        parameters is `k` and the number of data points is `n`,
        the shape of `self._f` is (n,) and the shape of `self._J`
        is(k, n). The first row of the jacobian holds all points of
        the function derived by the first fit parameter, the n'th row
        the derivative of the n'th fit parameter.
        
        If you can not or do not want to implement this function you
        may implement :func:`f` instead, and the jacobian will be
        approximated.

        :param pars: (ndarray) Fit parameters.
        """
    
        self.__JACapprox(pars)
        self.f(pars)
    
    def getFitParNames(self):
        """
        Return the names of the fit parameters.
        
        :returns: ([str]) List of strings containing the parameter names.
        """
        return self.pars_name
    
    def getFitPars(self):
        """
        Return the best fit parameter values as array.
        
        The order of the parameters is determined by the implementation
        and fixed. If you do not know the order, refer to :func:`getFitParsDict`
        or :func:`getFitParNames`.
        
        :returns: (ndarray) Best fit parameters.
        """
        return self.pars_fit
    
    def getFitErr(self):
        """
        Return the estimated errors of the best fit parameters.
        
        The order of the errors matches the order of the parameters
        ans is determined by the implementation. If you do not know
        the order, refer to :func:`getFitParsDict` or
        :func:`getFitParNames`.
        
        :returns: (ndarray) Best fit parameters.
        """
        return self.__estError(self.pars_fit)        
    
    def getFitParsDict(self, errors = True):
        """
        Return the best fit parameters as dictionary.
        
        The dictionary will contain the names of the fit
        parameters, their estimated best fit values and
        the estimated error of the parameter (unless you
        decide not to include estimated errors).
        
        :param errors: (bool) Include estimated errors.
        :returns: (dict) Best fit parameters.
        """
        if errors: pars_err = self.getFitErr()
        
        result = dict()
        for i, name in enumerate(self.pars_name):
            result[name] = self.pars_fit[i]
            if errors: result[name+"_err"] = pars_err[i]
        
        return result
    
    def getFitLog(self):
        """
        Return details from the fitting iteration. The result
        is a dictionary including the following information:
        
        =======   ==============================
        Name      Description
        =======   ==============================
        iter      Number of iterations.
        reason    Reason for stopping the fit ("small gradient", "small step", "singular matrix").
        =======   ==============================
        
        :returns: (dict) Fit procedure details.
        """
        return self.fit_log
    
    def getFitData(self, pars = None):
        """
        Calculate and return the data from the fitting function.
        
        If `pars` is None, return the data of the best fit function
        determined from the last successful fit run. You can also
        use this function to calculate the fit function for any
        other set of parameters if provided.
        
        :param pars: (ndarray) Fit function parameters or None. 
        :returns: (ndarray) Fit function data.
        """
        # return a reshaped copy of f(pars)
        if pars is None:
            pars = self.pars_fit
        if len(pars) != len(self.pars_name):
            raise ValueError("Invalid number of guess parameters.")
        pars = np.asfarray(pars, dtype = DEFAULT_TYPE_NPY)
        self.fJ(pars)
        return self._f.copy().reshape(self.data.shape)

class FitJob(QtCore.QObject):
    """
    Class for running a fit in a multiprocess environment.
    
    By using the python `multiprocessing` module, a fit can be executed within a
    seperate process for parallel processing. The FitJob class is derived from
    QObject and signals the completion of a fit by emitting the `fitFinished` signal.
    
    Example::
    
        fitter = Gauss2D(data)
        job = FitJob()
        job.fitFinished.connect(callbackFunction)
        job.startFit(fitter)
    """
    
    fitFinished = QtCore.pyqtSignal()
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.process = multiprocessing.Process(target = self.__run)
    
    def startFit(self, fitter):
        """
        Run the `fit` method of a fitter in a seperate process.
        
        The status of the running process can be checked by :func`isRunning`.
        When the fit procedure finishes, the `fitFinished` signal will be
        emitted and the fitter object will contain the results.
        
        :param fitter: Fitter instance.
        """
        if self.process.is_alive():
            raise RuntimeError("fit already running")
        self.fitter = fitter
        self.process = multiprocessing.Process(target = self.__run)
        self.queue = multiprocessing.Queue()
        self.process.start()
        self.timerId = self.startTimer(20)
    
    def isRunning(self):
        """
        Return the status of a fit job.
        
        :returns: (bool) True if a job is currently working.
        """
        return self.process.is_alive()
    
    def __run(self):
        pars = self.fitter.fit()
        self.queue.put(pars)
    
    def timerEvent(self, event):
        if self.process.is_alive(): return
        self.killTimer(self.timerId)
        self.fitter.pars_fit[:] = self.queue.get()
        self.fitFinished.emit()