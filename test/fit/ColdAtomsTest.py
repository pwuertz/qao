import unittest
import numpy as np
from unittest.case import TestCase
from qao.fit.coldatoms import ThomasFermi2D
from GaussTest import gauss2drot, gauss2d


def thomasFermi2D(x, y, pars):
    A, x0, rx, y0, ry, off = np.asfarray(pars)
    dx = (x-x0)**2 / rx**2
    dy = (y-y0)**2 / ry**2
    return A * np.power((1-dx-dy).clip(min=0), 3./2.) + off


class TestThomasFermi2D(TestCase):

    def test_fit(self):
        """
        Test the optimal case, that a fermi cloud
        without background and noise is well fitted
        """
        # Arange
        pars = 10, 150, 20, 250, 60, 1.
        x = np.arange(500)
        y = np.arange(400)
        X, Y = np.meshgrid(x, y)
        data = thomasFermi2D(X, Y, pars)
        fitter = ThomasFermi2D(data)
        expected = dict(zip(fitter.getFitParNames(), pars))

        # Act
        guess = fitter.guess()
        r = fitter.fit(guess)
        result = dict(zip(fitter.getFitParNames(), r))

        # Assert
        for key in expected:
            self.assertTrue(np.allclose(result[key], expected[key], atol=1e-3),
                            "Thomas Fermi Fit delivered wrong value for %s: %.3f != %.3f" % (
                                key, result[key], expected[key]
                            ))

    def test_fit_with_noise(self):
        """
        Test the optimal case, that a fermi cloud
        without background and noise is well fitted
        """
        # Arange
        pars = 10, 250, 20, 250, 60, 1.
        x = np.arange(400)
        y = np.arange(400)
        X, Y = np.meshgrid(x, y)
        data = thomasFermi2D(X, Y, pars)

        for nsr in [1e-3, 5e-3, 0.01]:
            noise = np.random.random(x.shape)*nsr*pars[0]
            raw = data + noise
            fitter = ThomasFermi2D(raw)
            expected = dict(zip(fitter.getFitParNames(), pars))

            # Act
            guess = fitter.guess()
            r = fitter.fit(guess)
            result = dict(zip(fitter.getFitParNames(), r))

            # Assert
            for key in expected:
                self.assertTrue(np.allclose(result[key], expected[key], atol=10*nsr),
                                "Thomas Fermi Fit delivered wrong value for %s and nsr %.e: %.3f != %.3f" % (
                                    key, nsr, result[key], expected[key]
                                ))

if __name__ == '__main__':
    unittest.main()
