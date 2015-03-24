import numpy as np
from qao.io.websocket import xor, np_xor
import struct
import unittest
from unittest.case import TestCase


class TestWebsocketXor(TestCase):
    def test_xor_even(self):
        # Arange
        n = 4*100
        mask = np.random.bytes(4)
        mock_data = np.random.bytes(n)

        expected = xor(mock_data, mask)
                
        # Act
        result = np_xor(mock_data, mask)
        
        # Assert
        self.assertEqual(result, expected, "Masking failed")
        

    def test_xor_odd(self):
        for i in range(1, 4):
            # Arange
            n = 4*100+i
            mask = np.random.bytes(4)
            mock_data = np.random.bytes(n)
            
            expected = xor(mock_data, mask)
            
            # Act
            result = np_xor(mock_data, mask)
    
            # Assert
            self.assertEqual(result, expected, "Masking failed")


if __name__ == '__main__':
    unittest.main()