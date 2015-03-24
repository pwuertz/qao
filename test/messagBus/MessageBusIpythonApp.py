#!/bin/python
# coding: utf-8
"""
This App embeds the MessageBus functionality within an IPython console Application.

"""
from PyQt5 import QtCore, QtWidgets
from IPython.qt.console.rich_ipython_widget import IPythonWidget
from IPython.qt.inprocess import QtInProcessKernelManager

import numpy as np

class Details(QtWidgets.QWidget):
    def __init__(self):
        super(Details, self).__init__()
        layout = QtWidgets.QVBoxLayout(self)

        self._file_label = QtWidgets.QLabel('File:')
        layout.addWidget(self._file_label)


class Main(QtWidgets.QWidget):
    def __init__(self, mbus):
        super(Main, self).__init__()
        self.mbus = mbus
        layout = QtWidgets.QVBoxLayout(self)

        # ipython console for scripting
        kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel()
        kernel_client = kernel_manager.client()
        kernel_client.start_channels()
        self._console = IPythonWidget(font_size=9)
        self._console.kernel_manager = kernel_manager
        self._console.kernel_client = kernel_client
        layout.addWidget(self._console)
        self.setWindowTitle("Messagebus Ipython Console.")

        # push useful imports to console.
        self.push(np=np, mbus=mbus,
                  subscribe=self.subscribe)

    def handleNewData(self, topic, data):
        self.push(data=data)

    def subscribe(self, topic):
        self.mbus.subscribe(topic, self.handleNewData)

    def push(self, **kwargs):
        self._console.kernel_manager.kernel.shell.push(kwargs)


if __name__ == "__main__":
    import argparse
    from qao.io.messageBus import MessageBusClient
    parser = argparse.ArgumentParser(description="Messagebus IPython Plugin")
    parser.add_argument("-host", type=str, help="Host", default="localhost")
    parser.add_argument("-port", type=int, help="Port", default=9090)

    args = parser.parse_args()

    mbus = MessageBusClient()
    mbus.connectToServer(args.host, args.port)

    args = parser.parse_args()
    app = QtWidgets.QApplication([])

    win = Main(mbus)
    win.show()
    app.exec_()