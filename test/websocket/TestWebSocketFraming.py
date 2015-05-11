#!/bin/python
# coding: utf-8
"""

"""
import json
import unittest
from qao.io.websocket import Frame


class TestFrame(unittest.TestCase):
    def setUp(self):
        self.data = json.dumps(["this", "is", "only", 1, "test"])

    def test_build(self):
        """
        Ensure that the build process is working
        """
        # Arrange
        frm = Frame(opCode=0, data=self.data)

        # Act & Assert
        raw = frm.build()
        self.assertIsNotNone(raw, "Unexpected result")

    def test_parse(self):
        """
        Ensure the parsing process is working.
        """
        # Arrange
        frm = Frame(opCode=0, data=self.data)
        build = frm.build()

        # Act
        try:
            pos = 0
            neededBytes = next(frm.parser)
            pos = neededBytes
            neededBytes = frm.parser.send(build[0:neededBytes])
            neededBytes = frm.parser.send(build[pos:(pos + neededBytes)])

        except StopIteration:
            data = frm.data

        # Assert
        self.assertEqual(pos, 2, "Start Bytes should be at least two.")
        self.assertEqual(data, self.data, "Parsing went wrong. %s != %s" % (data, self.data))


if __name__ == '__main__':
    unittest.main()
