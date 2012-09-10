"""
Image plotting
=================

This module provides functions for creating rgb-color mapped
images from raw data. These functions are optimized for speed
and very useful when developing responsive applications.

The data is provided as ndarray and can be converted to rgb
ndarrays for general use or directly to QImage objects for
application support and file output. The colormap used
during the conversion is given by a dictionary containing
three arrays named *r_map*, *g_map* and *b_map*. They define
the number of stops in the data-range 0.0 to 1.0 and the
corresponging color-value.

A few color-maps are already provided by this module:

* **cmap_jet** - Well known blue-to-red map
* **cmap_wjet** - Version of jet using white as starting color
* **cmap_hot** - Black-red-yellow/white colormap
* **cmap_gray** - Simple grayscale map

"""

import numpy as np
from scipy import weave
from PyQt4 import QtGui

#########################################################################################

cmap_wjet = {"r_map": np.array([1.0, 0.2, 0.0, 0.0, 0.5, 1.0, 1.0, 1.0]),
             "g_map": np.array([1.0, 0.3, 0.5, 1.0, 1.0, 1.0, 0.3, 0.0]),
             "b_map": np.array([1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0])}

cmap_jet = {"r_map": np.array([0.0, 0.0, 0.0, 0.5, 1.0, 1.0]),
            "g_map": np.array([0.0, 0.0, 1.0, 1.0, 1.0, 0.0]),
            "b_map": np.array([0.5, 1.0, 1.0, 0.3, 0.0, 0.0])}

cmap_hot = {"r_map": np.array([0.0, 0.8, 1.0, 1.0]),
            "g_map": np.array([0.0, 0.0, 0.9, 1.0]),
            "b_map": np.array([0.0, 0.0, 0.0, 1.0])}

cmap_gray = {"r_map": np.array([0.0, 1.0]),
             "g_map": np.array([0.0, 1.0]),
             "b_map": np.array([0.0, 1.0])}

########################################################################################################################################################

__ptr_from_capsule_code = """
unsigned char *rgbdata = (unsigned char*) PyCapsule_GetPointer(rgbdata_capsule, NULL);
"""
__ptr_from_cobject_code = """
unsigned char *rgbdata = (unsigned char*) PyCObject_AsVoidPtr(rgbdata_cobject);
"""

__cmapping_code = r"""
const double * const pdata = data;
const int size      = Ndata[1]*Ndata[0];
const int ncmap     = Nr_map[0];
const double scalef = (1. / (vmax-vmin)) * (ncmap-1);

#pragma omp parallel for
for (int i=0; i<size; ++i) {
    unsigned char *prgb = rgbdata + 4*i;
    double val = (pdata[i] - vmin) * scalef;
    val = fmax(val, 0);
    
    int j = fmin(val   , ncmap-1);
    int k = fmin(val+1., ncmap-1);
    double f = val - j;

    prgb[0] = (b_map[j]*(1.-f) + b_map[k]*f)*255;
    prgb[1] = (g_map[j]*(1.-f) + g_map[k]*f)*255;
    prgb[2] = (r_map[j]*(1.-f) + r_map[k]*f)*255;
    prgb[3] = 255;
}
"""

__compiler_args = "-O3 -march=native -ffast-math -fno-openmp"
__linker_args   = "-fno-openmp"

def __checkTypes(data, vmin, vmax):
    # data must be contiguous and of type double
    data = np.ascontiguousarray(data, dtype=np.double)
    assert data.ndim == 2, "invalid number of dimensions"
    # vmin and vmax must be double, determine values if necessary
    if vmin is None:
        vmin = float(data.min())
    else:
        vmin = float(vmin)
    if vmax is None:
        vmax = float(data.max())
    else:
        vmax = float(vmax)
    return data, vmin, vmax

def cmapping_ndarray_inline(data, rgbdata, vmin, vmax, r_map, g_map, b_map):
    weave.inline(__cmapping_code, ['data', 'rgbdata', 'vmin', 'vmax', 'r_map', 'g_map', 'b_map'],
                 extra_compile_args = [__compiler_args], extra_link_args = [__linker_args])
    
def cmapping_cobject_inline(data, rgbdata_cobject, vmin, vmax, r_map, g_map, b_map):
    weave.inline(__ptr_from_cobject_code + __cmapping_code, ['data', 'rgbdata_cobject', 'vmin', 'vmax', 'r_map', 'g_map', 'b_map'],
                 extra_compile_args = [__compiler_args], extra_link_args = [__linker_args])

def createRGB(data, vmin = None, vmax = None, cmap = cmap_wjet):
    """
    Create RGB values from data using a color-map.

    The minimum and maximum value for scaling the colormap is
    determined from `data` unless specified by `vmin` and `vmax`.
    The output array's shape will be (height, width, 4),
    containing the rgb values for each pixel. 
    
    :param data: (ndarray) Array containing the data values.
    :param vmin: (float) Minimum data value or None.
    :param vmax: (float) Maximum data value or None.
    :param cmap: (dict) Colormap for converting the data.
    :returns: (ndarray) Array containing RGB data.
    
    Example::
        
        import numpy as np
        import pylab as p
        from qao.plot.image import createRGB, cmap_hot
        
        data = np.random.rand(200, 200)
        data_rgb = createRGB(data, cmap = cmap_hot)
    """
    data, vmin, vmax = __checkTypes(data, vmin, vmax)
    # create rgb values from data
    rgbdata = np.empty([data.shape[0], data.shape[1], 4], dtype=np.uint8)
    cmapping_ndarray_inline(data, rgbdata, vmin, vmax, cmap["r_map"], cmap["g_map"], cmap["b_map"])
    return rgbdata

def createQImage(data, vmin = None, vmax = None, cmap = cmap_wjet):
    """
    Create QImage from data array using a color-map.

    The minimum and maximum value for scaling the colormap is
    determined from `data` unless specified by `vmin` and `vmax`.
    The output will be a 24bit RGB QImage that can be used within
    graphical user applications or saved to files. 
    
    :param data: (ndarray) Array containing the data values.
    :param vmin: (float) Minimum data value or None.
    :param vmax: (float) Maximum data value or None.
    :param cmap: (dict) Colormap for converting the data.
    :returns: (QImage) Image from given data.
    
    Example::
        
        import numpy as np
        from qao.plot.image import createQImage, cmap_jet
        
        data = np.random.rand(200, 200)
        qimage = createQImage(data, cmap = cmap_jet)
        qimage.save("random.png")
    """
    data, vmin, vmax = __checkTypes(data, vmin, vmax)
    # write rgb data to new QImage
    qimage = QtGui.QImage(data.shape[1], data.shape[0], QtGui.QImage.Format_RGB32)
    rgbdata_cobject = qimage.bits().ascobject()
    cmapping_cobject(data, rgbdata_cobject, vmin, vmax, cmap["r_map"], cmap["g_map"], cmap["b_map"])
    return qimage

def updateQImage(qimage, data, vmin = None, vmax = None, cmap = cmap_wjet):
    """
    Modify a QImage in place from data array.

    Like :func:`createQImage`, but instead of creating a new QImage,
    this function updates an existing QImage. The size of the image
    must not change.
    
    :param qimage: (QImage) QImage object to be updated.
    :param data: (ndarray) Array containing the data values.
    :param vmin: (float) Minimum data value or None.
    :param vmax: (float) Maximum data value or None.
    :param cmap: (dict) Colormap for converting the data.
    :returns: (QImage) Image from given data.
    
    Example::
        
        import numpy as np
        from qao.plot.image import createQImage, updateQImage
        
        data = np.random.rand(200, 200)
        qimage = createQImage(np.zeros_like(data))
        updateQImage(qimage, data)
        qimage.save("random.png")
    """
    data, vmin, vmax = __checkTypes(data, vmin, vmax)
    # write rgb data to existing QImage
    assert data.size == (qimage.height()*qimage.width()), "invalid size"
    rgbdata_cobject = qimage.bits().ascobject()
    cmapping_cobject(data, rgbdata_cobject, vmin, vmax, cmap["r_map"], cmap["g_map"], cmap["b_map"])

def buildExt(compiler='', verbose=1, optimize=True):
    # type definitions
    data = np.zeros([2,2], dtype=np.double)
    vmin = 0.; vmax = 1. #@UnusedVariable
    r_map   = np.zeros(2, dtype=np.double) #@UnusedVariable
    g_map   = np.zeros(2, dtype=np.double) #@UnusedVariable
    b_map   = np.zeros(2, dtype=np.double) #@UnusedVariable
    rgbdata = np.empty(data.size*4, dtype=np.uint8) #@UnusedVariable
    qimage  = QtGui.QImage(data.shape[1], data.shape[0], QtGui.QImage.Format_RGB32)
    rgbdata_cobject = qimage.bits().ascobject() #@UnusedVariable
    
    # build extension
    mod = weave.ext_tools.ext_module("ext_image", compiler)
    c_cmapping_ndarray = weave.ext_function("cmapping_ndarray", __cmapping_code, ['data', 'rgbdata', 'vmin', 'vmax', 'r_map', 'g_map', 'b_map'])
    c_cmapping_cobject = weave.ext_function("cmapping_cobject", __ptr_from_cobject_code + __cmapping_code, ['data', 'rgbdata_cobject', 'vmin', 'vmax', 'r_map', 'g_map', 'b_map'])
    mod.add_function(c_cmapping_ndarray)
    mod.add_function(c_cmapping_cobject)
    if optimize:
        mod.customize.add_extra_compile_arg(__compiler_args)
        mod.customize.add_extra_link_arg(__linker_args)
    mod.compile(verbose = verbose)

########################################################################################################################################################

# try to determine if this system can compile code, if not, try to load a precompiled extension
try:
    cmapping_ndarray_inline(np.empty([1,1], dtype=float), np.empty(4, dtype=np.uint8), 0, 1, cmap_wjet["r_map"], cmap_wjet["g_map"], cmap_wjet["b_map"])
    cmapping_ndarray = cmapping_ndarray_inline #@UnusedVariable
    cmapping_cobject = cmapping_cobject_inline
except:
    print "cannot compile inline"
    try:
        from ext_image import cmapping_ndarray, cmapping_cobject #@UnresolvedImport @UnusedImport
    except:
        raise Exception("precompiled ext not found, compile using buildExt")

########################################################################################################################################################

if __name__ == '__main__':
    data = np.random.rand(100,100)
    
    
    
    import time
    
    # create test data
    Y, X = np.ogrid[-2:2:1000j, -2:2:1000j]
    data = np.exp(- X**2 - Y**2)
    
    # create rgb image
    t_start = time.time()
    qimage = createQImage(data, cmap = cmap_wjet)
    dt = time.time() - t_start
    print "created %dx%d QImage in %.2f ms" % (X.size, Y.size, dt*1e3)
    
    # show image
    app = QtGui.QApplication([])
    lb1 = QtGui.QLabel()
    lb1.setPixmap(QtGui.QPixmap.fromImage(qimage))
    lb1.show()
    app.exec_()
