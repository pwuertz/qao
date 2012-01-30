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


class Parab2D(LevmarFitter):
    r"""
    Fitter for a two-dimensional parabola.
    
    The data to be fitted is interpreted as rectangular image,
    given by a 2d-ndarray. The parabola is aligned to the x and y axis.
    
    .. math:: f(x, y) = \max\left[A - \frac{(x-x_0)^2}{2 a_x^2} - \frac{(x-x_0)^2}{2 a_x^2} , 0 \right] + \text{off}
    
    The order of the fit parameters is (A, x_0, a_x, y_0, a_y, off). 
    
    :param data: (ndarray) Image to be fitted.
    """
        
    def __init__(self, data):
        LevmarFitter.__init__(self, ["A", "x_0", "a_x", "y_0", "a_y", "off"], data)
        
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
        s_x = pars_x[2]
        y_0 = pars_y[1]
        s_y = pars_y[2]
        off = 0.5 * (pars_x[3]/(ny-1) + pars_y[3]/(nx-1))
        return np.asfarray((amp, x_0, s_x, y_0, s_y, off))
    
    f_code = DEFAULT_TYPEDEFC + """
    const int nx = Ncache_x[0];
    const int ny = Ncache_y[0];
    const float_type inv_ax_2 = 1. / p[2] / p[2];
    const float_type inv_ay_2 = 1. / p[4] / p[4];

    // cache values
    for (int ix = 0; ix < nx; ++ix) {
        float_type dist = ix-p[1];
        cache_x[ix] = .5*inv_ax_2*dist*dist;
    }
    for (int iy = 0; iy < ny; ++iy) {
        float_type dist = iy-p[3];
        cache_y[iy] = .5*inv_ay_2*dist*dist;
    }
    // calc f
    for (int iy = 0; iy < ny; ++iy) {
        for (int ix = 0; ix < nx; ++ix) {
            f[nx*iy+ix] = fmax(p[0] - cache_x[ix] - cache_y[iy], 0.0) + p[5];
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
    const float_type invax = 1. / p[2];
    const float_type invay = 1. / p[4];
    const float_type inv_ax_2 = invax * invax;
    const float_type inv_ay_2 = invay * invay;
    const float_type inv_ax_3 = inv_ax_2 * invax;
    const float_type inv_ay_3 = inv_ay_2 * invay;

    // cache values
    for (int ix = 0; ix < nx; ++ix) {
        float_type dist = ix-p[1];
        cache_x[ix] = .5*inv_ax_2*dist*dist;
    }
    for (int iy = 0; iy < ny; ++iy) {
        float_type dist = iy-p[3];
        cache_y[iy] = .5*inv_ay_2*dist*dist;
    }
    // calc f and jacobian
    #pragma omp parallel for
    for (int iy = 0; iy < ny; ++iy) {
        const float_type disty = iy-p[3];
        
        for (int ix = 0; ix < nx; ++ix) {
            const float_type distx = ix-p[1];
            const float_type is_inside = (float) (p[0] > (cache_x[ix] + cache_y[iy]));
            const int ind = nx*iy+ix;
            
            f[ind] = (p[0] - cache_x[ix] - cache_y[iy]) * is_inside + p[5];
            J[ind] = is_inside;
            J[ind+1*n] = distx * inv_ax_2 * is_inside;
            J[ind+2*n] = distx * distx * inv_ax_3 * is_inside;
            J[ind+3*n] = disty * inv_ay_2 * is_inside;
            J[ind+4*n] = disty * disty * inv_ay_3 * is_inside;
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

class Bimodal2D(LevmarFitter):
    r"""
    Fitter for a two-dimensional bimodal distribution.
    
    A bimodal distribution is the combination of a parabola and a gaussian
    function. The data to be fitted is interpreted as rectangular image,
    given by a 2d-ndarray. The functions are aligned to the x and y axis.
    
    .. math::
    
        p(x, y) = \max\left[A_p - \frac{(x-x_0)^2}{2 a_x^2} - \frac{(x-x_0)^2}{2 a_x^2} , 0 \right]
        
        g(x, y) = A_g\cdot\exp\left[-\frac{(x-x_0)^2}{2 \sigma_x^2}-\frac{(y-y_0)^2}{2 \sigma_y^2}\right]
        
        \text{bimodal}(x, y) = p(x, y) + g(x, y) + \text{off}
    
    The order of the fit parameters is (A_p, A_g, x_0, a_x, s_x, y_0, a_y, s_y, off). 
    
    :param data: (ndarray) Image to be fitted.
    """
        
    def __init__(self, data):
        LevmarFitter.__init__(self, ["A_p", "A_g", "x_0", "a_x", "s_x", "y_0", "a_y", "s_y", "off"], data)
        
        cache_ex = np.empty(data.shape[1], dtype=float)
        cache_ey = np.empty(data.shape[0], dtype=float)
        cache_px = np.empty(data.shape[1], dtype=float)
        cache_py = np.empty(data.shape[0], dtype=float)
        self.cache = (cache_ex, cache_ey, cache_px, cache_py)
    
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
    const float_type invax = 1. / p[3];
    const float_type invsx = 1. / p[4];
    const float_type invay = 1. / p[6];
    const float_type invsy = 1. / p[7];

    // cache exp values
    for (int ix = 0; ix < nx; ++ix) {
        float_type dist = ix-p[2];
        cache_ex[ix] = exp(-.5*invsx*invsx*dist*dist);
        cache_px[ix] = .5*invax*invax*dist*dist;
    }
    for (int iy = 0; iy < ny; ++iy) {
        float_type dist = iy-p[5];
        cache_ey[iy] = exp(-.5*invsy*invsy*dist*dist);
        cache_py[iy] = .5*invay*invay*dist*dist;
    }
    // calc f and jacobian
    #pragma omp parallel for
    for (int iy = 0; iy < ny; ++iy) {
        const float_type disty = iy-p[5];
        
        for (int ix = 0; ix < nx; ++ix) {
            const float_type distx = ix-p[2];
            const float_type is_inside_p = (float) (p[0] > (cache_px[ix] + cache_py[iy]));
            const float_type gauss = p[1] * cache_ex[ix] * cache_ey[iy];
            const float_type parab = (p[0] - cache_px[ix] - cache_py[iy]) * is_inside_p;
            const int ind = nx*iy+ix;
            
            f[ind] = gauss + parab + p[8];
            J[ind] = is_inside_p;
            J[ind+1*n] = cache_ex[ix] * cache_ey[iy];
            J[ind+2*n] = distx*invax*invax*is_inside_p + distx*invsx*invsx*gauss;
            J[ind+3*n] = distx*distx*invax*invax*invax * is_inside_p;
            J[ind+4*n] = distx*distx*invsx*invsx*invsx * gauss;
            J[ind+5*n] = disty*invay*invay*is_inside_p + disty*invsy*invsy*gauss;
            J[ind+6*n] = disty*disty*invay*invay*invay * is_inside_p;
            J[ind+7*n] = disty*disty*invsy*invsy*invsy * gauss;
            J[ind+8*n] = 1.0;
        }
    }
    """
    
    def fJ(self, pars):
        f, J = self._f, self._J
        cache_ex, cache_ey, cache_px, cache_py = self.cache
        p = pars
        weave.inline(self.fJ_code, ["f", "J", "cache_ex", "cache_ey", "cache_px", "cache_py", "p"], **opt_args)

    def sanitizePars(self, pars):
        pars[[3,4,6,7]] = np.abs(pars[[3,4,6,7]])
        return pars

if __name__ == "__main__":
        
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
    pars_fit = fitter.fit(pars_ini)
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