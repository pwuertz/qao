import numpy as np
import scipy.weave as weave
from scipy.special import erf
from scipy.ndimage import rotate
from fitter import Fitter, DEFAULT_TYPE_C, DEFAULT_TYPE_NPY

__compiler_args = ["-O3", "-march=native", "-ffast-math", "-fno-openmp"]
__linker_args   = ["-fno-openmp"]
opt_args = {"extra_compile_args": __compiler_args,
            "extra_link_args": __linker_args}

DEFAULT_TYPEDEFC = "typedef {0} float_type;\n".format(DEFAULT_TYPE_C)

class Gauss1D(Fitter):
    def __init__(self, data):
        Fitter.__init__(self, ["A", "x0", "sig", "off"], data)

        cache_z = np.empty_like(self._f)
        cache_e = np.empty_like(self._f)
        self.cache = (cache_z, cache_e)
    
    def guess(self):
        data = self.data
        dmin = data.min()
        dmax = data.max()
        dsum = data.sum()
        # mean and variance
        x0  = (np.arange(data.size) * data).sum() * (1./dsum)
        var = ((np.arange(data.size)-x0)**2 * data).sum() * (1./dsum)
        # return guess
        return np.asfarray([dmax, x0, np.sqrt(var), dmin], dtype = DEFAULT_TYPE_NPY)
    
    f_code = DEFAULT_TYPEDEFC + """
    const int n = Nf[0];
    const float_type invp2sq = 1.0/(p[2]*p[2]);
    for (int i = 0; i < n; ++i) {
        float_type dist = i-p[1];
        cache_z[i] = dist * invp2sq;
        cache_e[i] = exp(-.5*dist*cache_z[i]);
        f[i] = p[0] * cache_e[i] + p[3];
    }
    """
    
    def f(self, pars):
        f = self._f
        cache_z, cache_e = self.cache
        p = pars
        weave.inline(self.f_code, ["f", "cache_z", "cache_e", "p"], **opt_args)
    
    fJ_code = DEFAULT_TYPEDEFC + """
    const int n = Nf[0];
    const float_type invp2sq = 1.0/(p[2]*p[2]);
    for (int i = 0; i < n; ++i) {
        float_type dist = i-p[1];
        cache_z[i] = dist * invp2sq;
        cache_e[i] = exp(-.5*dist*cache_z[i]);
        f[i] = p[0] * cache_e[i] + p[3];
    }
    
    const float_type invp2 = 1.0/p[2];
    for(int i=0; i<n; ++i){
        J[i] = cache_e[i];
    }
    for(int i=0; i<n; ++i){
        J[n+i] = cache_z[i] * p[0] * cache_e[i];
    }
    for(int i=0; i<n; ++i){
        J[2*n+i] = cache_z[i]*cache_z[i]*p[2] * p[0] * cache_e[i];
    }
    for(int i=0; i<n; ++i){
        J[3*n+i] = 1.;
    }
    """
    
    def fJ(self, pars):
        f, J = self._f, self._J
        cache_z, cache_e = self.cache
        p = pars
        weave.inline(self.fJ_code, ["f", "J", "cache_z", "cache_e", "p"], **opt_args)

class Gauss2D(Fitter):
    
    def __init__(self, data):
        Fitter.__init__(self, ["A", "x_0", "s_x", "y_0", "s_y", "off"], data)

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
        return np.asfarray((amp, x_0, s_x, y_0, s_y, off))
    
    f_code = DEFAULT_TYPEDEFC + """
    const int nx = Ncache_ex[0];
    const int ny = Ncache_ey[0];
    const float_type inv_sx_2 = 1. / p[2] / p[2];
    const float_type inv_sy_2 = 1. / p[4] / p[4];

    // cache exp values
    for (int ix = 0; ix < nx; ++ix) {
        float_type dist = ix-p[1];
        cache_ex[ix] = exp(-.5*inv_sx_2*dist*dist);
    }
    for (int iy = 0; iy < ny; ++iy) {
        float_type dist = iy-p[3];
        cache_ey[iy] = exp(-.5*inv_sy_2*dist*dist);
    }
    // calc f
    for (int iy = 0; iy < ny; ++iy) {
        for (int ix = 0; ix < nx; ++ix) {
            f[nx*iy+ix] = p[0] * cache_ex[ix] * cache_ey[iy] + p[5];
        }
    }
    """
    
    def f(self, pars):
        f = self._f
        cache_ex, cache_ey = self.cache
        p = pars
        weave.inline(self.f_code, ["f", "cache_ex", "cache_ey", "p"], **opt_args)
    
    fJ_code = DEFAULT_TYPEDEFC + """
    const int nx = Ncache_ex[0];
    const int ny = Ncache_ey[0];
    const int n = nx * ny;
    const float_type invsx = 1. / p[2];
    const float_type invsy = 1. / p[4];
    const float_type inv_sx_2 = invsx * invsx;
    const float_type inv_sy_2 = invsy * invsy;
    const float_type inv_sx_3 = inv_sx_2 * invsx;
    const float_type inv_sy_3 = inv_sy_2 * invsy;

    // cache exp values
    for (int ix = 0; ix < nx; ++ix) {
        float_type dist = ix-p[1];
        cache_ex[ix] = exp(-.5*inv_sx_2*dist*dist);
    }
    for (int iy = 0; iy < ny; ++iy) {
        float_type dist = iy-p[3];
        cache_ey[iy] = exp(-.5*inv_sy_2*dist*dist);
    }
    // calc f and jacobian
    #pragma omp parallel for
    for (int iy = 0; iy < ny; ++iy) {
        const float_type disty = iy-p[3];
        
        for (int ix = 0; ix < nx; ++ix) {
            const float_type distx = ix-p[1];
            const float_type e = cache_ex[ix] * cache_ey[iy];
            const int ind = nx*iy+ix;
            
            f[ind] = p[0] * e + p[5];
            J[ind] = e;
            J[ind+1*n] = distx * inv_sx_2 * p[0] * e;
            J[ind+2*n] = distx*distx * inv_sx_3 * p[0] * e;
            J[ind+3*n] = disty * inv_sy_2 * p[0] * e;
            J[ind+4*n] = disty*disty * inv_sy_3 * p[0] * e;
            J[ind+5*n] = 1.0;
        }
    }
    """
    
    def fJ(self, pars):
        f, J = self._f, self._J
        cache_ex, cache_ey = self.cache
        p = pars
        weave.inline(self.fJ_code, ["f", "J", "cache_ex", "cache_ey", "p"], **opt_args)


class Gauss2DRot(Fitter):
    
    def __init__(self, data):
        Fitter.__init__(self, ["A", "x_0", "s_x", "y_0", "s_y", "alpha", "off"], data)
    
    def guess(self):
        # fit projection to x and y direction
        projection_fitter = Gauss1D(self.data.sum(axis=0))
        pars_x = projection_fitter.fit()
        projection_fitter = Gauss1D(self.data.sum(axis=1))
        pars_y = projection_fitter.fit()

        # guess parameters
        ny, nx = self.data.shape  
        offset = .5 * (pars_x[3]/(nx-1) + pars_y[3]/(ny-1))
        x0 = pars_x[1]
        y0 = pars_y[1]
        sx = abs(pars_x[2])
        sy = abs(pars_y[2])
        
        # calculate central moment (1,1)
        Y, X = np.ogrid[:self.data.shape[0]:1., :self.data.shape[1]:1.]
        data_density = self.data - offset
        data_density *= 1. / data_density.sum()
        mu11 = ((X-x0) * (Y-y0) * data_density).sum()
        
        # calculate orientation
        alpha = .5 * np.arctan2(2*mu11, (sx**2-sy**2))
        
        # calculate original sigmas and amplitude from rotated image
        data_density_rot = rotate(data_density, alpha*180./np.pi, order=0)
        ny_rot, nx_rot = data_density_rot.shape
        projection_fitter = Gauss1D(data_density_rot.sum(axis=0))
        pars_x_rot = projection_fitter.fit()
        projection_fitter = Gauss1D(data_density_rot.sum(axis=1))
        pars_y_rot = projection_fitter.fit()
        def G(p, xupper):
            x1, x2 = 0, xupper 
            upper = np.sqrt(np.pi/2)*p[2]*erf((x2-p[1])/(np.sqrt(2)*p[2]))
            lower = np.sqrt(np.pi/2)*p[2]*erf((x1-p[1])/(np.sqrt(2)*p[2]))
            return upper-lower
        amp = 0.5 * (pars_x_rot[0]/G(pars_y_rot, ny_rot-1)+pars_y_rot[0]/G(pars_x_rot, nx_rot-1)); 
        
        return np.asfarray([amp, x0, pars_x_rot[2], y0, pars_y_rot[2], alpha, offset])

    f_code = DEFAULT_TYPEDEFC + """
    const int nx = Ndata[1];
    const int ny = Ndata[0];
    const int n = nx * ny;
    const float_type cosa = cos(p[5]), sina = sin(p[5]);
    
    const float_type inv_sx = 1./p[2], inv_sy = 1.0/p[4];
    const float_type inv_sx_2 = inv_sx*inv_sx, inv_sy_2 = inv_sy*inv_sy;

    // calc rotated gauss
    #pragma omp parallel for
    for (int iy = 0; iy < ny; ++iy) {
        float_type dy = iy - p[3];
        for (int ix = 0; ix < nx; ++ix) {
            float_type dx = ix - p[1];
            float_type xrot = cosa*dx + sina*dy;
            float_type yrot = cosa*dy - sina*dx;
            float_type e = exp(.5 * ( - inv_sx_2*xrot*xrot - inv_sy_2*yrot*yrot ) );                
            f[iy*nx + ix] = p[0] * e + p[6];
        }
    }
    """

    def f(self, pars):
        data = self.data
        f = self._f
        p = pars
        weave.inline(self.f_code, ["f", "p", "data"], **opt_args)
    
    fJ_code = DEFAULT_TYPEDEFC + """
    const int nx = Ndata[1];
    const int ny = Ndata[0];
    const int n = nx * ny;
    const float_type cosa = cos(p[5]), sina = sin(p[5]);
    
    const float_type inv_sx = 1./p[2], inv_sy = 1.0/p[4];
    const float_type inv_sx_2 = inv_sx*inv_sx, inv_sy_2 = inv_sy*inv_sy;
    const float_type inv_sx_3 = inv_sx_2*inv_sx, inv_sy_3 = inv_sy_2*inv_sy;

    // calc rotated gauss
    #pragma omp parallel for
    for (int iy = 0; iy < ny; ++iy) {
        float_type dy = iy - p[3];
        for (int ix = 0; ix < nx; ++ix) {
            float_type dx = ix - p[1];
            float_type xrot = cosa*dx + sina*dy;
            float_type yrot = cosa*dy - sina*dx;
            
            int ind = iy*nx + ix;
            float_type e = exp(.5 * ( - inv_sx_2*xrot*xrot - inv_sy_2*yrot*yrot ) );
            
            f[ind] = p[0] * e + p[6];
            
            float_type coeff[5];
            coeff[0] = inv_sx_2*cosa*xrot - inv_sy_2*sina*yrot;
            coeff[1] = inv_sx_3*xrot*xrot;
            coeff[2] = inv_sx_2*sina*xrot + inv_sy_2*cosa*yrot;
            coeff[3] = inv_sy_3*yrot*yrot;
            coeff[4] = (p[2]*p[2]-p[4]*p[4])*inv_sx_2*inv_sy_2 * yrot*xrot;
            
            J[ind] = e;
            J[ind+1*n] = p[0] * e * coeff[0];
            J[ind+2*n] = p[0] * e * coeff[1];
            J[ind+3*n] = p[0] * e * coeff[2];
            J[ind+4*n] = p[0] * e * coeff[3];
            J[ind+5*n] = p[0] * e * coeff[4];
            J[ind+6*n] = 1.;
        }
    }
    """
    
    def fJ(self, pars):
        data = self.data
        f, J = self._f, self._J
        p = pars
        weave.inline(self.fJ_code, ["f", "J", "p", "data"], **opt_args)


if __name__ == "__main__":
        
    def gauss1d(x, pars):
        A, x0, sx, off = pars        
        return A * np.exp(-(x-x0)**2 / sx**2 *.5) + off
        
    def gauss2d(x, y, pars):
        A, x0, sx, y0, sy, off = pars
        ex = np.exp(-(x-x0)**2 / sx**2 *.5)
        ey = np.exp(-(y-y0)**2 / sy**2 *.5)
        return A * ex * ey + off
        
    def gauss2drot(x, y, pars):
        A, x0, sx, y0, sy, alpha, off = pars
        sina, cosa = np.sin(alpha), np.cos(alpha)
        x, y = (x-x0), (y-y0)
        xr = x*cosa + y*sina
        yr = y*cosa - x*sina
        return A * np.exp(- .5*xr**2/sx**2 - .5*yr**2/sy**2) + off

    n = 250
    Y, X = np.ogrid[:n:1., :n:1.]
    
    alpha_org = -10 * np.pi / 180.
    pars_org = np.asfarray([1., n/2, 50, n/2, 5, alpha_org, 0])
    
    data_org = gauss2drot(X, Y, pars_org)
        
    fitter = Gauss2DRot(data_org)
    fitter.verbose = False
    pars_ini = fitter.guess()
    data_ini = gauss2drot(X, Y, pars_ini)
    pars_fit = fitter.fit(pars_ini)
    data_fit = gauss2drot(X, Y, pars_fit)
    
    import pylab as p
    p.subplot(1,3,1)
    p.imshow(data_org)
    p.subplot(1,3,2)    
    p.imshow(data_ini)
    p.subplot(1,3,3)
    p.imshow(data_fit)
    p.show()