import sys, os, numpy as np
from PyQt4 import QtCore, QtGui

# mpl stuff
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure

class MatplotlibWidget(QtGui.QWidget):
    colors = 'bgrkcm'
    markers = 'os^vd'
    linestyles = ['-', '--', '-.', ':']

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        # canvas
        font = self.font()
        windowColor = str(self.palette().window().color().name())
        matplotlib.rc('font', family=str(font.family()), size=.9*font.pointSize(), weight="normal")
        matplotlib.rc('figure', facecolor=windowColor, edgecolor=windowColor)
        self.fig = Figure(dpi=self.logicalDpiX())
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)

        # navigation
        self.navigation = NavigationToolbar(self.canvas, self, coordinates=False)
        self.actionGroupPlotStyle = self.navigation.addAction("Split", self.toggleGroupPlotStyle)
        self.actionGroupPlotStyle.setCheckable(True)
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.canvas)
        layout.addWidget(self.navigation)
        
        # init other stuff
        self.clearPlots()
        self.setGropPlotStyle("combined")
    
    def clearPlots(self):
        try:
            for ax in self.axes(): ax.lines.clear()
        except:
            pass
        self.plotGroups = []
        self.setXLabel("")
        
    def newPlotGroup(self):
        self.plotGroups.append([])

    def addGroupedPlot(self, label, x, y):
        if not self.plotGroups: self.newPlotGroup()
        self.plotGroups[-1].append((label, x, y))
    
    def setGropPlotStyle(self, style = "combined"):
        """
        style may be 'combined' or 'individual'
        """
        if style == "combined":
            self.actionGroupPlotStyle.setChecked(False)
            self.groupPlotStyle = "combined"
        elif style == "individual":
            self.actionGroupPlotStyle.setChecked(True)
            self.groupPlotStyle = "individual"
        else:
            raise Exception("invalid group plot style")
    
    def toggleGroupPlotStyle(self):
        if self.groupPlotStyle == "combined":
            self.setGropPlotStyle("individual")
        else:
            self.setGropPlotStyle("combined")
        self.draw()
    
    def setXLabel(self, label):
        self.xlabel = label
    
    def draw(self):
        nPlotGroups = len(self.plotGroups)
        if not nPlotGroups: return
        if self.groupPlotStyle == "individual":
            self._setupFigure(nPlotGroups)
            axes = self.axes
        else:
            self._setupFigure(1)
            axes = [self.axes[0]]*nPlotGroups
        
        # for every set of plot groups plot...
        for ax, color, plotGroup in zip(axes, self.colors, self.plotGroups):
            # for every plot in group
            for linestyle, groupItem in zip(self.linestyles, plotGroup):
                label, x, y = groupItem
                ax.plot(x, y, label = label, color = color, ls = linestyle)
            ax.legend(loc=0)
        
        axes[-1].set_xlabel(self.xlabel)
        #self.axes.relim() # only required when using set_data on line2d
        #self.axes[0].autoscale_view()
        self.canvas.draw()

    def _setupFigure(self, nAxes = 1):
        try:
            nAxesOld = self.nAxes
        except:
            nAxesOld = 0
        if nAxesOld != nAxes:
            self.fig.clf()
            self.axes = [self.fig.add_subplot(nAxes,1,i) for i in range(1, nAxes+1)]
            self.axes[0].set_autoscale_on(True)
        else:
            for ax in self.axes: ax.cla()

if __name__ == "__main__":
    app = QtGui.QApplication([])
    palette = app.palette()
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor("black"))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor("white"))
    app.setPalette(palette)
    
    win = MatplotlibWidget()
    win.show()

    x = np.arange(10); y = x**2
    win.setGropPlotStyle("individual")
    win.newPlotGroup()
    win.addGroupedPlot("2", x, y)
    win.addGroupedPlot("3", x, y-2)
    win.newPlotGroup()
    win.addGroupedPlot("2", -x, y)
    win.addGroupedPlot("3", -x, y-2)
    win.setXLabel("x axis")
    win.draw()


    app.exec_()
    