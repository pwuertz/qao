r"""
Fast fitting routines
========================

The tools for fitting data in this module are optimized for speed and ease of use.
Generally, you create an instance of a desired fitter implementing a specific fit
function and let the fitter simply guess and fit your data.

There is a small collection of fitters already available in :mod:`qao.fit.gauss`,
which can be also imported from :mod:`qao.fit`.

* :class:`qao.fit.gauss.Gauss1D`
* :class:`qao.fit.gauss.Gauss2D`
* :class:`qao.fit.gauss.Gauss2DRot`

An already instanced fitter can be reused to fit another set of data. This can
seed up batch-processing larger amounts of data. The number of measurements within
each dataset must be constant though.

For implementing new fit function please refer to the base class documentation
:class:`qao.fit.fitter.LevmarFitter`.

This is a simple example how to use the fitting routines from this module.
A gaussian function with additional noise is generated and fitted. The results
are printed and plotted afterwards::

    import pylab as p
    import numpy as np
    import qao.fit
    
    # create data
    x = np.arange(100, dtype = float)
    y = np.exp(-x**2/(2.*30.**2)) + .1*np.random.rand(100)
    
    # fit data
    fitter = qao.fit.Gauss1D(y)
    pars_fit = fitter.fit()
    
    # get results
    pars_name  = fitter.getFitParNames()
    pars_fit   = fitter.getFitPars()
    pars_error = fitter.getFitErr()
    for row in zip(pars_name, pars_fit, pars_error):
        print "%s\t%.3f +/- %.3f" % row
    
    # plot results
    y_fit = fitter.getFitData()
    p.plot(x, y, "b.")
    p.plot(x, y_fit, "r-")
    p.show()

.. automodule:: qao.fit.fitter
.. automodule:: qao.fit.gauss

"""

from gauss import Gauss1D, Gauss2D, Gauss2DRot

if __name__ == '__main__':
    import pylab as p
    import numpy as np
    import qao.fit
    
    # create data
    x = np.arange(100, dtype = float)
    y = np.exp(-x**2/(2.*30.**2)) + .1*np.random.rand(100)
    
    # fit data
    fitter = qao.fit.Gauss1D(y)
    fitter.fit()
    
    # print results
    par_names = fitter.getFitParNames()
    par_value = fitter.getFitPars()
    par_error = fitter.getFitErr()
    for row in zip(par_names, par_value, par_error):
        print "%s\t%.3f +/- %.3f" % row
    
    # plot results
    y_fit = fitter.getFitData()
    p.plot(x, y, "b.")
    p.plot(x, y_fit, "r-")
    p.show()