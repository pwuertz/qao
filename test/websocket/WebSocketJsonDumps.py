import unittest
from unittest.case import TestCase

import numpy as np
from qao.io.jsonEncoder import dumps, loads


class JSonDumpsNdArray(TestCase):
    
    def test_json_ndarray(self):
        # Arrange
        m = 10
        expected = np.arange(m)
        
        # Act
        dumped = dumps(expected)
        result = loads(dumped)
        
        # Assert
        self.assertEqual(expected.shape, result.shape, "Shape mismatch")
        self.assertEqual(expected.dtype, result.dtype, "Type mismatch %s != %s" % (expected.dtype, result.dtype))
        self.assertTrue(np.allclose(expected, result), "Value mismatch")
        
    def test_json_ndarray_in_list(self):
        # Arrange
        m = 10
        expected = [np.arange(i) for i in range(m)]
        
        # Act
        dumped = dumps(expected)
        result = loads(dumped)
        
        # Assert
        for i, expected_array in enumerate(expected):
            result_array = result[i]
            self.assertEqual(expected_array.shape, result_array.shape, "Shape mismatch")
            self.assertEqual(expected_array.dtype, result_array.dtype, "Type mismatch %s != %s" % (expected_array.dtype, result_array.dtype))
            self.assertTrue(np.allclose(expected_array, result_array), "Value mismatch")
    

    def test_json_ndarray_in_dict(self):
        # Arrange
        m = 10
        expected = {'0':np.arange(0),
                    '10':np.arange(10)}
        
        # Act
        dumped = dumps(expected)
        result = loads(dumped)

        # Assert
        for i, expected_array in expected.iteritems():
            result_array = result[i]
            self.assertEqual(expected_array.shape, result_array.shape, "Shape mismatch")
            self.assertEqual(expected_array.dtype, result_array.dtype, "Type mismatch %s != %s" % (expected_array.dtype, result_array.dtype))
            self.assertTrue(np.allclose(expected_array, result_array), "Value mismatch")
    
if __name__ == '__main__':
    unittest.main()