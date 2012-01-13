"""

The module :mod:`qao.plot.PlotTools` is deprecated and
should not be used anymore. Most functions are merged to
:mod:`qao.plot.image`.
"""

from PyQt4 import QtCore, QtGui
import pylab as p
import numpy

########################################################################
# matplotlib

def plotPolar(theta, radius, size = 8, rlabelsize=0, tlabelsize=15, rmax=1.0, datacolor = 'b'):
  from matplotlib.pyplot import figure, show, rc, grid, savefig
  rc('grid', color='k', linewidth=.5, linestyle='--')
  rc('xtick', labelsize=tlabelsize)
  rc('ytick', labelsize=rlabelsize)
  fig = figure(figsize=(size,size),facecolor='w')
  ax = fig.add_axes([0.1, 0.1, 0.8, 0.8], polar=True, axisbg='w')
  for i in range(len(radius)):
    ax.plot([theta[i]], [radius[i]],"o", color=datacolor)
    ax.set_rmax(rmax)
    grid(True)
  return fig

__colormaps = {
   "hot":   p.cm.hot,
   "jet":   p.cm.jet,
   "gray":  p.cm.gray,
   "winter":  p.cm.winter,
   "gist_yarg":  p.cm.gist_yarg,
   "gist_heat":  p.cm.gist_heat,
   "blues": p.cm.Blues,
   "greys": p.cm.Greys,
   "bupu": p.cm.BuPu,
   "cool": p.cm.cool,
   "summer": p.cm.summer
}

def imsave(data, filename, colormap = "jet"):
   """
   imsave(data, filename, colormap)
   
   Saves an image to 'filename' using a colormap from (jet,hot,gray).
   Every element of the 2d matrix 'data' is represented by a single pixel.
   """
   
   figsize=(numpy.array(data.shape)/100.0)[::-1]
   p.rcParams.update({'figure.figsize':figsize})
   fig = p.figure(figsize=figsize)
   p.axes([0,0,1,1]) # plot shall occupy the whole canvas
   p.axis('off')
   fig.set_size_inches(figsize)
   p.imshow(data, origin='upper', cmap=__colormaps[colormap])
   p.savefig(filename, facecolor='black', edgecolor='black', dpi=100)
   p.clf()

########################################################################
# qt4

class LinearColorMap:

    def __init__(self, color1, color2):
        assert isinstance(color1, QtGui.QColor), "QColor required"
        assert isinstance(color2, QtGui.QColor), "QColor required"
        
        self.stops = [[0.0, color1], [1.0, color2]]

    def addColorStop(self, position, color):
        assert isinstance(color, QtGui.QColor), "QColor required"
        
        self.stops.append([position,color])
        self.stops.sort(lambda x,y: int(x[0]-y[0]+1)*2-1)        

cmap_gray = LinearColorMap(QtGui.QColor("#000000"), QtGui.QColor("#ffffff"))

cmap_wjet = LinearColorMap(QtGui.QColor("#ffffff"), QtGui.QColor("#ff0000"))
cmap_wjet.addColorStop(0.12,QtGui.QColor("#0000ff"))
cmap_wjet.addColorStop(0.35,QtGui.QColor("#00ffff"))
cmap_wjet.addColorStop(0.53,QtGui.QColor("#83ff63"))
cmap_wjet.addColorStop(0.65,QtGui.QColor("#ffff00"))

cmap_jet = LinearColorMap(QtGui.QColor("#00007f"), QtGui.QColor("#ff0000"))
cmap_jet.addColorStop(0.12,QtGui.QColor("#0000ff"))
cmap_jet.addColorStop(0.35,QtGui.QColor("#00ffff"))
cmap_jet.addColorStop(0.53,QtGui.QColor("#83ff63"))
cmap_jet.addColorStop(0.65,QtGui.QColor("#ffff00"))

cmap_hot = LinearColorMap(QtGui.QColor("#000000"), QtGui.QColor("#ffffff"))
cmap_hot.addColorStop(0.40,QtGui.QColor("#ff0000"))
cmap_hot.addColorStop(0.70,QtGui.QColor("#ffff00"))


def convertToQImage(data, cmap=cmap_wjet, plotrange=[None, None]):
    # check range
    if plotrange[0] == None: plotrange = [data.min(), plotrange[1]]
    if plotrange[1] == None: plotrange = [plotrange[0], data.max()]
    # float and normalize data
    data = numpy.asfarray(data)
    data = (data-plotrange[0]) * (1. / (plotrange[1]-plotrange[0]))
    data = data.clip(0,1)
    # create red, green and blue channel images
    data_r = numpy.zeros(data.shape, dtype=numpy.uint32)
    data_g = numpy.zeros(data.shape, dtype=numpy.uint32)
    data_b = numpy.zeros(data.shape, dtype=numpy.uint32)
    
    for i in range(1, len(cmap.stops)):
        pos1, color1 = cmap.stops[i-1]
        pos2, color2 = cmap.stops[i]
        
        # linear interpolation from color1 to color2
        mask = (data >= pos1)
        norm = 1.0 / (pos2-pos1)
        f = (data[mask]-pos1) * norm
        
        data_r[mask] = f*(color2.red() - color1.red()) + color1.red()
        data_g[mask] = f*(color2.green() - color1.green()) + color1.green()
        data_b[mask] = f*(color2.blue() - color1.blue()) + color1.blue()

    image_data = ((data_r<<16) | (data_g<<8) | (data_b))

    # convert uint32 array to QImage
    image = QtGui.QImage(image_data.data,data.shape[1],data.shape[0],QtGui.QImage.Format_RGB32)
    image._numpyReference = image_data
    return image

def convertToGrayscaleQImage(data, plotrange=[None, None]):
    # check range, scale to 255
    if plotrange[0] == None: plotrange = [data.min(), plotrange[1]]
    if plotrange[1] == None: plotrange = [plotrange[0], data.max()]
    data = (data-plotrange[0]) * (255.0 / (plotrange[1]-plotrange[0]))
    # clip and convert data
    data = data.clip(0,255).astype(numpy.uint8)
    # create rgba image buffer
    data_rgb = numpy.empty([data.shape[0], data.shape[1], 4], numpy.uint8)
    data_rgb[:,:,0] = data
    data_rgb[:,:,1] = data
    data_rgb[:,:,2] = data
    # create qimage
    qimage = QtGui.QImage(data_rgb.data,data.shape[1],data.shape[0],QtGui.QImage.Format_RGB32)
    qimage._numpyReference = data_rgb
    return qimage

def convertToIndexedQImage(data, plotrange=[None, None]):
    # check range, scale to 255
    if plotrange[0] == None: plotrange = [data.min(), plotrange[1]]
    if plotrange[1] == None: plotrange = [plotrange[0], data.max()]
    data = (data-plotrange[0]) * (255.0 / (plotrange[1]-plotrange[0]))
    # clip and convert data
    data = data.clip(0,255).astype(numpy.uint8)
    qimage = QtGui.QImage(data.data,data.shape[1],data.shape[0],QtGui.QImage.Format_Indexed8)
    qimage._numpyReference = data
    return qimage

########################################################################
# vtk & maya

def plot3D(data, cmap = "blue-red"):
  from enthought.tvtk.tools import mlab

  gui = mlab.GUI()
  fig = mlab.figure()
  (height,width) = data.shape
  x = numpy.arange(0, width)
  y = numpy.arange(0, height)

  def fct(x,y):
      return data[y,x]

  s = mlab.SurfRegular(x, y , fct)
  s.lut_type=cmap
  fig.add(s)
  gui.start_event_loop()
