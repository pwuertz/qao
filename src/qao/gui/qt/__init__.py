"""
Qt API selector that can be used to switch between PyQt4/5 and PySide.

It first tries to import Qt modules from from the currently loaded Qt binding.
If no modules were loaded yet, import from the binding specified by the
"QT_API" environment variable. If the variable is not set, load the first
binding available.
"""

import os

from qao.gui.qt._loader import (loaded_api, load_qt, QT_API_PYSIDE, QT_API_PYQT, QT_API_PYQTv1, QT_API_PYQT5)

QT_API = os.environ.get('QT_API', loaded_api())
if QT_API not in [QT_API_PYSIDE, QT_API_PYQT, QT_API_PYQTv1, QT_API_PYQT5, None]:
    raise RuntimeError("Invalid Qt API %r, valid values are: %r, %r, %r, %r" %
                       (QT_API, QT_API_PYSIDE, QT_API_PYQT, QT_API_PYQTv1, QT_API_PYQT5))
if QT_API is None:
    api_opts = [QT_API_PYQT5, QT_API_PYQT, QT_API_PYSIDE]
else:
    api_opts = [QT_API]

QtCore, QtGui, QtSvg, QtNetwork, QT_API = load_qt(api_opts)

del loaded_api
del load_qt
