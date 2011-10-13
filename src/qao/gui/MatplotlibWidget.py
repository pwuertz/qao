import numpy as np
from PyQt4 import QtGui

# mpl stuff
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure

class MatplotlibWidget(QtGui.QWidget):
    colors = 'bgrkcm'
    markers = 'os^vd'
    linestyles = ['-', '--', '-.', ':']

    def __init__(self, parent=None, autoscaleBn = False):
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
        self.actionAutoscale = self.navigation.addAction("Auto", self.toggleAutoscale)
        self.actionAutoscale.setCheckable(True)
        self.actionAutoscale.setChecked(True)
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.canvas)
        layout.addWidget(self.navigation)
        
        # init other stuff
        self.xlabel = ""
        self._needSetupFigure = True
        self._needSetupLines  = True
        self._needRescale     = True
        self.clearPlots()
        self.setGropPlotStyle("combined")
    
    def clearPlots(self):
        self.plotGroups = []
        self._needSetupFigure = True
    
    def resizeEvent(self, event):
        w, h = event.size().width(), event.size().height()
        self.fig.subplots_adjust(left = 30./w, right = 1-5./w, top = 1-5./h, bottom = 50./h, hspace = 70./h)
        
    def newPlotGroup(self):
        assert len(self.plotGroups) < len(self.colors)
        self.plotGroups.append([])
        self._needSetupFigure = True

    def addGroupedPlot(self, label, x, y):
        if not self.plotGroups: self.newPlotGroup()
        assert len(self.plotGroups[-1]) < len(self.linestyles)
        lineGroup = self.plotGroups[-1]
        line = matplotlib.lines.Line2D(x, y, label = label,
                                       color = self.colors[len(self.plotGroups)-1],
                                       ls = self.linestyles[len(lineGroup)])
        lineGroup.append(line)
        self._needSetupLines = True
    
    def updateGroupedPlot(self, group, item, x, y):
        line = self.plotGroups[group][item]
        line.set_xdata(x)
        line.set_ydata(y)
        self._needRescale = True
    
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

        # update figure layout
        self._needSetupFigure = True
    
    def toggleGroupPlotStyle(self):
        if self.groupPlotStyle == "combined":
            self.setGropPlotStyle("individual")
        else:
            self.setGropPlotStyle("combined")
        self.draw()
    
    def toggleAutoscale(self):
        self.draw() 
    
    def setXLabel(self, label):
        self.xlabel = label
    
    def draw(self):
        if self._needSetupFigure: self._setupFigure()
        if self._needSetupLines: self._setupLines()
        if self._needRescale: self._setupScale()
        self.canvas.draw()

    def _setupFigure(self):
        self._needSetupFigure = False
        # clear figure and setup axes for plot groups
        self.fig.clf()
        nGroups = len(self.plotGroups)
        if not nGroups: return
        if self.groupPlotStyle == "combined":
            self.axes = [self.fig.add_subplot(1,1,1)] * nGroups
        elif self.groupPlotStyle == "individual":
            self.axes  = [self.fig.add_subplot(nGroups,1,1)]
            self.axes += [self.fig.add_subplot(nGroups,1,i, sharex=self.axes[0]) for i in range(2, nGroups+1)]
        self.axes[-1].set_xlabel(self.xlabel)
        # axes prepared, add lines to axes
        self._setupLines()
    
    def _setupLines(self):
        self._needSetupLines = False
        self._needRescale = False
        # clear lines from axes
        for ax in self.axes: ax.lines = []
        # every group of lines is plotted to one axes
        for ax, lines in zip(self.axes, self.plotGroups):
            for line in lines:
                ax.add_line(line)
                line.set_transform(ax.transData)
            ax.autoscale_view()
            ax.legend(loc=0)
    
    def _setupScale(self):
        self._needRescale = False
        if not self.actionAutoscale.isChecked(): return
        for ax in self.axes:
            ax.relim()
            ax.autoscale()

if __name__ == "__main__":
    app = QtGui.QApplication([])
    palette = app.palette()
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor("black"))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor("white"))
    app.setPalette(palette)
    
    win = MatplotlibWidget()
    win.show()

    x = np.arange(10); y = x**2
    win.setGropPlotStyle("combined")
    win.newPlotGroup()
    win.addGroupedPlot("one, 1st", x, y)
    win.addGroupedPlot("one, 2nd", x, y-2)
    win.newPlotGroup()
    win.addGroupedPlot("two, 1st", -x, y)
    win.addGroupedPlot("two, 2nd", -x, y-2)
    win.setXLabel("x axis")
    win.draw()


    app.exec_()
    