"""
Matplotlib Widget
-----------------

"""

import numpy as np
from PyQt4 import QtGui

# mpl stuff
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure

from qao.utils import unique_mean

class MatplotlibWidget(QtGui.QWidget):
    """
    MatplotlibWidget is a plotting widget based on matplotlib.
    
    While the FigureCanvasQTAgg widget provided by matplotlib itself is
    intended for easy matplotlib integration in Qt applications, this
    widget focuses on hiding matplotlib internals from the user and
    adding new features.
    
    As the widget is designed to be used within applications,
    MatplotlibWidget provides methods for updating the data of
    graphs without clearing the figure and setting it up from scratch.
    This optimizes performance when the data is changed frequently.
    
    After creating a MatplotlibWidget, you add a new plots to the
    figure by calling :func:`addGroupedPlot`. A new feature is the
    use of so called `plot groups`. When calling :func:`newPlotGroup`,
    all subsequent calls to :func:`addGroupedPlot` will add new plots
    to a different group, which will change the appearance of the
    plots. The plot will be updated when calling :func:`draw`.
    
    All plots within a group will have the same color but different
    line styles. Each group however will differ in color. You can
    choose a split presentation, where each group will be displayed
    in its own graph.
    
    You can use :func:`updateGroupedPlot` for changing the plot-data,
    or :func:`clearPlots` for clearing the whole figure and setting
    it up from scratch.
    
    :param parent: Parent parameter of QWidget, usually None.
    :param autoscaleBn: (bool) Add autoscale button to panel.
    
    Example:
    
    .. literalinclude:: ../src/qao/gui/MatplotlibWidget.py
        :pyobject: testMatplotlibWidget
    """
    
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
        """
        Removes all plots from the figure and deletes all plot groups.
        """
        self.plotPointGroups = []
        self.plotLineGroups = []
        self._needSetupFigure = True
    
    def resizeEvent(self, event):
        w, h = event.size().width(), event.size().height()
        self.fig.subplots_adjust(left = 30./w, right = 1-5./w, top = 1-5./h, bottom = 50./h, hspace = 70./h)
        
    def newPlotGroup(self):
        """
        Creates a new group for further plots added to the figure.
        
        Plots within a group have different line styles. Plots of different
        groups will receive different colors. In the split presentation, each
        plot group will be displayed in its own graph.
        
        :returns: (int) Group id assigned for updating plots later on.
        """
        assert len(self.plotPointGroups) < len(self.colors), "maximum number of plot groups reached"
        self.plotPointGroups.append([])
        self.plotLineGroups.append([])
        self._needSetupFigure = True
        
        return len(self.plotLineGroups) - 1

    def addGroupedPlot(self, label, x, y):
        """
        Creates a new plot within the last created plot group.
        
        Generally, this function creates two plots for a given dataset.
        The first plot is a scatter plot, showing all x and y values.
        The second plot is a line plot, averaging over y values if there
        are multiple occurrences of x values.
        
        The plot data can be updated by calling :func:`updateGroupedPlot`. 
        
        :param label: (str) Label to be displayed in the figure legend.
        :param x: (ndarray) Array or list of x values.
        :param y: (ndarray) Array or list of y values.
        :returns: (int) Plot id assigned for updating plots later on.
        """
        if not self.plotPointGroups: self.newPlotGroup()
        assert len(self.plotPointGroups[-1]) < len(self.linestyles), "maximum number of plot group elements reached"
        pointGroup = self.plotPointGroups[-1]
        lineGroup  = self.plotLineGroups[-1]
        xu, yu = unique_mean(x, y)
        points = matplotlib.lines.Line2D(x, y,
                                       color = self.colors[len(self.plotPointGroups)-1],
                                       marker = "o", ls = "")
        line = matplotlib.lines.Line2D(xu, yu, label = label,
                                       color = self.colors[len(self.plotLineGroups)-1],
                                       ls = self.linestyles[len(lineGroup)])
        pointGroup.append(points)
        lineGroup.append(line)
        self._needSetupLines = True
        
        return len(lineGroup) - 1
    
    def updateGroupedPlot(self, group, plot, x, y):
        """
        Update the data for a single plot.
        
        The plot you want to update is defined by the group and plot
        id. Both numbers are starting at zero and simply increment when
        new groups/plots are added by the user, so the second plot within
        the first group is (group=0, plot=1).
        
        :param group: (int) Group id of the plot.
        :param plot: (int) Plot id of the plot.
        :param x: (ndarray) New x values for plotting.
        :param y: (ndarray) New y values for plotting.
        """
        line   = self.plotLineGroups[group][plot]
        points = self.plotPointGroups[group][plot]
        xu, yu = unique_mean(x, y)
        line.set_xdata(xu)
        line.set_ydata(yu)
        points.set_xdata(x)
        points.set_ydata(y)
        self._needRescale = True
    
    def setGropPlotStyle(self, style = "combined"):
        """
        Change the presentation style regarding the plot groups.
        
        The default behavior is a combined presentation, where
        all plots are displayed in the same graph. The split
        view assignes one graph for each plot group.
        
        :param style: (str) Plot style, may be 'combined' or 'individual'.
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
        """
        Convenience function for changing the plot style.
        
        If the currently active style is 'combined', the
        style will chance to 'individual' and vice versa.
        
        .. seealso:: :func:`setGropPlotStyle`
        """
        if self.groupPlotStyle == "combined":
            self.setGropPlotStyle("individual")
        else:
            self.setGropPlotStyle("combined")
        self.draw()
    
    def toggleAutoscale(self):
        self.draw() 
    
    def setXLabel(self, label):
        """
        Change the label for the x-axis.
        
        :param label: (str) Text displayed under x-axis.
        """
        self.xlabel = label
    
    def draw(self):
        """
        Redraw the current figure.
        
        Changes to the plot data, labels etc. will be visible
        after calling this method.
        """
        if self._needSetupFigure: self._setupFigure()
        if self._needSetupLines: self._setupLines()
        if self._needRescale: self._setupScale()
        self.canvas.draw()

    def _setupFigure(self):
        self._needSetupFigure = False
        # clear figure and setup axes for plot groups
        self.fig.clf()
        nGroups = len(self.plotLineGroups)
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
        if not len(self.plotLineGroups): return
        self._needSetupLines = False
        self._needRescale = False
        # clear lines from axes
        for ax in self.axes: ax.lines = []
        # every group of lines is plotted to one axes
        for ax, pointlines, lines in zip(self.axes, self.plotPointGroups, self.plotLineGroups):
            for line in lines:
                ax.add_line(line)
                line.set_transform(ax.transData)
            for points in pointlines:
                ax.add_line(points)
                points.set_transform(ax.transData)
            ax.autoscale_view()
            ax.legend(loc=0)
    
    def _setupScale(self):
        self._needRescale = False
        if not self.actionAutoscale.isChecked(): return
        if not len(self.plotLineGroups): return
        for ax in self.axes:
            ax.relim()
            ax.autoscale()

##########################################################################

def testMatplotlibWidget():
    app = QtGui.QApplication([])
    
    win = MatplotlibWidget()
    win.show()

    x = np.arange(10); y = x**2
    win.setGropPlotStyle("combined")
    win.newPlotGroup()
    win.addGroupedPlot("one, 1st", x, y)
    win.addGroupedPlot("one, 2nd", x, y-15)
    win.newPlotGroup()
    win.addGroupedPlot("two, 1st", -x, y)
    win.addGroupedPlot("two, 2nd", -x, y-15)
    win.setXLabel("x axis")
    win.draw()

    app.exec_()

if __name__ == "__main__":
    testMatplotlibWidget()
