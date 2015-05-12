#!/bin/python
# coding: utf-8
"""
Ensure that the messageBusCommunicator is working as expected
by injecting mocking methods.
"""
import six
import unittest
from qao.io import websocket, jsonEncoder
from qao.gui.qt import QtCore
from qao.io.messageBus import MessageBusCommunicator


class MockConnection(QtCore.QIODevice):
    def __init__(self):
        super(MockConnection, self).__init__()
        self.readBuffer = b''
        self.written = b''

    def open(self, openMode):
        return True

    def write(self, byte):
        if isinstance(byte, str) and six.PY3:
            byte = six.b(byte)
        self.written += byte
        return len(byte)

    def bytesAvailable(self):
        return len(self.readBuffer)

    def read(self, nBytes=0):
        buffer, self.readBuffer = self.readBuffer[:nBytes], self.readBuffer[nBytes:]
        return buffer


class MockMessageBusCommunicator(MessageBusCommunicator):
    def __init__(self):
        super(MockMessageBusCommunicator, self).__init__()
        self.connection = MockConnection()
        self.handshakeDone = False

    def _send(self, RawData, blocking=False):
        self.connection.write(RawData)


class TestMessageBusCommunicator(unittest.TestCase):
    def setUp(self):
        self.comunicator = MockMessageBusCommunicator()

    def test_sendFrame(self):
        # Arrange
        results = []
        data = "1"*30
        com = self.comunicator

        def _send(raw):
            results.append(raw)
        com._send = _send

        # Act
        com._sendFrame_(data, websocket.OPCODE_BINARY)
        com._sendFrame_(data, websocket.OPCODE_ASCII)

        # Assert
        self.assertEqual(len(results), 2, "len(Results) should be two")

    def test_sendFrame01(self):
        # Arrange
        data = "1"*30
        com = self.comunicator
        com.handshakeDone = True

        # Act
        com._sendFrame_(data, websocket.OPCODE_ASCII)

        # Assert
        self.assertGreater(len(com.connection.written), 0, "written data should be longer than zero")

    def test_handleReadyRead_ascii(self):
        # Arrange
        data = "abcdefg x87$&*"
        com = self.comunicator
        com.handshakeDone = True
        com._sendFrame_(data, websocket.OPCODE_ASCII)

        # Assert
        def handleFrame(frm):
            self.assertEqual(frm.data, six.b(data), "Read did not work properly")
        com._handleFrame_ = handleFrame

        # Act
        com.connection.readBuffer = com.connection.written
        self.assertRaises(StopIteration, com._handleReadyRead(), "Missing end of parser")

    def test_handleReadyRead_binary(self):
        # Arrange
        data = "abcdefg x87$&*"
        com = self.comunicator
        com.handshakeDone = True
        com._sendFrame_(data, websocket.OPCODE_BINARY)

        # Assert
        def handleFrame(frm):
            self.assertEqual(frm.data, six.b(data), "Read did not work properly")
        com._handleFrame_ = handleFrame

        # Act
        com.connection.readBuffer = com.connection.written
        self.assertRaises(StopIteration, com._handleReadyRead(), "Missing end of parser")

    def test_handleFrame(self):
        # Arrange
        data = ["this", "is", "just", 1, "Test"]
        expected = jsonEncoder.dumps(data, separators=(',', ':'), sort_keys=True)
        com = self.comunicator

        # pipe write to read buffer
        def write(bytes):
            if isinstance(bytes, str):
                bytes = six.b(bytes)
            com.connection.readBuffer += bytes
            com._handleReadyRead()
            return len(bytes)

        com.connection.write = write
        com.handshakeDone = True

        # Assert
        def handleNewPacket(result):
            self.assertEqual(result, expected, "Unexpected Data: %s != %s" % (result, expected))
        com._handleNewPacket = handleNewPacket

        # Act
        com._sendPacket(data, binary=False)

if __name__ == '__main__':
    unittest.main()
