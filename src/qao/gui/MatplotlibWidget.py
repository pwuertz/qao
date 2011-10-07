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
        self.plotGroups = []
        
    def newPlotGroup(self):
        assert len(self.plotGroups) < len(self.colors)
        self.plotGroups.append([])

    def addGroupedPlot(self, label, x, y):
        if not self.plotGroups: self.newPlotGroup()
        assert len(self.plotGroups[-1]) < len(self.linestyles)
        lineGroup = self.plotGroups[-1]
        line = matplotlib.lines.Line2D(x, y, label = label,
                                       color = self.colors[len(self.plotGroups)-1],
                                       ls = self.linestyles[len(lineGroup)])
        lineGroup.append(line)
        
    
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
        
        # every group of lines is plottet to one axes
        for ax, lineGroup in zip(axes, self.plotGroups):
            for line in lineGroup:
                ax.add_line(line)
                line.set_transform(ax.transData)
            ax.autoscale_view()
            ax.legend(loc=0)
        
        axes[-1].set_xlabel(self.xlabel)
        self.canvas.draw()

    def _setupFigure(self, nAxes = 1):
        if "axes" not in self.__dict__: self.axes = []
        if len(self.axes) != nAxes:
            self.fig.clf()
            self.axes = [self.fig.add_subplot(nAxes,1,i) for i in range(1, nAxes+1)]
        else:
            for ax in self.axes: ax.lines = []

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
    win.addGroupedPlot("one, 1st", x, y)
    win.addGroupedPlot("one, 2nd", x, y-2)
    win.newPlotGroup()
    win.addGroupedPlot("two, 1st", -x, y)
    win.addGroupedPlot("two, 2nd", -x, y-2)
    win.setXLabel("x axis")
    win.draw()


    app.exec_()
    