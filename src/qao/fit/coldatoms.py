import numpy as np
import scipy.weave as weave
from scipy.special import erf
from scipy.ndimage import rotate
from fitter import LevmarFitter, DEFAULT_TYPE_C, DEFAULT_TYPE_NPY
from gauss import Gauss1D

__compiler_args = ["-O3", "-march=native", "-ffast-math", "-fno-openmp"]
__linker_args   = ["-fno-openmp"]
opt_args = {"extra_compile_args": __compiler_args,
            "extra_link_args": __linker_args}

DEFAULT_TYPEDEFC = "typedef {0} float_type;\n".format(DEFAULT_TYPE_C)


class ThomasFermi2D(LevmarFitter):
    r"""
    Fitter for a two-dimensional Thomas Fermi profile.
    
    The data to be fitted is interpreted as rectangular image,
    given by a 2d-ndarray. The function is aligned to the x and y axis.
    
    .. math:: f(x, y) = A\cdot\max\left[1. - \frac{(x-x_0)^2}{r_x^2} - \frac{(y-y_0)^2}{r_y^2} , 0 \right]^\frac{3}{2} + \text{off}
    
    The order of the fit parameters is (A_t, x_0, r_x, y_0, r_y, off). 
    
    :param data: (ndarray) Image to be fitted.
    """
        
    def __init__(self, data):
        LevmarFitter.__init__(self, ["A_t", "x_0", "r_x", "y_0", "r_y", "off"], data)
        
        cache_x = np.empty(data.shape[1], dtype=float)
        cache_y = np.empty(data.shape[0], dtype=float)
        self.cache = (cache_x, cache_y)
    
    def guess(self):
        # fit projection to x and y direction
        projection_fitter = Gauss1D(self.data.sum(axis=0))
        pars_x = projection_fitter.fit()
        projection_fitter = Gauss1D(self.data.sum(axis=1))
        pars_y = projection_fitter.fit()
        
        def G(p, xupper):
            x1, x2 = 0, xupper 
            upper = np.sqrt(np.pi/2)*p[2]*erf((x2-p[1])/(np.sqrt(2)*p[2]))
            lower = np.sqrt(np.pi/2)*p[2]*erf((x1-p[1])/(np.sqrt(2)*p[2]))
            return upper-lower
        
        # guess parameters from 1d fits
        nx, ny = self.cache[0].size, self.cache[1].size
        amp = 0.5 * (pars_x[0]/G(pars_y, ny-1)+pars_y[0]/G(pars_x, nx-1));
        x_0 = pars_x[1]
        r_x = pars_x[2] * 2.
        y_0 = pars_y[1]
        r_y = pars_y[2] * 2.
        off = 0.5 * (pars_x[3]/(ny-1) + pars_y[3]/(nx-1))
        return np.asfarray((amp, x_0, r_x, y_0, r_y, off))
    
    f_code = DEFAULT_TYPEDEFC + """
    const int nx = Ncache_x[0];
    const int ny = Ncache_y[0];
    const float_type inv_rx_2 = 1. / p[2] / p[2];
    const float_type inv_ry_2 = 1. / p[4] / p[4];

    // cache values
    for (int ix = 0; ix < nx; ++ix) {
        float_type dist = ix-p[1];
        cache_x[ix] = inv_rx_2*dist*dist;
    }
    for (int iy = 0; iy < ny; ++iy) {
        float_type dist = iy-p[3];
        cache_y[iy] = inv_ry_2*dist*dist;
    }
    // calc f
    for (int iy = 0; iy < ny; ++iy) {
        for (int ix = 0; ix < nx; ++ix) {
            f[nx*iy+ix] = p[0]*pow(fmax(1. - cache_x[ix] - cache_y[iy], 0.0), 3./2.) + p[5];
        }
    }
    """
    
    def f(self, pars):
        f = self._f
        cache_x, cache_y = self.cache
        p = pars
        weave.inline(self.f_code, ["f", "cache_x", "cache_y", "p"], **opt_args)
    
    fJ_code = DEFAULT_TYPEDEFC + """
    const int nx = Ncache_x[0];
    const int ny = Ncache_y[0];
    const int n = nx * ny;
    const float_type invrx = 1. / p[2];
    const float_type invry = 1. / p[4];

    // cache values
    for (int ix = 0; ix < nx; ++ix) {
        float_type distx = ix-p[1];
        cache_x[ix] = distx*invrx*invrx;
    }
    for (int iy = 0; iy < ny; ++iy) {
        float_type disty = iy-p[3];
        cache_y[iy] = disty*invry*invry;
    }
    // calc f and jacobian
    #pragma omp parallel for
    for (int iy = 0; iy < ny; ++iy) {
        const float_type disty = iy-p[3];
        
        for (int ix = 0; ix < nx; ++ix) {
            const float_type distx = ix-p[1];
            const int ind = nx*iy+ix;
            
            const float_type is_inside_p = (float_type) ((distx*cache_x[ix] + disty*cache_y[iy]) < 1.);
            const float_type parab_sqrt = sqrt(1. - distx*cache_x[ix] - disty*cache_y[iy]) * is_inside_p;
            
            f[ind] = p[0]*parab_sqrt*parab_sqrt*parab_sqrt + p[5];
            J[ind] = parab_sqrt*parab_sqrt*parab_sqrt;
            J[ind+1*n] = p[0]*3.*cache_x[ix] * parab_sqrt;
            J[ind+2*n] = p[0]*3.*distx*cache_x[ix]*invrx * parab_sqrt;
            J[ind+3*n] = p[0]*3.*cache_y[iy] * parab_sqrt;
            J[ind+4*n] = p[0]*3.*disty*cache_y[iy]*invry * parab_sqrt;
            J[ind+5*n] = 1.0;
        }
    }
    """
    
    def fJ(self, pars):
        f, J = self._f, self._J
        cache_x, cache_y = self.cache
        p = pars
        weave.inline(self.fJ_code, ["f", "J", "cache_x", "cache_y", "p"], **opt_args)

    def sanitizePars(self, pars):
        pars[2] = abs(pars[2])
        pars[4] = abs(pars[4])
        return pars
    
    def integral(self, pars = None):
        """
        Calculate the integral of the Thomas Fermi function
        defined by `pars`.
        
        :param pars: (ndarray) Parameters or `None` to use param from fit.
        :return: (float) Value of the integral.
        """
        if pars is None:
            pars = self.pars_fit
        return 2.*np.pi / 5. * pars[0] * pars[2] * pars[4]

class Bimodal2D(LevmarFitter):
    r"""
    Fitter for a two-dimensional bimodal distribution.
    
    A bimodal distribution is the combination of a thomas fermi and a gaussian
    function. The data to be fitted is interpreted as rectangular image,
    given by a 2d-ndarray. The functions are aligned to the x and y axis.
    
    .. math::
    
        t(x, y) = A_t\cdot\max\left[1 - \frac{(x-x_0)^2}{2 r_x^2} - \frac{(y-y_0)^2}{2 r_y^2} , 0 \right]^\frac{3}{2}
        
        g(x, y) = A_g\cdot\exp\left[-\frac{(x-x_0)^2}{2 \sigma_x^2}-\frac{(y-y_0)^2}{2 \sigma_y^2}\right]
        
        \text{bimodal}(x, y) = t(x, y) + g(x, y) + \text{off}
    
    The order of the fit parameters is (A_t, A_g, x_0, r_x, s_x, y_0, r_y, s_y, off). 
    
    :param data: (ndarray) Image to be fitted.
    """
        
    def __init__(self, data):
        LevmarFitter.__init__(self, ["A_t", "A_g", "x_0", "r_x", "s_x", "y_0", "r_y", "s_y", "off"], data)
        
        cache_ex = np.empty(data.shape[1], dtype=float)
        cache_ey = np.empty(data.shape[0], dtype=float)
        self.cache = (cache_ex, cache_ey)
    
    def guess(self):
        # fit projection to x and y direction
        projection_fitter = Gauss1D(self.data.sum(axis=0))
        pars_x = projection_fitter.fit()
        projection_fitter = Gauss1D(self.data.sum(axis=1))
        pars_y = projection_fitter.fit()
        
        def G(p, xupper):
            x1, x2 = 0, xupper 
            upper = np.sqrt(np.pi/2)*p[2]*erf((x2-p[1])/(np.sqrt(2)*p[2]))
            lower = np.sqrt(np.pi/2)*p[2]*erf((x1-p[1])/(np.sqrt(2)*p[2]))
            return upper-lower
        
        # guess parameters from 1d fits
        nx, ny = self.cache[0].size, self.cache[1].size
        amp = 0.5 * (pars_x[0]/G(pars_y, ny-1)+pars_y[0]/G(pars_x, nx-1));
        x_0 = pars_x[1]
        s_x = pars_x[2]
        y_0 = pars_y[1]
        s_y = pars_y[2]
        off = 0.5 * (pars_x[3]/(ny-1) + pars_y[3]/(nx-1))
        return np.asfarray((amp/2, amp/2, x_0, s_x, s_x, y_0, s_y, s_y, off))
    
    fJ_code = DEFAULT_TYPEDEFC + """
    const int nx = Ncache_ex[0];
    const int ny = Ncache_ey[0];
    const int n = nx * ny;
    const float_type amp_t = fabs(p[0]);
    const float_type amp_g = fabs(p[1]);
    const float_type invrx = 1. / p[3];
    const float_type invsx = 1. / p[4];
    const float_type invry = 1. / p[6];
    const float_type invsy = 1. / p[7];

    // cache exp values
    for (int ix = 0; ix < nx; ++ix) {
        float_type dist = ix-p[2];
        cache_ex[ix] = exp(-.5*invsx*invsx*dist*dist);
    }
    for (int iy = 0; iy < ny; ++iy) {
        float_type dist = iy-p[5];
        cache_ey[iy] = exp(-.5*invsy*invsy*dist*dist);
    }
    // calc f and jacobian
    #pragma omp parallel for
    for (int iy = 0; iy < ny; ++iy) {
        const float_type disty = iy-p[5];
        
        for (int ix = 0; ix < nx; ++ix) {
            const int ind = nx*iy+ix;
            const float_type distx = ix-p[2];
            
            const float_type gauss = amp_g * cache_ex[ix] * cache_ey[iy];
            
            const float_type is_inside_p = (float_type) ((distx*distx*invrx*invrx + disty*disty*invry*invry) < 1.);
            const float_type parab_sqrt = sqrt(1. - distx*distx*invrx*invrx - disty*disty*invry*invry) * is_inside_p;
            
            f[ind] = gauss + amp_t*parab_sqrt*parab_sqrt*parab_sqrt + p[8];
            J[ind] = parab_sqrt*parab_sqrt*parab_sqrt;
            J[ind+1*n] = cache_ex[ix] * cache_ey[iy];
            J[ind+2*n] = amp_t*3.*distx*invrx*invrx*parab_sqrt + distx*invsx*invsx*gauss;
            J[ind+3*n] = amp_t*3.*distx*distx*invrx*invrx*invrx * parab_sqrt;
            J[ind+4*n] = distx*distx*invsx*invsx*invsx * gauss;
            J[ind+5*n] = amp_t*3.*disty*invry*invry*parab_sqrt + disty*invsy*invsy*gauss;
            J[ind+6*n] = amp_t*3.*disty*disty*invry*invry*invry * parab_sqrt;
            J[ind+7*n] = disty*disty*invsy*invsy*invsy * gauss;
            J[ind+8*n] = 1.0;
        }
    }
    """
    
    def fJ(self, pars):
        f, J = self._f, self._J
        cache_ex, cache_ey = self.cache
        p = pars
        weave.inline(self.fJ_code, ["f", "J", "cache_ex", "cache_ey", "p"], **opt_args)

    def sanitizePars(self, pars):
        pars[[3,4,6,7]] = np.abs(pars[[3,4,6,7]])
        return pars

    def integral_tf(self, pars = None):
        """
        Calculate the integral of the Thomas Fermi part of the bimodal
        distribution defined by `pars`.
        
        :param pars: (ndarray) Parameters or `None` to use param from fit.
        :return: (float) Value of the integral.
        """
        if pars is None:
            pars = self.pars_fit
        return 2.*np.pi / 5. * pars[0] * pars[3] * pars[6]

    def integral_gauss(self, pars = None):
        """
        Calculate the integral of the gaussian part of the bimodal
        distribution defined by `pars`.
        
        :param pars: (ndarray) Parameters or `None` to use param from fit.
        :return: (float) Value of the integral.
        """
        if pars is None:
            pars = self.pars_fit
        return 2.*np.pi * pars[1] * pars[4] * pars[7]

    def integral(self, pars = None):
        """
        Calculate the integral of bimodal distribution defined by `pars`.
        
        :param pars: (ndarray) Parameters or `None` to use param from fit.
        :return: (float) Value of the integral.
        """
        if pars is None:
            pars = self.pars_fit
        return self.integral_gauss(pars) + self.integral_tf(pars)

if __name__ == "__main__":
    import time
        
    def gauss1d(x, pars):
        A, x0, sx, off = pars        
        return A * np.exp(-(x-x0)**2 / sx**2 *.5) + off
        
    def gauss2d(x, y, pars):
        A, x0, sx, y0, sy, off = pars
        ex = np.exp(-(x-x0)**2 / sx**2 *.5)
        ey = np.exp(-(y-y0)**2 / sy**2 *.5)
        return A * ex * ey + off

    n = 250
    Y, X = np.ogrid[:n:1., :n:1.]
    
    alpha_org = -10 * np.pi / 180.
    pars_org = np.asfarray([1., n/2, 50, n/2, 5, 0])
    
    data_org = gauss2d(X, Y, pars_org)
        
    fitter = Bimodal2D(data_org)
    fitter.verbose = False
    pars_ini = fitter.guess()
    data_ini = fitter.getFitData(pars_ini)
    t_start = time.time()
    pars_fit = fitter.fit(pars_ini)
    print "%.2f ms for fit" % ((time.time() - t_start)*1e3)
    data_fit = fitter.getFitData(pars_fit)
    
    print fitter.getFitLog()
    
    import pylab as p
    p.subplot(1,3,1)
    p.imshow(data_org)
    p.subplot(1,3,2)    
    p.imshow(data_ini)
    p.subplot(1,3,3)
    p.imshow(data_fit)
    p.show()
