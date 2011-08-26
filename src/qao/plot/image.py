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

#########################################################################################

__ptr_from_capsule_code = """
unsigned char *rgbdata = (unsigned char*) PyCapsule_GetPointer(rgbdata_capsule, NULL);
"""
__ptr_from_cobject_code = """
unsigned char *rgbdata = (unsigned char*) PyCObject_AsVoidPtr(rgbdata_cobject);
"""

__cmapping_code = """
double *pdata = data;
unsigned char *prgb = rgbdata;
const int size      = Ndata[1]*Ndata[0];
const int ncmap     = Nr_map[0];
const double scalef = (1. / (vmax-vmin)) * (ncmap-1);

for (int i=0; i<size; ++i) {
    double val = (*pdata - vmin) * scalef;
    val = fmax(val, 0);
    
    int j = fmin(val   , ncmap-1);
    int k = fmin(val+1., ncmap-1);
    double f = val - j;

    *prgb = (b_map[j]*(1.-f) + b_map[k]*f)*255; ++prgb;
    *prgb = (g_map[j]*(1.-f) + g_map[k]*f)*255; ++prgb;
    *prgb = (r_map[j]*(1.-f) + r_map[k]*f)*255; ++prgb;
    *prgb = 255; ++prgb;
    ++pdata;
}
"""

#########################################################################################

def createRGB(data, vmin = None, vmax = None, cmap = cmap_wjet):
    """
    create rgb data from data array using the given colormap
    """
    data = np.ascontiguousarray(data, dtype=np.double)
    if vmin == None: vmin = float(data.min())
    else: vmin = float(vmin)
    if vmax == None: vmax = float(data.max())
    else: vmax = float(vmax)
    
    # create rgb values from data
    rgbdata = np.empty(data.size*4, dtype=np.uint8)
    weave.inline(__cmapping_code, ['data', 'rgbdata', 'vmin', 'vmax', 'r_map', 'g_map', 'b_map'], global_dict = cmap)
    return rgbdata

def createQImage(data, vmin = None, vmax = None, cmap = cmap_wjet):
    """
    create QImage from data array using the given colormap
    """
    data = np.ascontiguousarray(data, dtype=np.double)
    if vmin == None: vmin = float(data.min())
    else: vmin = float(vmin)
    if vmax == None: vmax = float(data.max())
    else: vmax = float(vmax)
                
    # write rgb data to new qimage
    assert data.ndim == 2, "not an image"
    qimage = QtGui.QImage(data.shape[1], data.shape[0], QtGui.QImage.Format_RGB32)
    rgbdata_cobject = qimage.bits().ascobject()  # P3K: .ascapsule()
    code = __ptr_from_cobject_code + __cmapping_code # P3K: ptr_from_capsule_code
    weave.inline(code, ['data', 'rgbdata_cobject', 'vmin', 'vmax', 'r_map', 'g_map', 'b_map'], global_dict = cmap)
    return qimage

def updateQImage(qimage, data, vmin = None, vmax = None, cmap = cmap_wjet):
    """
    modify existing QImage using an array of data and the given colormap
    """
    data = np.ascontiguousarray(data, dtype=np.double)
    if vmin == None: vmin = float(data.min())
    else: vmin = float(vmin)
    if vmax == None: vmax = float(data.max())
    else: vmax = float(vmax)
    
    # write rgb data to qimage
    assert data.ndim == 2, "not an image"
    assert data.size == (qimage.height()*qimage.width()), "invalid size"
    rgbdata_cobject = qimage.bits().ascobject()  # P3K: .ascapsule()
    code = __ptr_from_cobject_code + __cmapping_code # P3K: ptr_from_capsule_code
    weave.inline(code, ['data', 'rgbdata_cobject', 'vmin', 'vmax', 'r_map', 'g_map', 'b_map'], global_dict = cmap)

if __name__ == '__main__':
    import time
    
    # create test data
    Y, X = np.ogrid[-2:2:800j, -2:2:800j]
    data = np.exp(- X**2 - Y**2)
    
    # create rgb image
    t_start = time.time()
    qimage = createQImage(data, cmap = cmap_jet)
    dt = time.time() - t_start
    print "created %dx%d QImage in %.2f ms" % (X.size, Y.size, dt*1e3)
    
    # show image
    app = QtGui.QApplication([])
    lb1 = QtGui.QLabel()
    lb1.setPixmap(QtGui.QPixmap.fromImage(qimage))
    lb1.show()
    app.exec_()
