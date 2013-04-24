# -*- coding: utf-8 -*-
"""
Kalman Filters
--------------

This module provides a set of filters for estimating and predicting the
state of specific systems, given a series of measurements. The filters are
based on the Kalman filter, implemented in :class:`KalmanFilterBase`.
"""

import numpy as np

class KalmanFilterBase:
    """
    Basis implementation of the Kalman filter. Use this class to implement
    system specific filters by customizing the matrices F, H, B, Q and R.
    See http://en.wikipedia.org/wiki/Kalman_filter for a definition of
    these parameters.
    
    The matrices and the control input can be made time dependent by
    using the corresponding setters before calling :func:`_predict_state` or
    :func:`_measurement_update`.
    """
    
    def __init__(self, x_init, P_init, u_init, Q, R, F, H, B):
        self._set_Q(Q)
        self._set_R(R)
        self._set_F(F)
        self._set_H(H)
        self._set_B(B)
        self._set_u(u_init)
        self._P = np.array(P_init)
        self._x = np.array(x_init)

    def _set_Q(self, Q):
        r"""
        Set the process noise covariance matrix
        :math:`Q \in \mathbb{R}^{n \times n}`.
        """
        self._Q = np.array(Q)
    
    def _set_R(self, R):
        r"""
        Set the measurement noise covariance matrix
        :math:`R \in \mathbb{R}^{m \times m}`.
        """
        self._R = np.array(R)

    def _set_F(self, F):
        r"""
        Set the state transition model matrix
        :math:`F \in \mathbb{R}^{n \times n}`.
        """
        self._F = np.array(F)

    def _set_H(self, H):
        r"""
        Set the observation model matrix
        :math:`H \in \mathbb{R}^{m \times n}`.
        """
        self._H = np.array(H)
    
    def _set_B(self, B):
        r"""
        Set the control-input model matrix
        :math:`B \in \mathbb{R}^{n \times l}`.
        """
        self._B = np.array(B)
    
    def _set_u(self, u):
        r"""
        Set the control-input vector :math:`\vec{u} \in \mathbb{R}^l` for
        the next prediction or measurement update step.
        """
        self._u = np.array(u)
    
    def _predict_state(self):
        r"""
        Predict the next state :math:`\vec{x}_{k|k-1}` and :math:`P_{k|k-1}`
        based on the information up to the last measured observation
        :math:`\vec{z}_{k-1}`.
        
        The state update equation reads:
        
        .. math:: \vec{x}_{k|k-1} = F\cdot\vec{x}_{k-1|k-1} + B\cdot\vec{u}
        
        :returns: (:math:`\vec{x}_{k|k-1}`, :math:`P_{k|k-1}`)
        """
        F, x, B, u = self._F, self._x, self._B, self._u
        P, Q  = self._P, self._Q
        x_predict = np.dot(F, x) + np.dot(B, u)
        P_predict = np.dot(F, np.dot(P, F.T)) + Q
        return x_predict, P_predict
    
    def _measurement_update(self, z):
        r"""
        Update the estimation of the current state vector
        :math:`\vec{x}_{k|k}` based on a new measurement :math:`\vec{z}_{k}`.
        """
        H, R = self._H, self._R
        x_predict, P_predict = self._predict_state()
        innov = z - np.dot(H, x_predict)
        
        S = np.dot(H, np.dot(P_predict, H.T)) + R
        Sinv = np.linalg.inv(S)
        K = np.dot(P_predict, np.dot(H.T, Sinv))
        
        self._x = x_predict + np.dot(K, innov)
        self._P = P_predict - np.dot(np.dot(K, H), P_predict)


class LinearSystem(KalmanFilterBase):
    r"""
    Kalman filter for a one dimensional system with linear drifts. The
    evolution of the system is modelled as follows:
    
    .. math::

       x_k &= x_{k-1} + v_{k-1} \cdot \Delta t + N(0, \sigma_\text{pos}^2) \\
       v_k &= v_{k-1} + N(0, \sigma_\text{drift}^2)
    
    The position :math:`x` and drift velocity :math:`v` can depend
    on normally distributed noise with the standard deviations
    :math:`\sigma_\text{pos}` and :math:`\sigma_\text{drift}`. If the
    measurements are irregularly spaced in time, the time step
    :math:`\Delta t` can be altered with :func:`set_dt` before predicting
    the next position or performing a measurement update.
    
    The observable of the system is the position :math:`x_k`. Its measurement
    :math:`\tilde{x}_k` shall be affected by normally distributed noise with
    a standard deviation of :math:`\sigma_\text{meas}`:
    
    .. math::

       \tilde{x}_k = x_k + N(0, \sigma_\text{meas}^2)
    
    After creating an instance of :class:`LinearSystem` with initial
    parameters, use the methods :func:`add_pos_measurement` to update its
    position estimate andd :func:`predicted_pos` to calculate a prediction
    of the next measured position.

    :param pos_init: Initial position.
    :param sig_pos: Standard deviation :math:`\sigma_\text{pos}`.
    :param sig_drift: Standard deviation :math:`\sigma_\text{drift}`.
    :param sig_meas: Standard deviation :math:`\sigma_\text{meas}`.
    :param dt: Initial time-step factor (default=1.0).
    """
    
    def __init__(self, pos_init, sig_pos, sig_drift, sig_meas, dt=1.):
        # covariance matrices
        Q = np.array([[sig_pos**2, 0.],[0., sig_drift**2]])
        R = sig_meas**2
        # system matrices
        F = np.array([[1., dt],[0., 1.]])
        H = np.array([[1., 0.]])
        # controlled position shift
        B = np.array([-1., 0.])
        # initialize KalmanFilterBase
        x_init = np.array([pos_init, 0.])
        P_init = Q.copy()**.5
        u_init = 0.
        KalmanFilterBase.__init__(self, x_init=x_init, P_init=P_init,
                                  u_init=u_init, Q=Q, R=R, F=F, H=H, B=B)    
    
    def predicted_pos(self):
        """
        Get the predicted position for the next measurement, based on the
        last measurement.
        """
        x, _ = self._predict_state()
        return x[0]
    
    def current_pos(self):
        """
        Return the estimated current position of the system, based on the
        last measurement.
        """
        return self._x[0]
    
    def add_pos_measurement(self, pos_meas):
        """
        Update the position of the system based on a new measurement.
        """
        self._measurement_update(np.array(pos_meas))
    
    def set_dt(self, dt):
        """
        Set the time difference that is assumed for the predictions and
        measurement updates.
        """
        self._F[0,1] = dt


class PeriodicLinearSystem(LinearSystem):
    r"""
    The :class:`PeriodicLinearSystem` is based on the
    :class:`LinearSystem` and thus behaves the same way. It is however
    specialized for systems with a periodicity of `L`, where :math:`x` and
    :math:`x+L` represent the same position. The default periodicity is
    :math:`L=2\pi`, which means that the positions can be interpreted as
    angles.

    :param pos_init: Initial position.
    :param sig_pos: Standard deviation :math:`\sigma_\text{pos}`.
    :param sig_drift: Standard deviation :math:`\sigma_\text{drift}`.
    :param sig_meas: Standard deviation :math:`\sigma_\text{meas}`.
    :param dt: Initial time-step factor (default=1.0).
    :param L: Periodicity of the position (default :math:`L=2\pi`).
    """
    
    def __init__(self, pos_init, sig_pos, sig_drift, sig_meas, dt=1., L=2*np.pi):
        self.L = L
        LinearSystem.__init__(self, pos_init, sig_pos, sig_drift, sig_meas, dt)
    
    def predicted_pos(self):
        r"""
        Get the predicted position for the next measurement, based on the
        last measurement. The returned position is mapped to
        :math:`-\frac{L}{2} \leq x < \frac{L}{2}`.
        """
        pos = LinearSystem.predicted_pos(self)
        return ((pos + .5*self.L) % self.L) - .5*self.L

    def current_pos(self):
        r"""
        Return the estimated current position of the system, based on the
        last measurement. The returned position is mapped to
        :math:`-\frac{L}{2} \leq x < \frac{L}{2}`.
        """
        pos = LinearSystem.current_pos(self)
        return ((pos + .5*self.L) % self.L) - .5*self.L

    def add_pos_measurement(self, pos_meas):
        """
        Update the position of the system based on a new measurement. The
        measurement is automatically mapped to the periodicity of the system.
        """
        pos = LinearSystem.predicted_pos(self)
        diff = pos_meas - pos
        diff_normalized = ((diff + .5*self.L) % self.L) - .5*self.L
        LinearSystem.add_pos_measurement(self, pos + diff_normalized)


if __name__ == "__main__":
    import pylab as plt

    # create test data
    sig_noise = .2
    X = np.linspace(-1, 1, 100)
    data_orig = np.cos(X * 2*np.pi)
    data = data_orig + np.random.normal(0, sig_noise, X.size)
    
    # filter data
    f = LinearSystem(pos_init=data[0], dt=X[1]-X[0],
                     sig_pos=0, sig_drift=.9, sig_meas=sig_noise)
    data_predict = [data[0]]
    data_estimate = [data[0]]
    for y in data[1:]:
        data_predict.append(f.predicted_pos())
        f.add_pos_measurement(y)
        data_estimate.append(f.current_pos())
    
    # plot result
    plt.plot(X, data_orig, "b--", label="original data")
    plt.plot(X, data, "b-", label="data + noise")
    plt.plot(X, data_predict, "r-", label="kalman prediction")
    plt.plot(X, data_estimate, "r--", label="kalman estimate")
    plt.legend()
    plt.show()
    