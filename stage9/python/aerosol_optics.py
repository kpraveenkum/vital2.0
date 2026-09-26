"""
aerosol_optics.py

Diagnostic helper functions for calculating aerosol optical depth (AOD)
from vertical extinction profiles and radiation differences.
"""

import numpy as np


def _trapz(y, x, axis=-1):
    if hasattr(np, "trapezoid"):
        return np.trapezoid(y, x, axis=axis)
    return np.trapz(y, x, axis=axis)


def optical_depth_from_extinction(extinction, height, axis=-1):
    """
    Numerical approximation:
        AOD = integral(beta_ext dz)

    extinction: aerosol extinction coefficient
    height: vertical coordinate in metres
    """
    extinction = np.asarray(extinction, dtype=float)
    height = np.asarray(height, dtype=float)
    return _trapz(extinction, height, axis=axis)


def radiation_difference(feedback, control):
    return np.asarray(feedback) - np.asarray(control)
