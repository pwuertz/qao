"""
Viewer for 2D data
===================

The classes in :mod:`qao.plot.image2dview` may be used to construct applications for analyzing
2d images. A colored data-to-image conversion is provided by utilizing the functions in :mod:`qao.plot.image`.
Furthermore, tools for selecting points/lines and rectangles in an image can be added to an image
viewer, so the user may mark regions of interest.

Example:
    
    .. literalinclude:: ../src/qao/plot/image2dview.py
        :pyobject: testWidgets
"""

import sys
import numpy
from qao.plot import image
from PyQt4 import QtGui, QtCore

# TODO: Signals and slots should only be used in QObjects.
# QGraphicsItem is not a QObject and multiple inheritance from Qt classes
# is not allowed in PyQt4. The proper solution is to wait for QGraphicsObject
# from Qt 4.6.

# workaround for emitting signals
class Emitter(QtCore.QObject):
    signal = QtCore.pyqtSignal()
    def __init__(self):
        QtCore.QObject.__init__(self)

class LinescanItem(QtGui.QGraphicsItemGroup):
    """
    Tool for selecting a point or lines in horizontal and vertical direction
    within an image.
    """
    
    class MoveHandle(QtGui.QGraphicsEllipseItem):
        def __init__(self, parent):
            width = 10.0
            QtGui.QGraphicsEllipseItem.__init__(self,
                                                QtCore.QRectF(-width*.5,-width*.5,width,width),
                                                parent)
            self.linescan = parent
            self.setFlags(QtGui.QGraphicsItem.ItemIsMovable)
            self.setBrush(QtCore.Qt.white)
            
        def mouseMoveEvent(self, event):
            # check for valid move
            if not self.scene().sceneRect().contains(event.scenePos()): return
            # move linescan
            QtGui.QGraphicsEllipseItem.mouseMoveEvent(self, event)
            self.linescan.setLinescanPos(self.pos())
            
    def __init__(self, scene):
        QtGui.QGraphicsItemGroup.__init__(self)
        scene.addItem(self)
        self.setHandlesChildEvents(False)
        
        # add lines
        linePen = QtGui.QPen(QtCore.Qt.black, 1.0)
        self.lineHorizontal = scene.addLine(QtCore.QLineF(0,0,scene.sceneRect().width(),0),linePen)
        self.lineVertical = scene.addLine(QtCore.QLineF(0,0,0,scene.sceneRect().height()),linePen)
        self.addToGroup(self.lineHorizontal)
        self.addToGroup(self.lineVertical)
        
        # add move handle
        self.handle = self.MoveHandle(self)
        self.setZValue(1.0)
        self.addToGroup(self.handle)
                
        # signals and slots
        scene.sceneRectChanged.connect(self.handleSceneResize)
        self.emitter = Emitter()
        
    def handleSceneResize(self, rect):
        self.lineHorizontal.setLine(0, 0, rect.width(), 0)
        self.lineVertical.setLine(0, 0, 0, rect.height())
        self.update()
        
    def setLinescanPos(self, point):
        """
        Set the selected linescan position to a given point.
        
        :param point: (QPoint) New linescan position.
        """
        self.lineHorizontal.setPos(0, point.y())
        self.lineVertical.setPos(point.x(), 0)
        self.handle.setPos(point)
        self.emitter.signal.emit()
        self.update()
        
    def getLinescanPos(self):
        """
        Retrieve the current linescan position.
        
        :returns: (Qpoint) Linescan position
        """
        return self.handle.pos().toPoint()


class ResizableRectItem(QtGui.QGraphicsRectItem):
    """
    Tool for selecting rectangular regions within an image.
    """
    
    class ResizeHandle(QtGui.QGraphicsRectItem):
        def __init__(self, parent):
            QtGui.QGraphicsRectItem.__init__(self, QtCore.QRectF(-5,-5,7,7), parent)
            self.rectItem = parent
            self.setFlags(QtGui.QGraphicsItem.ItemIsMovable)
            self.setBrush(QtCore.Qt.white)
        def mouseMoveEvent(self, event):
            # check for valid resize move
            distance = event.scenePos() - self.rectItem.scenePos()
            if distance.x() < 25 or distance.y() < 25: return
            # resize parent rect
            QtGui.QGraphicsRectItem.mouseMoveEvent(self, event)
            self.rectItem.resizeRect(self.pos().x(), self.pos().y())
            
    def __init__(self, scene):
        defaultWidth = 50; defaultHeight = 25
        QtGui.QGraphicsRectItem.__init__(self, 0, 0, defaultWidth, defaultHeight)
        scene.addItem(self)
        self.setFlags(QtGui.QGraphicsItem.ItemIsMovable)
        
        # add resize handle
        self.handleItem = self.ResizeHandle(self)
        self.handleItem.setPos(defaultWidth, defaultHeight)
        # add text label
        self.labelItem = QtGui.QGraphicsTextItem("", self)
        #self.labelItem.setPos(3, 3)
        
        # signals
        self.emitter = Emitter()
        
    def setColor(self, color):
        """
        Change the color of the selection rectangle.
        
        The borders and the background will be colored with the given color.
        The background will be slightly transparent, so the image behind the
        rectangle stays visible.
        
        :param color: (QColor) New color.
        """
        color = QtGui.QColor(color)
        color.setAlpha(50)
        self.setBrush(QtGui.QBrush(color))
        color.setAlpha(255)
        self.setPen(QtGui.QPen(color, 1.0))

    def setText(self, text):
        # TODO: doesnt do anything yet
        self.labelItem.setPlainText(text)
        
    def resizeRect(self, width, height):
        """
        Change the size of the current rectangle without changing its position.
        
        :param width: (int) New width in pixels.
        :param height: (int) New height in pixels.
        """
        rect = self.rect()
        rect.setWidth(width)
        rect.setHeight(height)
        self.setRect(rect)
    
    def getRect(self):
        """
        Return the currently selected rectangle coordinates.
        
        :returns: (QRect) Selection rectangle.
        """
        return self.rect()

class GraphWidget(QtGui.QGraphicsView):
    """
    The GraphWidget is a QGraphicsView derived widget for simple plotting of one dimensional
    data. Multiple colored plots are supported, so it may be used to display data and fit curves
    within one figure. Its main purpose is to serve as linescan-plotting widget for :class:`Data2DViewer`.
    
    :param parent: Parent parameter of QWidget objects.
    :param orientation: Qt.Horizontal or Qt.Vertical.
    """
    
    colors = {"k": QtCore.Qt.black,
              "r": QtCore.Qt.red,
              "g": QtCore.Qt.green,
              "b": QtCore.Qt.blue,
              }
    
    def __init__(self, parent = None, orientation = QtCore.Qt.Horizontal):
        QtGui.QGraphicsScene.__init__(self, parent)
        self.setFrameStyle(QtGui.QFrame.NoFrame)
        self.setAntialiasing(True)
        self.orientation = orientation
        
        # setup scene
        self.scene = QtGui.QGraphicsScene(self)
        self.setScene(self.scene)
        
        # path items
        self.pathItem_list = []
    
    def setAntialiasing(self, enabled):
        """
        Enable or disable antialiasing for performance control.
        
        :param enabled: (bool)
        """
        self.setRenderHint(QtGui.QPainter.Antialiasing, enabled)
        
    def clear(self):
        """
        Clear all plots from this widget.
        """
        for pathItem in self.pathItem_list:
            self.scene.removeItem(pathItem)
            
    def addPlot(self, X, Y, color = "k"):
        """
        Add a new plot to this widget. You can define x and y data as well as
        the color of the plot line.
        
        :param X: (ndarray) x points
        :param Y: (ndarray) y points
        :param color: (str) Color of the plot ("k", "r", "g", "b").
        """
        if color in self.colors: color = self.colors[color] 
        
        path = QtGui.QPainterPath()
        path.moveTo(X[0],Y[0])
        for i in xrange(1, len(X)):
            path.lineTo(X[i],Y[i])
        self.pathItem_list.append(self.scene.addPath(path, QtGui.QPen(color)))
        
    def updatePlot(self, index, X, Y):
        """
        Change the xy data of an existing plot.
        
        :param index: (int) Index of the plot to update (starts at 0).
        :param X: (ndarray) x points
        :param Y: (ndarray) y points
        """
        path = QtGui.QPainterPath()
        path.moveTo(X[0],Y[0])
        for i in xrange(1, len(X)):
            path.lineTo(X[i],Y[i])
        self.pathItem_list[index].setPath(path)
        
    def showPlot(self, index, visible = True):
        """
        Change the visibility of the plot with the given index.
        
        :param index: (int) Index of the plot.
        :param visible: (bool) True if the plot should become visible.
        """
        self.pathItem_list[index].setVisible(visible)
        
    def hidePlot(self, index):
        """
        Hide the plot with the given index.
        
        :param index: (int)
        """
        self.pathItem_list[index].hide()
        
    def resizeEvent(self, event):
        QtGui.QGraphicsView.resizeEvent(self, event)
       
        # update scene scales
        self.resetMatrix()
        h = event.size().height()
        w = event.size().width()

        if self.orientation == QtCore.Qt.Horizontal:
            self.scene.setSceneRect(QtCore.QRectF(0,0,1,1))
            self.scale(w,-h)
        else:
            self.rotate(-90);
            self.scene.setSceneRect(QtCore.QRectF(0,0,1,1))
            self.scale(-h,-w)
            
class ImageWidget(QtGui.QGraphicsView):
    """
    A image viewer derived from QGraphicsView.
    """
    
    def __init__(self, parent = None):
        QtGui.QGraphicsScene.__init__(self, parent)
        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setFrameStyle(QtGui.QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # setup scene
        scene = QtGui.QGraphicsScene(self)
        self.setScene(scene)
        self.imageItem = scene.addPixmap(QtGui.QPixmap())
        self.imageItem.setZValue(-1)
        self.toolItems = []
        
        # set defaults
        self.setZRange(None, None)
        self.imageData = numpy.zeros([1,1])
        self.allowScaling = False
    
    def heightForWidth(self, w):
        return int(self.imageData.shape[0] * float(w)/self.imageData.shape[1])
    
    def setAllowScaling(self, allow):
        self.allowScaling = allow
        if allow:
            self.setMinimumSize(1, 1)
        else:
            self.setMinimumSize(self.imageItem.pixmap().size())
    
    def resizeEvent(self, event):
        if self.allowScaling: self.fitInView(self.sceneRect(), mode=1)
           
    def setImageData(self, data, colormap = "gray"):
        # store new image data        
        self.imageData = data
        # create a pixmap from qimage
        if colormap == "hot":
            qimage = image.createQImage(self.imageData, vmin=self.zrange[0], vmax=self.zrange[1], cmap=image.cmap_hot)
        elif colormap == "wjet":
            qimage = image.createQImage(self.imageData, vmin=self.zrange[0], vmax=self.zrange[1], cmap=image.cmap_wjet)
        elif colormap == "jet":
            qimage = image.createQImage(self.imageData, vmin=self.zrange[0], vmax=self.zrange[1], cmap=image.cmap_jet)
        else:
            qimage = image.createQImage(self.imageData, vmin=self.zrange[0], vmax=self.zrange[1], cmap=image.cmap_gray)
        
        pixmap = QtGui.QPixmap.fromImage(qimage).copy()
        # apply new pixmap and rescale the scene 
        self.imageItem.setPixmap(pixmap)
        self.scene().setSceneRect(0, 0, pixmap.width(), pixmap.height())
        # if the image is not to be scaled, set new minimum size
        if not self.allowScaling:
            self.setMinimumSize(self.imageItem.pixmap().size())
        
    def setZRange(self, zmin = None, zmax = None):
        self.zrange = [zmin,zmax]
        
    def addRectSelection(self, color = QtCore.Qt.black, text = "", rect = QtCore.QRect()):
        rect = ResizableRectItem(self.scene())
        rect.setColor(color)
        return rect
        
    def addLineSelection(self, pos = QtCore.QPointF()):
        linescan = LinescanItem(self.scene())
        linescan.setLinescanPos(pos)
        return linescan
        
class Data2DViewer(QtGui.QWidget):
    """
    A data viewer constructed of other classes in this module. Displays an image of the
    data supplied in the center, adds a linescan tool and shows x and y plots of line-slices.
    """
    
    def __init__(self, *args, **kwargs):
        # setup widgets
        QtGui.QWidget.__init__(self, *args, **kwargs)
        self.linescanXWidget = GraphWidget(self, QtCore.Qt.Horizontal)
        self.linescanYWidget = GraphWidget(self, QtCore.Qt.Vertical)
        self.histogramWidget = GraphWidget(self, QtCore.Qt.Horizontal)
        self.linescanXWidget.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        self.linescanYWidget.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)        
        self.histogramWidget.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        self.linescanXWidget.setMinimumHeight(100)
        self.linescanYWidget.setMinimumWidth(100)
        self.linescanXWidget.setAntialiasing(False)
        self.linescanYWidget.setAntialiasing(False)
        self.histogramWidget.setAntialiasing(False)
        self.imageWidget = ImageWidget(self)
        self.imageWidget.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        
        # add plots for image linescan
        self.linescanXWidget.addPlot([0], [0])
        self.linescanYWidget.addPlot([0], [0])
        self.histogramWidget.addPlot([0], [0])
        
        # layout widgets
        layout = QtGui.QGridLayout(self)
        layout.addWidget(self.imageWidget, 0, 0)
        layout.addWidget(self.linescanXWidget, 1, 0)
        layout.addWidget(self.linescanYWidget, 0, 1)
        layout.addWidget(self.histogramWidget, 1, 1)
        layout.setSpacing(0)
        self.setLayout(layout)
        
        # add linscan to scene
        self.linescanItem = self.imageWidget.addLineSelection()
        self.linescanItem.emitter.signal.connect(self.handleLinescanChange)
        
        # add selection rectangle
        #self.selectionItem = self.imageWidget.addRectSelection()
        #self.imageWidget.scene().removeItem(self.selectionItem)
        
        # defaults
        self.setImageData(numpy.zeros([100, 100], dtype=float))
        
    def setImageData(self, data, colormap="gray"):
        # set new image
        data_old = self.imageWidget.imageData
        self.imageWidget.setImageData(data, colormap=colormap)
        
        # set new linescan position for new image shapes 
        if (numpy.array(data.shape) != data_old.shape).any():
            self.linescanItem.setLinescanPos(QtCore.QPointF(data.shape[1]*.5, data.shape[0]*.5))
        
        # update histogram
        hist, borders = numpy.histogram(data, range=(0.,1.), bins=20)
        hist = hist.astype(float)
        hist *= 1. / hist.max()
        hist = hist.repeat(2)
        borders = borders.repeat(2)
        self.histogramWidget.updatePlot(0, borders[1:-1], hist)
        
    def handleLinescanChange(self):
        data = self.imageWidget.imageData
        pos = self.linescanItem.getLinescanPos()
        x,y = pos.x(), pos.y()
        h,w = data.shape
        if x<0 or y<0 or x>=w or y>=h: return
        X = numpy.linspace(0, 1, w)
        Y = numpy.linspace(0, 1, h)
        self.linescanXWidget.updatePlot(0, X, data[y,:])
        self.linescanYWidget.updatePlot(0, Y, data[:,x])

def testWidgets():
    # sample data
    Y,X = numpy.ogrid[-1:1:512j,-1:1:768j]
    data = 1 - numpy.sin(2*X)**3 + numpy.sin(-2*Y)**3
    data -= data.min()
    data /= data.max()
    data += numpy.random.random(data.shape) * (1+data) * 0.2
    data -= data.min()
    data /= data.max()
    
    app = QtGui.QApplication(sys.argv)
    # viewer with linescans and crosshair
    win1 = Data2DViewer()
    win1.show()
    win1.setImageData(data, colormap="wjet")
    
    # viewer only
    win2 = ImageWidget()
    win2.setAllowScaling(True)
    win2.setImageData(data, colormap="gray")
    win2.addRectSelection("red", "Selection")
    win2.show()
    app.exec_()

if __name__ == "__main__":
    testWidgets()

