#!/bin/python
# coding: utf-8
"""
Try to ensure Messagebus funtionality by creating a mocking
messageBusCommunicator which maps Server send to Client read methods.
"""
import unittest
from qao.io.messageBus import MessageBusClient, MessageBusServer, MessageBusCommunicator


class TestMessageBus(unittest.TestCase):
    def test(self):
        """
        
        """
        # Arrange

        # Act

        # Assert
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
