"""
In Order to Safe import PyQt4 or PyQt5 use this module

    from qao.gui.qt import QtCore, QtGui, QtWidgets, QtNetwork



@author:tlausch
created: 2014-05-28
"""

import sys

PYQT4 = 'PyQt4'
PYQT5 = 'PyQt5'
PYSIDE = 'PySide'

def has_module(mod):
    for key in sys.modules.keys():
        if key.startswith(mod):
            return True
    return False

def import_qt4():
    from PyQt4 import QtCore, QtGui, QtSvg, QtNetwork
    return QtCore, QtGui, QtGui, QtSvg, QtNetwork

def import_qt5():
    from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg, QtNetwork
    class Qt45Gui(object):
        """
        wraps qtgui and makes pyqt4 code useable in pyqt5 environment
        s.t. it is backward compatible
        """
        def __getattribute__(self, item):
            if hasattr(QtGui, item):
                return getattr(QtGui, item)
            return getattr(QtWidgets, item)

    qt45Gui = Qt45Gui()
    return QtCore, qt45Gui, QtWidgets, QtSvg, QtNetwork

def import_pyside():
    from PySide import QtCore, QtGui, QtSvg, QtNetwork
    return QtCore, QtGui, QtGui, QtSvg, QtNetwork

def import_qt(version):
    if version == PYQT4:
        return import_qt4()
    elif version == PYSIDE:
        return import_pyside()
    return import_qt5()

version = PYQT5
if has_module(PYQT4):
    version = PYQT4
elif has_module(PYSIDE):
    version = PYSIDE

QtCore, QtGui, QtWidgets, QtSvg, QtNetwork = import_qt(version)
