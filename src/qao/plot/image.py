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
* **cmap_bwr** - Blue-white-red colormap
* **cmap_gray** - Simple grayscale map

"""

import numpy as np
from scipy import weave
from qao.gui.qt import QtGui

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

cmap_bwr = {"r_map": np.array([0.2298057, 0.26623388, 0.30386891, 0.342804478, 0.38301334, 0.424369608, 0.46666708, 0.509635204, 0.552953156, 0.596262162, 0.639176211, 0.681291281, 0.722193294, 0.761464949, 0.798691636, 0.833466556, 0.865395197, 0.897787179, 0.924127593, 0.944468518, 0.958852946, 0.96732803, 0.969954137, 0.966811177, 0.958003065, 0.943660866, 0.923944917, 0.89904617, 0.869186849, 0.834620542, 0.795631745, 0.752534934, 0.705673158]),
            "g_map": np.array([0.298717966, 0.353094838, 0.406535296, 0.458757618, 0.50941904, 0.558148092, 0.604562568, 0.648280772, 0.688929332, 0.726149107, 0.759599947, 0.788964712, 0.813952739, 0.834302879, 0.849786142, 0.860207984, 0.86541021, 0.848937047, 0.827384882, 0.800927443, 0.769767752, 0.734132809, 0.694266682, 0.650421156, 0.602842431, 0.551750968, 0.49730856, 0.439559467, 0.378313092, 0.312874446, 0.24128379, 0.157246067, 0.01555616]),
            "b_map": np.array([0.753683153, 0.801466763, 0.84495867, 0.883725899, 0.917387822, 0.945619588, 0.968154911, 0.98478814, 0.995375608, 0.999836203, 0.998151185, 0.990363227, 0.976574709, 0.956945269, 0.931688648, 0.901068838, 0.865395561, 0.820880546, 0.774508472, 0.726736146, 0.678007945, 0.628751763, 0.579375448, 0.530263762, 0.481775914, 0.434243684, 0.387970225, 0.343229596, 0.300267182, 0.259301199, 0.220525627, 0.184115123, 0.150232812])}

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
    Create image from data using a color-map.

    The minimum and maximum value for scaling the colormap is
    determined from `data` unless specified by `vmin` and `vmax`.
    The output array's shape will be (height, width, 4),
    containing the color values for each pixel. The color order
    is RGBA.
    
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
    cmapping_ndarray_inline(data, rgbdata, vmin, vmax, cmap["b_map"], cmap["g_map"], cmap["r_map"])
    return rgbdata

def createBGR(data, vmin = None, vmax = None, cmap = cmap_wjet):
    """
    Create image from data using a color-map.

    The minimum and maximum value for scaling the colormap is
    determined from `data` unless specified by `vmin` and `vmax`.
    The output array's shape will be (height, width, 4),
    containing the color values for each pixel. The color order
    is BGRA.
    
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
