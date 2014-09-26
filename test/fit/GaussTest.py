import struct
import unittest
import numpy as np
from unittest.case import TestCase
from qao.fit.gauss import Gauss1D, Gauss2D, Gauss2DRot

def gauss1d(x, pars):
    A, x0, sx, off = pars
    return A * np.exp(-(x-x0)**2 / sx**2 *.5) + off

def gauss2d(x, y, pars):
    A, x0, sx, y0, sy, off = pars
    ex = np.exp(-(x-x0)**2 / sx**2 *.5)
    ey = np.exp(-(y-y0)**2 / sy**2 *.5)
    return A * ex * ey + off

def gauss2drot(x, y, pars):
    A, x0, sx, y0, sy, alpha, off = pars
    sina, cosa = np.sin(alpha), np.cos(alpha)
    x, y = (x-x0), (y-y0)
    xr = x*cosa + y*sina
    yr = y*cosa - x*sina
    return A * np.exp(- .5*xr**2/sx**2 - .5*yr**2/sy**2) + off

class TestGauss1D(TestCase):

    def test_guess_without_background_correction(self):
        """
        Ensure that in case of a background offset which changes the momentum
        the correct guess for gauss 1d fitting is chosen.
        """
        # Arrange
        # A x0, sx, off
        pars = 1.5, 50, 10., 0.
        x = np.arange(1000.)
        y = gauss1d(x, pars)
        fitter = Gauss1D(y)
        expected = pars

        # Act
        guess = fitter.guess()

        # Assert
        self.assertTrue(np.allclose(guess, expected, atol=.01),
                        'Wrong Guess has been chosen for the 1D - Fit')


    def test_guess_with_background_correction(self):
        """
        Ensure that in case of a background offset which changes the momentum
        the correct guess for gauss 1d fitting is chosen.
        """
        # Arrange
        # A x0, sx, off
        pars = 1.5, 50, 10., 100.
        x = np.arange(1000.)
        y = gauss1d(x, pars)
        fitter = Gauss1D(y)
        expected = pars

        # Act
        guess = fitter.guess()

        # Assert
        self.assertTrue(np.allclose(guess, expected, atol=.01),
                        'Wrong Guess has been chosen for the 1D - Fit')

    def test_fit(self):
        """
        Test that the Gauss 1D is able to fit params to data with 10*sx without noise
        """
        # Arrange
        A, x0, sx, off = 1.5, 40, 10., 1.
        x = np.arange(100.)
        y = gauss1d(x, (A, x0, sx, off))
        fitter = Gauss1D(y)
        expected = dict(
            A=A, x0=x0, sx=sx, off=off
        )

        # Act
        guess = fitter.guess()
        result = fitter.fit(guess)
        
        # Assert
        for i, key in enumerate(expected):
            self.assertTrue(np.allclose(result[i], expected[key]),
                            "Gauss 1D Fit returned wrong value for %s: %.3f != %.3f" % (
                                key, result[i], expected[key]
                            ))

    def test_fit_snr(self):
        """
        Test that the Gauss 1D is able to fit params to data with 10*sigma for several
        signal to noise ratios
        """
        # Arrange
        A, x_0, s, off = 1.5, 40, 10., 1.
        x = np.arange(100.)
        y = gauss1d(x, (A, x_0, s, off))
        expected = dict(
            A=A, x_0=x_0, s=s, off=off
        )
        for nsr in [1e-3, 0.1, 0.5]:
            noise = np.random.random(x.shape)*nsr*A
            fitter = Gauss1D(y + noise)

            # Act
            guess = fitter.guess()
            result = fitter.fit(guess)

            # Assert
            for i, key in enumerate(fitter.pars_name):
                self.assertTrue(np.allclose(result[i], expected[key], atol=nsr*10),
                                "Gauss 1D Fit snr %s returned wrong value for %s: %.3f != %.3f" % (
                                    1./nsr, key, result[i], expected[key]
                                ))


class TestGauss2D(TestCase):

    def test_fit(self):
        """
        Test that the Gauss 2D is able to fit params to data with 10*s_x, s_y without noise
        """
        # Arrange
        A, x_0, s_x, y_0, s_y, off = 1.5, 45, 10, 40., 20, 1.
        x = np.arange(100.)
        y = np.arange(100.)
        X, Y = np.meshgrid(x, y)
        gauss = gauss2d(Y, X, (A, x_0, s_x, y_0, s_y, off))
        fitter = Gauss2D(gauss.T)
        expected = dict(
            A=A, x_0=x_0, s_x=s_x, off=off,
            y_0=y_0, s_y=s_y
        )

        # Act
        guess = fitter.guess()
        result = fitter.fit(guess)

        # Assert
        for i, key in enumerate(fitter.pars_name):
            self.assertTrue(np.allclose(result[i], expected[key], atol=1e-4),
                            "Gauss 2D Fit returned wrong value for %s: %.3f != %.3f" % (
                                key, result[i], expected[key]
                            ))


class TestGauss2DRot(TestCase):

    def test_fit(self):
        """
        Test that the Gauss 2D is able to fit params rotated to data with 10*s_x, s_y without noise
        """
        # Arrange
        pars = 2., 45, 10, 40., 10, np.pi/4., 1.
        x = np.arange(100.)
        y = np.arange(100.)
        X, Y = np.meshgrid(x, y)
        gauss = gauss2drot(Y, X, pars)
        fitter = Gauss2DRot(gauss.T)
        expected = dict(zip(fitter.getFitParNames(), pars))

        # Act
        guess = fitter.guess()
        fitter.fit(guess)
        result = fitter.getFitParsDict(False)
        result['alpha'] = np.abs(result['alpha'])

        # Assert
        for key in fitter.pars_name:
            self.assertTrue(np.allclose(result[key], expected[key], atol=.1),
                            "Gauss 2D Rot Fit returned wrong value for %s: %.3f != %.3f" % (
                                key, result[key], expected[key]
                            ))

    def test_fit_asym(self):
        """
        Test that the Gauss 2D is able to fit params rotated to data with 10*s_x, s_y without noise
        but and different aspect ratios of s_x = n s_y
        """
        import matplotlib.pyplot as plt
        # Arrange
        for i in range(2, 10):
            A, x_0, s_x, y_0, alpha, off = 2., 45, 5, 40., np.pi/4., 1.
            s_y = s_x * i
            x = np.arange(100.)
            y = np.arange(100.)
            X, Y = np.meshgrid(x, y)
            gauss = gauss2drot(Y, X, (A, x_0, s_x, y_0, s_y, alpha, off))
            fitter = Gauss2DRot(gauss.T)
            expected = dict(
                A=A, x_0=x_0, s_x=s_x, off=off,
                y_0=y_0, s_y=s_y, alpha=alpha
            )

            # Act
            guess = fitter.guess()
            result = fitter.fit(guess)
            result_dict = fitter.getFitParsDict()

            # Assert
            for j, key in enumerate(fitter.pars_name):

                self.assertTrue(np.allclose(result[0], expected['A'], atol=.01), "Gauss 2D Rot Fit returned wrong Amplitude")
                self.assertTrue(np.allclose(result[1], expected['x_0'], atol=.01), "Gauss 2D Rot Fit returned wrong Position x_0 %.f" % result[1] )
                self.assertTrue(np.allclose(result[3], expected['y_0'], atol=.01), "Gauss 2D Rot Fit returned wrong Position y_0")
                self.assertTrue(np.allclose(result[2], expected['s_x'], atol=.01) |
                                np.allclose(result[2], expected['s_y'], atol=.01), "Gauss 2D Rot Fit returned wrong SigmaX")
                self.assertTrue(np.allclose(result[4], expected['s_x'], atol=.01) |
                                np.allclose(result[4], expected['s_y'], atol=.01), "Gauss 2D Rot Fit returned wrong SigmaY")
                self.assertTrue(np.allclose(result[6], expected['off'], atol=.01), "Gauss 2D Rot Fit returned wrong offset %.f " % result[6])
                self.assertTrue(np.allclose(result[5] % expected['alpha'], 0, atol=0.05) |
                                np.allclose(result[5] % expected['alpha'], expected['alpha'], atol=.05), "Gauss 2D Rot Fit returned wrong Angle alpha %.3f" % (result[5] % expected['alpha']))

if __name__ == '__main__':
    unittest.main()