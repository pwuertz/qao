#!/bin/python
# coding: utf-8
"""

"""
import unittest
from qao.io.websocket import DefaultHTTPClientHeader, HTTPHeader


class TestHttpHeader(unittest.TestCase):
    def test_createHeader(self):
        """
        Ensure creation of httpheader works.
        """
        # Arrange
        header = DefaultHTTPClientHeader()

        # Act
        hdr = header.createHeader()

        # Assert
        self.assertIsNotNone(hdr, "Header cannot be None. Has to be an non empty string.")
        self.assertGreater(len(hdr), 0, "Has to be an non empty string.")

    def test_readHeader(self):
        """
        Ensure that the header is read back properly
        """
        # Arrange
        default = DefaultHTTPClientHeader()
        # first line GET Verb is ignored.
        lines = default.createHeader().split('\n')[1:]
        expected = default.attr

        header = HTTPHeader()
        def send():
            _ = next(header.parser)
            for line in lines:
                header.parser.send(line)

        # Act
        self.assertRaises(StopIteration, send)
        attrs = header.attr

        # Assert
        self.assertDictEqual(attrs, expected, "Unexpected contents: %s != %s" % (attrs, expected))

    def test_buildServerReply(self):
        """
        Ensure that the header is read back properly
        """
        # Arrange
        default = DefaultHTTPClientHeader()

        # Act
        header = default.buildServerReply()

        # Assert
        self.assertIsNotNone(header, "A Reply cannot by None")
        self.assertIsInstance(header, HTTPHeader, "Reply should be a HttpHeader")

if __name__ == '__main__':
    unittest.main()
