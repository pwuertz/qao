"""
Data Table
-------------

The :mod:`DataTable` module contains classes for acquiring and storing data
of various types in a single table-like structure.
"""

import time
import os
import csv
import numpy as np
from PyQt4 import QtGui, QtCore

from MatplotlibWidget import MatplotlibWidget

ID_KEY_DEFAULT = "id"

class DataTable(QtCore.QObject):
    """
    This class provides 
    
    """
    
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
        Clear and re-initialize the data table.
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
        """
        Save the table to a file.
        
        The type of file is determined by the file suffix. Currently,
        python readable files (*.py) and CSV files (*.csv) are supported.
        
        :param filename: Path to file.
        :returns: (bool) Success of saving the file.
        """
        ext = os.path.splitext(filename)[1].lower()
        fh = open(filename, "w")
        
        data_list = self.data.tolist()
        if ext == ".py":
            fh.writelines([repr(self.colInfo["name"].tolist()), "\n"])
            fh.write(repr(data_list))
        elif ext == ".csv":
            fh.writelines([",".join(self.colInfo["name"]), "\n"])
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
        Add new columns to the table.
        
        New columns named by the elements in `newColNames` will be added to the right.
        If the same column name already exists, no new column will be added and the new
        name will be silently ignored.
        
        :param newColNames: ([str]) List of new column names.
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
        Remove a column from the table.
        
        :param col: (int) Index of the column to be removed.
        """
        if self.checkFlag(col, "persistent"): return
        self.colInfo = np.delete(self.colInfo, col)
        self.data = np.delete(self.data, col, axis=1)
        
        self._modified = True
        self.colRemoved.emit(col)
        
    def removeRow(self, row):
        """
        Remove a row from the table.
        
        :param row: (int) Index of the row to be removed
        """
        self.data = np.delete(self.data, row, axis=0)
        
        self._modified = True
        self.rowRemoved.emit(row)
    
    def setGroupBy(self, col, enabled = True):
        """
        Declare a column as `group column`.
        
        This method sets the "group" flag on a specific column. The group
        column will affect the output of :func:`getColumnValuesGrouped`.
        Only one column can be the group column. 
        
        :param col: (int) Index of the column.
        :param enabled: (bool) Set/unset group column.
        """
        self.setFlagUnique(col, "group", enabled)
    
    def setDynamic(self, col, expression):
        """
        Declare a column as `dynamic column`.
        
        Set an expression to be evaluated for the column's cells, whenever
        the data in a row changes. Remove the expression and the dynamic
        behavior by passing False as expression.
        
        :param col: (int) Index of the column.
        :param expression: (str) Expression to be evaluated.
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
        Recalculate values of dynamic columns.
        
        The cell to be recalculated is determined by the `row` and `col`
        index. If `row` or `column` is None, all cells are recalculated.
        
        :param row: (int) Row index.
        :param col: (int) Column index.
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
        Internal recalculation of dynamic expressions.
        Not to be called from outside.
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
        Toggle a flag on a column.
        
        If the flag was previously cleared, change the status to set and vice versa.
        
        :param col: (int) Column index.
        :param flag: (str) Flag to set/clear.
        
        .. seealso:: :func:`setFlag` :func:`checkFlag`
        
        """
        isSet = self.checkFlag(col, flag)
        self.setFlag(col, flag, enabled=not isSet)

    def setFlag(self, col, flag, enabled = True):
        """
        Set a flag on a column.
        
        A flag is a string attribute that can be set to enabled or disabled
        for any column, may be used for special treatment of columns.
        
        :param col: (int) Column index.
        :param flag: (str) Flag to set/clear.
        :param enabled: (bool) Set or clear flag.
        
        .. seealso:: :func:`checkFlag`
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
        Set flag on a column and clear this flag on other columns.
        
        Same functionality as :func:`setFlag`, but this method ensures that
        the given flag is only set on one single column.
        
        :param col: (int) Column index.
        :param flag: (str) Flag to set/clear.
        :param enabled: (bool) Set or clear flag.
        """
        for c in range(len(self.colInfo)):
            if c != col:
                self.setFlag(c, flag, enabled = False)
        self.setFlag(col, flag, enabled)

    def setFlagAll(self, flag, enabled = True):
        """
        Set or clear a flag, affecting all columns.
        
        :param flag: (str) Flag to set/clear.
        :param enabled: (bool) Set or clear flag.
        """
        for i in range(len(self.colInfo)): self.setFlag(i, flag, enabled)
    
    def checkFlag(self, col, flag):
        """
        Check if a flag is set on a column.
        
        :param col: (int) Column index.
        :param flag: (str) Flag to check for.
        :returns: (bool) Status of the flag.
        """
        return flag in self.colInfo[col]["flags"]
    
    def searchFlag(self, flag):
        """
        Return a list of columns with `flag` set.
        
        :returns: ([str]) Columns with active flag.
        """
        colFlags = self.colInfo["flags"]
        hasflag  = lambda i: flag in colFlags[i]
        return filter(hasflag, range(len(self.colInfo)))
    
    def insertData(self, data_dict):
        """
        Insert data into a table.
        
        The data is read from a dictionary, where the keys denote the column for the
        values to be inserted. New rows and columns are created if necessary.
        This also triggers reevaluation of dynamic expressions.
        
        :param data_dict: (dict) New data to be inserted.
        """
        # add new columns
        self.addColumns(data_dict.keys())
        
        # get idval from data_dict and determine where to insert the data
        if self.id_key in data_dict:
            idval = data_dict[self.id_key]
        else:
            print "insertData failed, '%s' not found" % self.id_key
            return
        itemindex = (self.data[:, 0] == idval).nonzero()[0]
        if len(itemindex):
            # idval found in table
            row = itemindex[0]
        else:
            # idval not found, insert row
            row = np.searchsorted(self.data[:,0], idval)
            self.data = np.insert(self.data, row, None, axis=0)
            self.data[row, 0] = idval
        
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
        Get values from multiple columns.
        
        A subset of the table is returned containing the requested columns.
        Only rows with column values that are not None are included in the
        result.
        
        :param columns: (int) Column indices.
        :returns: ([ndarray]) List of values for selected columns.
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
        Get grouped values from multiple columns.
        
        A subset of the table is returned containing the requested columns.
        Only rows with column values that are not None are included in the
        result.
        
        The values are grouped by the values found in the group column. For
        each unique value in the group column, the value and a list of requested
        columns is returned.
        
        The result is structured like [[group_val1, col1, col2, ..], [group_val2, col1, col2, ..], ..].
        
        :param columns: (int) Column indices.
        :returns: List of group values and matching column values.
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
    """
    This class implements a table model to be used in conjunction with QTableView.
    A table using this model will be able to show a view of a DataTable.
    """
    
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
    """
    DataTableView is a QTableView subclass that shows the contents of a :class:`DataTable`.
    It furthermore implements functionality specifically for DataTable, like context menus.
    
    :param dataTable: (DataTable) Initial table object to show a view for.
    """
    
    default_path     = ""
    default_path_tpl = ""
    
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
        Save table header and visual appearance to a file.
        
        :param fname: (str) Filename to store the layout to.
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
        Load table header and visual appearance from a file.
        Be warned, this will drop all information from this table.
        
        :param fname: (str) Filename to restore layout from.
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
        
    def loadTemplateDialog(self):
        """
        This function is a wrapper around :func:`loadTemplate`, displaying
        a dialog for the user to choose the file to load the template from.
        """
        filefilter = "Table Template (*.tpl)"
        fname = QtGui.QFileDialog.getOpenFileNameAndFilter(self, "Load Template", DataTableView.default_path_tpl, filefilter)[0]
        fname = str(fname)
        if fname:
            self.loadTemplate(fname)
            DataTableView.default_path_tpl = os.path.dirname(fname)
    
    def saveTemplateDialog(self):
        """
        This function is a wrapper around :func:`saveTemplate`, displaying
        a dialog for the user to choose the file to save the template to.
        """
        filefilter = "Table Template (*.tpl)"
        fname = QtGui.QFileDialog.getSaveFileNameAndFilter(self, "Save Template", DataTableView.default_path_tpl, filefilter)[0]
        fname = str(fname)
        if fname:
            if os.path.splitext(fname)[1] != ".tpl": fname += ".tpl"
            self.saveTemplate(fname)
            DataTableView.default_path_tpl = os.path.dirname(fname)

    def saveTableDialog(self):
        """
        Displays a dialog for saving the data in the table to a file.
        """
        filefilter = ["CSV File (*.csv)", "Python File (*.py)"]
        fname, filt = QtGui.QFileDialog.getSaveFileNameAndFilter(self, "Save Table", DataTableView.default_path, ";;".join(filefilter))
        fname = str(fname)
        if fname:
            filt = {0: ".csv", 1: ".py"}[filefilter.index(str(filt))]
            if os.path.splitext(fname)[1] != filt: fname += filt
            self.dataTable.save(fname)
            DataTableView.default_path = os.path.dirname(fname)

    def showColumnDialog(self):
        """
        Displays a dialog for selectively showing and hiding columns of the table.
        """
        # build list for columns and visibility
        colNames   = self.dataTable.colInfo["name"].tolist()
        listWidget = QtGui.QListWidget()
        listItems  = []
        for i, name in enumerate(colNames):
            item = QtGui.QListWidgetItem(name)
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            if not self.isColumnHidden(i):
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
            listWidget.addItem(item)
            listItems.append(item)
        # on change, show/hide column
        def handleSelection(item):
            self.setColumnHidden(listItems.index(item), item.checkState() == QtCore.Qt.Unchecked) 
        listWidget.itemChanged.connect(handleSelection)
        
        # build/exec dialog
        dialog = QtGui.QDialog()
        dialog.setWindowTitle("Visible Columns")
        layout = QtGui.QVBoxLayout(dialog)
        layout.addWidget(listWidget)
        dialog.exec_()
    
    def setDataTable(self, dataTable):
        """
        Change the DataTable object used by the view.
        
        :param dataTable: (DataTable) Instance of DataTable.
        """
        self.setModel(DataTableModel(dataTable))
        self.plotWidget.setDataTable(dataTable)
        
    def setModel(self, model):
        assert isinstance(model, DataTableModel)
        self.dataTable = model.dataTable
        return QtGui.QTableView.setModel(self, model)
    
    def getColumnActions(self, col):
        colFlags = self.dataTable.colInfo[col]["flags"]
        colName  = self.dataTable.colInfo[col]["name"]
        isXPlot  = "plotX" in colFlags
        isYPlot  = "plotY" in colFlags
        isGPlot  = "group" in colFlags
        
        # plotting
        actionAsX = QtGui.QAction("Plot as X", None)
        actionAsX.setCheckable(True)
        actionAsX.setChecked(isXPlot)
        actionAsX.triggered.connect(lambda: self.plotWidget.setColumnAsX(col, not isXPlot))
        actionAsY  = QtGui.QAction("Plot as Y", None)
        actionAsY.setCheckable(True)
        actionAsY.setChecked(isYPlot)
        actionAsY.triggered.connect(lambda: self.plotWidget.setColumnAsY(col, not isYPlot))
        actionAsG  = QtGui.QAction("Plot Group", None)
        actionAsG.setCheckable(True)
        actionAsG.setChecked(isGPlot)
        actionAsG.triggered.connect(lambda: self.plotWidget.setColumnAsG(col, not isGPlot))
        
        # dynamic expressions
        def expressionFunc():
            expr = self.dataTable.colInfo[col]["expression"]
            expr, ok = QtGui.QInputDialog.getText(self, "Set Expression", "Evaluate for Column '%s':" % colName, text=expr)
            if ok: self.dataTable.setDynamic(col, str(expr))
        actionExpression = QtGui.QAction("Set Expression", None)
        actionExpression.triggered.connect(expressionFunc)
        actionRecalculate = QtGui.QAction("Recalculate Column", None)
        actionRecalculate.setVisible("dynamic" in colFlags)
        actionRecalculate.triggered.connect(lambda: self.dataTable.updateDynamic(col=col))
        
        # hide / delete
        actionHide = QtGui.QAction("Hide Column", None)
        actionHide.triggered.connect(lambda: self.hideColumn(col))
        def deleteFunc():
            buttons = QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
            answer = QtGui.QMessageBox.question(self, "Delete Column", "Delete column '%s' and all its contents?" % colName, buttons)
            if answer == QtGui.QMessageBox.Yes: self.dataTable.removeColumn(col)
        actionDelete = QtGui.QAction("Delete Column", None)
        actionDelete.setVisible("persistent" not in colFlags)
        actionDelete.triggered.connect(deleteFunc)
        
        def sep():
            sep = QtGui.QAction("", None); sep.setSeparator(True)
            return sep
        
        return [actionAsX, actionAsY, actionAsG, sep(),
                actionExpression, actionRecalculate, sep(),
                actionHide, actionDelete]
    
    def getTableActions(self):
        actionSave = QtGui.QAction("Save Table", None)
        actionSave.triggered.connect(self.saveTableDialog)
        actionSaveTpl = QtGui.QAction("Save Template", None)
        actionSaveTpl.triggered.connect(self.saveTemplateDialog)
        actionShowCol = QtGui.QAction("Show Columns", None)
        actionShowCol.triggered.connect(self.showColumnDialog)
        actionShowPlot = QtGui.QAction("Show Plot", None)
        actionShowPlot.triggered.connect(self.plotWidget.show)
        def addColFunc():
            name, ok = QtGui.QInputDialog.getText(self, "Add Column", "Name:")
            if ok: self.dataTable.addColumns([str(name)])
        actionAddCol = QtGui.QAction("Add Column", None)
        actionAddCol.triggered.connect(addColFunc)
        
        sep = QtGui.QAction("", None)
        sep.setSeparator(True)
        
        return [actionSave, actionSaveTpl, sep, actionShowPlot, actionShowCol, actionAddCol]

    def headerContextMenu(self, pos):
        # create menu for this column
        menu = QtGui.QMenu()
        col = self.horizontalHeader().logicalIndexAt(pos)
        for action in self.getColumnActions(col):
            action.setParent(menu)
            menu.addAction(action)
        # show menu
        menu.exec_(QtGui.QCursor.pos())
    
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
    """
    Widget for plotting columns of a :class:`DataTableView`.
    """
    
    def __init__(self, dataTable):
        MatplotlibWidget.__init__(self)
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setDataTable(dataTable)
    
    def setDataTable(self, dataTable):
        # disconnect from previous table
        try:
            self.dataTable.dataChanged.disconnect(self.updatePlotData)
            self.dataTable.rowInserted.disconnect(self.updatePlotData)
            self.dataTable.rowRemoved.disconnect(self.updatePlotData)
            self.dataTable.flagChanged.disconnect(self.handleFlagChange)
        except:
            pass
        # connect to new table
        self.dataTable = dataTable
        dataTable.dataChanged.connect(self.updatePlotData)
        dataTable.rowInserted.connect(self.updatePlotData)
        dataTable.rowRemoved.connect(self.updatePlotData)
        dataTable.flagChanged.connect(self.handleFlagChange)
    
    def showEvent(self, event):
        self.setupPlotData()
    
    def handleFlagChange(self, col, flag):
        if flag in ["plotX", "plotY", "group"]: self.setupPlotData()
    
    def setColumnAsX(self, col, enable = True):
        self.dataTable.setFlagUnique(col, "plotX", enable)
    
    def setColumnAsY(self, col, enable = True):
        self.dataTable.setFlag(col, "plotY", enable)

    def setColumnAsG(self, col, enable = True):
        self.dataTable.setGroupBy(col, enable)
    
    def setupPlotData(self):
        if self.isHidden(): return
        # get selected x and y column numbers
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
        
        # give data to MatplotlibWidget
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
        
    def updatePlotData(self):
        if self.isHidden(): return
        # get selected x and y column numbers
        try:
            colX = self.dataTable.searchFlag("plotX")[0]
            colsY = self.dataTable.searchFlag("plotY")
        except:
            return
        
        # update data
        for i, colY in enumerate(colsY):
            groupedData = self.dataTable.getColumnValuesGrouped(colX, colY)
            for j, groupItem in enumerate(groupedData):
                self.updateGroupedPlot(i, j, groupItem[1], groupItem[2])
        
        # data updated, draw plot figure
        self.draw()

class DataTableTabs(QtGui.QTabWidget):
    """
    Tabbed view of multiple DataTables. Adding more functionality for interacting
    with DataTables.
    """
    def __init__(self, default_id_key = None):
        QtGui.QTabWidget.__init__(self)
        self.setTabsClosable(True)
        self.tabBar().setMovable(True)
        self.default_id_key = default_id_key
        
        self.tabBar().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self.handleContextMenuReq)
        self.tabCloseRequested.connect(self.handleTabClose)
        
        self.activeTable = None
        
    def setDefaultIdKey(self, default_id_key):
        self.default_id_key = default_id_key
    
    def newTable(self, name, tableView = None):
        """
        Add a new table to the tab widget.
        
        :param name: (str) Name of the new table.
        :param tableView: Instance or None to create one.
        """
        if not tableView:
            dataTable = DataTable(id_key = self.default_id_key)
            tableView = DataTableView(dataTable)
        self.addTab(tableView, name)
        self.setCurrentIndex(self.count()-1)
        self.setActiveTable(self.count()-1)
        return tableView
    
    def setActiveTable(self, tab):
        """
        Define a table to be the active table.
        
        :param tab: (int) Index of the tab.
        """
        for i in range(self.count()):
            title = str(self.tabText(i))
            if title[-1] == "*": self.setTabText(i, title[:-1])
        tableView = self.widget(tab)
        self.setTabText(tab, str(self.tabText(tab))+"*")
        self.activeTable = tableView
    
    def handleTabClose(self, tab):
        tableView = self.widget(tab)
        if tableView.dataTable._modified:
            buttons = QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel
            bn = QtGui.QMessageBox.question(self, "Unsaved Data", "Table contains unsaved data. Do you want to save before closing the table?", buttons=buttons, defaultButton=QtGui.QMessageBox.Save)
            if bn == QtGui.QMessageBox.Save:
                self.saveTable(tableView)
            elif bn == QtGui.QMessageBox.Cancel:
                return
            elif bn == QtGui.QMessageBox.Discard:
                pass

        tableView.setParent(None)
        if self.count() == 0: self.newTable("results")
        self.setActiveTable(self.count()-1)
        
    def handleContextMenuReq(self, pos):
        tab = self.tabBar().tabAt(pos)
        self.setCurrentIndex(tab)
        tableView = self.widget(tab)
        
        # table tabs actions
        actionActive = QtGui.QAction("Make Active", None)
        actionActive.triggered.connect(lambda: self.setActiveTable(tab))
        def newFunc():
            name, ok = QtGui.QInputDialog.getText(self, "New Table", "Name for new table:", text = "results")
            if ok: self.newTable(name = str(name))
        actionNew = QtGui.QAction("New Table", None)
        actionNew.triggered.connect(newFunc)
        def newTplFunc():
            name, ok = QtGui.QInputDialog.getText(self, "New Table", "Name for new table:", text = "results")
            if ok: tableView = self.newTable(name = str(name))
            else: return
            tableView.loadTemplateDialog()
        actionNewTpl = QtGui.QAction("New Table from Template", None)
        actionNewTpl.triggered.connect(newTplFunc)
        
        # collect actions
        sep = QtGui.QAction("", None)
        sep.setSeparator(True)
        actions  = [actionActive, actionNew, actionNewTpl, sep]
        actions += tableView.getTableActions()
        
        # build menu
        menu = QtGui.QMenu()
        for action in actions:
            action.setParent(menu)
            menu.addAction(action)
        menu.exec_(QtGui.QCursor.pos())

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
    dataTable.setGroupBy(4)
    #dataTable.save("dump.py")
    #dataTable.save("dump.csv")

    tabs = DataTableTabs()
    tabs.newTable("test 1", DataTableView(dataTable))
    tabs.newTable("test 2", DataTableView(dataTable))
    tabs.show()

    app.exec_()