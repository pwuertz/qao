import time
import os
import csv
import numpy as np
from StringIO import StringIO
from PyQt4 import QtGui, QtCore

import matplotlib
from MatplotlibWidget import MatplotlibWidget

ID_KEY_DEFAULT = "id"

class DataTable(QtCore.QObject):
    cleared      = QtCore.pyqtSignal()
    rowInserted  = QtCore.pyqtSignal(int)
    colInserted  = QtCore.pyqtSignal(int)
    rowRemoved   = QtCore.pyqtSignal(int)
    colRemoved   = QtCore.pyqtSignal(int)
    dataChanged  = QtCore.pyqtSignal(int, int, int, int)
    flagChanged = QtCore.pyqtSignal(int, str, bool)
    
    def __init__(self, id_key=None):
        if not id_key: id_key = ID_KEY_DEFAULT
        QtCore.QObject.__init__(self)
        self.id_key = id_key
        self.clear()
    
    def clear(self):
        """
        clear/init table
        """
        # column information
        colInfos  = ["name", "flags", "dtype", "expression"]
        dtColInfo = np.dtype({'names': colInfos, 'formats': [object]*len(colInfos)})
        # create empty tables
        self.colInfo = np.array([], dtype=dtColInfo)
        self.data = np.empty((0, len(self.colInfo)), dtype=object)
        # emit cleared, and add standard columns
        self.cleared.emit()
        self.addColumns([self.id_key])
        self.addColumns(["discard"]); self.colInfo[1]["dtype"] = "bool"; self.discardCol = 1;
        self.addColumns(["comment"]); self.colInfo[2]["dtype"] = "str"; self.setFlag(2, "editable")
        self.setFlagAll("persistent", True)
        
        self._modified = False
    
    def save(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        fh = open(filename, "w")
        
        data_list = self.data.tolist()
        if ext == ".py":
            fh.writelines(["#", ",".join(self.colInfo["name"]), "\n"])
            fh.write(repr(data_list))
        elif ext == ".csv":
            fh.writelines(["#", ",".join(self.colInfo["name"]), "\n"])
            csvfile = csv.writer(fh)
            csvfile.writerows(data_list)
        else:
            return False
        
        fh.close()
        self._modified = False
    
    def __getitem__(self, index):
        return self.data.__getitem__(index)
    
    def __setitem__(self, index, value):
        # setitem on real array
        self.data.__setitem__(index, value)
        self._modified = True
        # determine changes and emit signal
        if type(index) == tuple:
            indices = [np.arange(s)[i] for s, i in zip(self.data.shape, index)]
            r_from, r_to = np.min(indices[0]), np.max(indices[0])
            c_from, c_to = np.min(indices[1]), np.max(indices[1])
            self.dataChanged.emit(r_from, r_to, c_from, c_to)
        else:
            indices = np.arange(self.data.shape[0])[index]
            r_from, r_to = np.min(indices), np.max(indices)
            self.dataChanged.emit(r_from, r_to, 0, self.data.shape[1]-1)

    def addColumns(self, newColNames):
        """
        function for adding columns, only new column names are added
        """
        # determine new columns to be inserted
        oldColNames = self.colInfo["name"].tolist()
        newColNames = [name for name in newColNames if name not in oldColNames]
        nNewCols    = len(newColNames)
        if not nNewCols: return 0
        
        self._modified = True
        # add each new column
        for name in newColNames:
            # enlarge data and column info table
            pos = len(self.colInfo)
            newColInfo = (name, set(), "object", "")
            self.colInfo = np.insert(self.colInfo, pos, newColInfo)
            self.data    = np.insert(self.data   , pos, None, axis=1)
            # signal new column
            self.colInserted.emit(pos)
    
    def removeColumn(self, col):
        """
        remove a column from the table
        """
        if self.checkFlag(col, "persistent"): return
        self.colInfo = np.delete(self.colInfo, col)
        self.data = np.delete(self.data, col, axis=1)
        
        self._modified = True
        self.colRemoved.emit(col)
        
    def removeRow(self, row):
        """
        remove a row from the table
        """
        self.data = np.delete(self.data, row, axis=0)
        
        self._modified = True
        self.rowRemoved.emit(row)
    
    def setGrouping(self, col, enabled = True):
        """
        use a column to group returned values by elements of this column
        """
        self.setFlagUnique(col, "group", enabled)
    
    def setDynamic(self, col, expression):
        """
        set expression to be evaluated whenever data in a row changes
        remove expression by passing a False expression
        """
        if col == 0: return # not allowed for id column
        
        if expression:
            self.setFlag(col, "dynamic")
            self.colInfo[col]["expression"] = expression
            self.updateDynamic(row=None, col=col)
        else:
            self.setFlag(col, "dynamic", False)
            self.colInfo[col]["expression"] = ""
    
    def updateDynamic(self, row = None, col = None):
        """
        recalculate values of dynamic columns.
        if row or column is None, recalculate all cells.
        """
        # determine which cells to update
        dynCols = self.searchFlag("dynamic")
        if col not in dynCols: return
        if row is None:
            rows = range(self.data.shape[0])
        else:
            rows = [row]
        if col is None:
            cols = dynCols
        else:
            cols = [col]
        
        if not rows: return
        
        # emit dataChanged for recalculated cells
        self._recalculateDynamic(rows, cols)
        for col in cols:
            self.dataChanged.emit(rows[0], rows[-1], col, col)
    
    def _recalculateDynamic(self, rows, cols):
        """
        internal recalculation of dynamic expressions
        not to be called from outside
        """
        self._modified = True
        # evaluate dynamic expressions for each row
        colNames = self.colInfo["name"].tolist()
        for row in rows:
            # build value dictionary for this row
            valuedict = dict()
            for key, val in zip(colNames, self.data[row].tolist()):
                valuedict[key.replace(' ', '_')] = val
            # evaluate each dynamic expression
            for col in cols:
                try:
                    result = eval(self.colInfo[col]["expression"], valuedict)
                except:
                    result = None
                self.data[row, col] = result 

    def toggleFlag(self, col, flag):
        """
        toggle a flag on a column
        """
        isSet = self.checkFlag(col, flag)
        self.setFlag(col, flag, enabled=not isSet)

    def setFlag(self, col, flag, enabled = True):
        """
        set a flag on a column
        """
        flags  = self.colInfo[col]["flags"]
        nflags = len(flags)
        if enabled:
            flags.add(flag)
        else:
            flags.discard(flag)
        if nflags != len(flags): self.flagChanged.emit(col, flag, enabled)
    
    def setFlagUnique(self, col, flag, enabled = True):
        """
        set flag on a column, unset this flag on other columns
        """
        for c in range(len(self.colInfo)):
            if c != col:
                self.setFlag(c, flag, enabled = False)
        self.setFlag(col, flag, enabled)

    def setFlagAll(self, flag, enabled = True):
        """
        clear flag from all columns
        """
        for i in range(len(self.colInfo)): self.setFlag(i, flag, enabled)
    
    def checkFlag(self, col, flag):
        """
        check if a flag is set on a column
        """
        return flag in self.colInfo[col]["flags"]
    
    def searchFlag(self, flag):
        """
        return a list of columns with flag set
        """
        colFlags = self.colInfo["flags"]
        hasflag  = lambda i: flag in colFlags[i]
        return filter(hasflag, range(len(self.colInfo)))
    
    def insertData(self, data_dict):
        """
        insert data from data_dict, add rows and columns if necessary
        this also triggers reevaluation of dynamic expressions
        """
        # add new columns
        self.addColumns(data_dict.keys())
        
        # get id from data_dict and determine where to insert the data
        if self.id_key in data_dict:
            id = data_dict[self.id_key]
        else:
            print "insertData failed, '%s' not found" % self.id_key
            return
        itemindex = (self.data[:, 0] == id).nonzero()[0]
        if len(itemindex):
            # id found in table
            row = itemindex[0]
        else:
            # id not found, insert row
            row = np.searchsorted(self.data[:,0], id)
            self.data = np.insert(self.data, row, None, axis=0)
            self.data[row, 0] = id
        
        # finally insert data to row
        colNames = self.colInfo["name"].tolist()
        for key, val in data_dict.items():
            self.data[row, colNames.index(key)] = val
        
        # evaluate dynamic expressions
        self._recalculateDynamic([row], self.searchFlag("dynamic"))
        
        self._modified = True
        
        # emit signal
        if len(itemindex):
            self.dataChanged.emit(row, row, 0, self.data.shape[1]-1)
        else:
            self.rowInserted.emit(row)
    
    def getColumnValues(self, *columns):
        """
        get a list of rows containing values from all requested columns
        only rows with column values not-None are returned
        """
        # determine rows without None values
        rowsValid = np.not_equal(self.data[:, columns], None).all(axis=1)
        rowsDiscard = self.data[:, self.discardCol].astype(bool)
        rowsUsed = rowsValid * (~rowsDiscard)
        data = self.data[rowsUsed][:,columns].transpose()
        data = [data[i] for i in range(len(columns))]
        return data    
    
    def getColumnValuesGrouped(self, *columns):
        """
        tuples of group value and columns are returned for each unique value
        of the group-column (value, [C1,C2,...])
        """
        # in case no group column is set
        groupCols = self.searchFlag("group")
        if not len(groupCols): return [[None] + self.getColumnValues(*columns)]
        
        # determine rows without None values
        rowsValid = np.not_equal(self.data[:, columns], None).all(axis=1)
        rowsDiscard = self.data[:, self.discardCol].astype(bool)
        rowsUsed = rowsValid * (~rowsDiscard)
        
        # iterate over group values
        groupedColumnData = []
        groupVals = np.unique(self.data[:, groupCols[0]])
        for groupVal in groupVals:
            rowsGroup = np.equal(self.data[:, groupCols[0]], groupVal)
            data = self.data[rowsUsed*rowsGroup][:,columns].transpose()
            data = [data[i] for i in range(len(columns))]
            groupedColumnData.append([groupVal] + data)
        return groupedColumnData

class DataTableModel(QtCore.QAbstractTableModel):
    def __init__(self, dataTable): 
        QtCore.QAbstractTableModel.__init__(self)
        # connect signals from the data source
        self.dataTable = dataTable
        dataTable.cleared.connect(self.handleCleared)
        dataTable.rowInserted.connect(self.handleRowInserted)
        dataTable.colInserted.connect(self.handleColInserted)
        dataTable.rowRemoved.connect(self.handleRowRemoved)
        dataTable.colRemoved.connect(self.handleColRemoved)
        dataTable.dataChanged.connect(self.handleDataChanged)
        dataTable.flagChanged.connect(self.handleFlagChanged)
    
    def handleCleared(self):
        self.reset()
    
    def handleRowInserted(self, row):
        self.rowsInserted.emit(QtCore.QModelIndex(), row, row)

    def handleColInserted(self, col):
        self.columnsInserted.emit(QtCore.QModelIndex(), col, col)
    
    def handleRowRemoved(self, row):
        self.rowsRemoved.emit(QtCore.QModelIndex(), row, row)
    
    def handleColRemoved(self, col):
        self.columnsRemoved.emit(QtCore.QModelIndex(), col, col)

    def handleDataChanged(self, rowFrom, rowTo, colFrom, colTo):
        self.dataChanged.emit(self.index(rowFrom, colFrom), self.index(rowTo, colTo))
            
    def handleFlagChanged(self, col):
        self.headerDataChanged.emit(QtCore.Qt.Horizontal, col, col)
 
    def rowCount(self, parent = QtCore.QModelIndex()): 
        if parent.isValid():
            return 0
        return self.dataTable.data.shape[0]
 
    def columnCount(self, parent = QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return self.dataTable.data.shape[1]
    
    def flags(self, index):
        col = index.column()
        if self.dataTable.colInfo[col]["dtype"] == "bool":
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable
        elif self.dataTable.checkFlag(col, "editable"):
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            colName = self.dataTable.colInfo[section]["name"]
            if self.dataTable.checkFlag(section, "plotX"): colName += " (X)"
            if self.dataTable.checkFlag(section, "plotY"): colName += " (Y)"
            if self.dataTable.checkFlag(section, "group"): colName += " (G)"
            return colName
        
        #elif orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DecorationRole:
        #    return QtGui.QIcon()
        
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return " "
        
        return QtCore.QVariant()
 
    def data(self, index, role = QtCore.Qt.DisplayRole):
        row, col = index.row(), index.column()
        isBool = self.dataTable.colInfo[col]["dtype"] == "bool"
        
        if not index.isValid():
            return QtCore.QVariant()
        elif (role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole) and not isBool:
            val = self.dataTable[row, col]
            if val != None: return str(val)
            else: return None
        elif role == QtCore.Qt.BackgroundRole:
            return QtCore.QVariant() #return QtGui.QColor("gray")
        elif role == QtCore.Qt.DecorationRole:
            return QtCore.QVariant()# QtGui.QColor("green")
        elif role == QtCore.Qt.CheckStateRole and isBool:
            return (QtCore.Qt.Unchecked, QtCore.Qt.Checked)[bool(self.dataTable[row, col])]
        else: 
            return QtCore.QVariant()
    
    def setData(self, index, value, role):
        row, col = index.row(), index.column()
        value = value.toPyObject()
        
        # try to convert the data to a recommended dtype
        dtype = self.dataTable.colInfo[col]["dtype"]
        if dtype in ["str", "int", "float", "bool"]:
            dtype = eval(dtype)
            try:
                value = dtype(value)
            except:
                value = None

        # store value and emit change
        self.dataTable[row, col] = value
        return True

class DataTableView(QtGui.QTableView):
    
    def __init__(self, dataTable = None):
        QtGui.QTableView.__init__(self)
        if not dataTable: dataTable = DataTable()
        
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        #self.setGridStyle(QtCore.Qt.DotLine)
        #self.setAlternatingRowColors(True)
        header = self.horizontalHeader()
        header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.headerContextMenu)
        header.setMovable(True)
        
        # add plot window
        self.plotWidget = DataTablePlot(dataTable)
        self.setDataTable(dataTable)
    
    def saveTemplate(self, fname):
        """
        save table header and visual appearance to a file
        """
        colInfo = repr(self.dataTable.colInfo.tolist())
        viewState = repr(self.horizontalHeader().saveState().data())
        fh = open(fname, "w")
        fh.writelines([colInfo,"\n"])
        fh.writelines([viewState,"\n"])
        fh.close()
        return True
    
    def loadTemplate(self, fname):
        """
        load table header and visual appearance from a file
        """
        # try to load data from file
        try:
            fh = open(fname, "r")
            colInfos, viewState = fh.readlines()[:2]
            colInfos = eval(colInfos)
            viewState = eval(viewState)
            fh.close()
        except Exception as e:
            print e
            return False
        
        # restore dataTable
        id_key = colInfos[0][0]
        dataTable = DataTable(id_key = id_key)        
        try:
            dataTable.addColumns([info[0] for info in colInfos])
            for i, info in enumerate(colInfos):
                dataTable.colInfo[i] = info
        except:
            print "error constructing table"
            return False
        self.setDataTable(dataTable)
        
        # restore view properties
        self.horizontalHeader().restoreState(viewState)
        return True
    
    def setDataTable(self, dataTable):
        self.setModel(DataTableModel(dataTable))
        self.plotWidget.setDataTable(dataTable)
        
    def setModel(self, model):
        assert isinstance(model, DataTableModel)
        self.dataTable = model.dataTable
        return QtGui.QTableView.setModel(self, model)

    def headerContextMenu(self, pos):
        col = self.horizontalHeader().logicalIndexAt(pos)
        colName = self.dataTable.colInfo[col]["name"]
        colFlags = self.dataTable.colInfo[col]["flags"]
        isXPlot = "plotX" in colFlags
        isYPlot = "plotY" in colFlags
        isGPlot = "group" in colFlags 
        
        menu = QtGui.QMenu()
        actionAsX  = menu.addAction("Plot as X")
        actionAsX.setCheckable(True)
        actionAsX.setChecked(isXPlot)
        actionAsY  = menu.addAction("Plot as Y")
        actionAsY.setCheckable(True)
        actionAsY.setChecked(isYPlot)
        actionAsG  = menu.addAction("Plot Group")
        actionAsG.setCheckable(True)
        actionAsG.setChecked(isGPlot)
        actionPlot = menu.addAction("Show Plot")
        
        menu.addSeparator()
        actionExpression = menu.addAction("Set Expression")
        actionRecalculate = menu.addAction("Recalculate Column")
        
        menu.addSeparator()
        actionAdd    = menu.addAction("Add Column")
        actionDelete = menu.addAction("Delete Column")
        actionHide   = menu.addAction("Hide Column")
        actionShow   = menu.addAction("Show Columns")
        
        # remove some items
        actionDelete.setVisible("persistent" not in colFlags)
        actionRecalculate.setVisible("dynamic" in colFlags)
        
        action = menu.exec_(QtGui.QCursor.pos())
        
        if action == actionAsX:
            self.plotWidget.setColumnAsX(col, not isXPlot)
        elif action == actionAsY:
            self.plotWidget.setColumnAsY(col, not isYPlot)
        elif action == actionAsG:
            self.plotWidget.setColumnAsG(col, not isGPlot)
        elif action == actionPlot:
            self.plotWidget.show()
            
        elif action == actionExpression:
            expr = self.dataTable.colInfo[col]["expression"]
            expr, ok = QtGui.QInputDialog.getText(self, "Set Expression", "Evaluate for Column '%s':" % colName, text=expr)
            if ok: self.dataTable.setDynamic(col, str(expr))
        elif action == actionRecalculate:
            self.dataTable.updateDynamic(col=col)
            
        elif action == actionAdd:
            name, ok = QtGui.QInputDialog.getText(self, "Add Column", "Name:")
            if ok: self.dataTable.addColumns([str(name)])
        elif action == actionDelete:
            name = self.dataTable.colInfo[col]["name"]
            buttons = QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
            answer = QtGui.QMessageBox.question(self, "Delete Column", "Delete column '%s' and all its contents?" % name, buttons)
            if answer == QtGui.QMessageBox.Yes: self.dataTable.removeColumn(col)
        elif action == actionHide:
            self.hideColumn(col)
        elif action == actionShow:
            for i in range(self.dataTable.colInfo.size): self.showColumn(i)
    
    def contextMenuEvent(self, event):
        rows = [index.row() for index in self.selectionModel().selectedRows()]
        rows.sort()
        if not len(rows): return

        menu = QtGui.QMenu()
        actionDiscard = menu.addAction("Discard Rows")
        actionAccept = menu.addAction("Accept Rows")
        actionDelete = menu.addAction("Delete Rows")
        action = menu.exec_(event.globalPos())
        
        if action == actionDelete:
            buttons = QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
            answer = QtGui.QMessageBox.question(self, "Delete Rows", "Delete selected rows?", buttons)
            if answer == QtGui.QMessageBox.Yes:
                for row in rows[::-1]: self.dataTable.removeRow(row)
                self.selectionModel().clearSelection()
        elif action == actionDiscard:
            self.dataTable[rows, self.dataTable.discardCol] = True
        elif action == actionAccept:
            self.dataTable[rows, self.dataTable.discardCol] = False

class DataTablePlot(MatplotlibWidget):
    
    def __init__(self, dataTable):
        MatplotlibWidget.__init__(self)
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setDataTable(dataTable)
    
    def setDataTable(self, dataTable):
        # disconnect from previous table
        try:
            self.dataTable.dataChanged.disconnect(self.updatePlotData)
            self.dataTable.rowInserted.disconnect(self.updatePlotData)
        except:
            pass
        # connect to new table
        self.dataTable = dataTable
        dataTable.dataChanged.connect(self.updatePlotData)
        dataTable.rowInserted.connect(self.updatePlotData)
    
    def showEvent(self, event):
        self.updatePlotData()
    
    def setColumnAsX(self, col, enable = True):
        self.dataTable.setFlagUnique(col, "plotX", enable)
        self.updatePlotData()
    
    def setColumnAsY(self, col, enable = True):
        self.dataTable.setFlag(col, "plotY", enable)
        self.updatePlotData()

    def setColumnAsG(self, col, enable = True):
        self.dataTable.setGrouping(col, enable)
        self.updatePlotData()

    def updatePlotData(self):
        if self.isHidden(): return
        # get x and y data from selected columns
        try:
            colX = self.dataTable.searchFlag("plotX")[0]
            colsY = self.dataTable.searchFlag("plotY")
        except:
            return
        # get name for the group column
        try:
            groupCol  = self.dataTable.searchFlag("group")[0]
            groupName = self.dataTable.colInfo[groupCol]["name"]
        except:
            groupName = ""
        
        # give data to matplotlibwidget
        self.clearPlots()
        for colY in colsY:
            self.newPlotGroup()
            colYName = self.dataTable.colInfo[colY]["name"]
            groupedData = self.dataTable.getColumnValuesGrouped(colX, colY)
            for groupValue, x, y in groupedData:
                if groupName:
                    label = "%s, %s = %s" % (colYName, groupName, groupValue)
                else:
                    label = colYName
                self.addGroupedPlot(label, x, y)
        self.setXLabel(self.dataTable.colInfo[colX]["name"])
        
        # data is set, draw plot figure
        self.draw()

class DataTableTabs(QtGui.QTabWidget):
    def __init__(self, default_id_key = None):
        QtGui.QTabWidget.__init__(self)
        self.setTabsClosable(True)
        self.tabBar().setMovable(True)
        self.default_id_key = default_id_key
        
        self.tabCloseRequested.connect(self.handleTabClose)
    
    def addTable(self, name, tableView = None):
        """
        add a new table to the tab widget
        """
        if not tableView:
            dataTable = DataTable(id_key = self.default_id_key)
            tableView = DataTableView(dataTable)
        self.addTab(tableView, name)
    
    def handleTabClose(self, tab):
        tableView = self.widget(tab)
        if tableView.dataTable._modified:
            buttons = QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel
            bn = QtGui.QMessageBox.question(self, "Unsaved Data", "Table contains unsaved data. Do you want to save before closing the table?", buttons=buttons, defaultButton=QtGui.QMessageBox.Save)
            if bn == QtGui.QMessageBox.Save:
                dir = ""; filefilter = "CSV File (*.csv);;Python File (*.py)"
                filename, filter = QtGui.QFileDialog.getSaveFileNameAndFilter(self, "Save Table", dir, filefilter)
                filename = str(filename); filter = str(filter)
                tableView.dataTable.save(filename)
            elif bn == QtGui.QMessageBox.Discard:
                pass

        tableView.setParent(None)

if __name__ == "__main__":   
    QtGui.QApplication.setGraphicsSystem("raster")
    app = QtGui.QApplication([])
    
    MY_ID_KEY = "tid"
    
    # create dataTable and init
    dataTable = DataTable(MY_ID_KEY)
    base = int(time.time())
    for i in range(12):
        g = i % 4
        data_dict = {MY_ID_KEY: i, "b": i**2 + 10*g, "g": g}
        dataTable.insertData(data_dict)
    dataTable.setFlag(0, "plotX")
    dataTable.setFlag(3, "plotY")
    dataTable.setGrouping(4)
    dataTable.save("dump.py")
    dataTable.save("dump.csv")

    tabs = DataTableTabs()
    tabs.addTable("test 1", DataTableView(dataTable))
    tabs.addTable("test 2", DataTableView(dataTable))
    tabs.show()

    app.exec_()