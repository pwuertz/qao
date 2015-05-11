#!/bin/python
# coding: utf-8
"""
Try to ensure Messagebus funtionality by creating a mocking
messageBusCommunicator which maps Server send to Client read methods.
"""
import unittest
import time
from qao.gui.qt import QtCore
from qao.io.messageBus import MessageBusClient, MessageBusServer

app = QtCore.QCoreApplication([])

TESTPORT = 12345

class TestMessageBus(unittest.TestCase):

    server = None

    def setUp(self):
        self.server = MessageBusServer(port=TESTPORT)
        self.messageBus = MessageBusClient()
        self.messageBus.connectToServer("localhost", TESTPORT)
        self.process()
        self.assertEqual(len(self.server.clients), 1, "At least one client should be connected")
        self.assertTrue(self.messageBus.isConnected(), "MessageBus is not connected")

    def tearDown(self):
        self.messageBus.disconnectFromServer()
        self.messageBus = None
        del self.server.server
        del self.server
        self.server = None

    def process(self):
        for i in range(10):
            app.processEvents()
            self.messageBus.connection.waitForBytesWritten()
            for client in self.server.clients:
                client.connection.waitForBytesWritten()
            time.sleep(0.01)
            app.processEvents()


    def testPublish(self):
        # Assert
        self.messageBus.publishEvent('topic', [1]*20)

    def testSubscribe(self):
        """
        Ensure that subscription callback is handled correctly
        """
        # Arrange
        expected = ["This", "is", "just", 1, "Test"]

        # Assert
        def assertion(result):
            setattr(assertion, 'wasCalled', True)
            self.assertListEqual(result, expected, "Unexpected: %s != %s" % (result, expected))
        setattr(assertion, 'wasCalled', False)

        # Act
        self.messageBus.subscribe('topic', assertion)
        self.process()
        self.messageBus.publishEvent('topic', expected)
        self.process()

        self.assertTrue(assertion.wasCalled, "Assertion has not been called")

if __name__ == '__main__':
    unittest.main()
