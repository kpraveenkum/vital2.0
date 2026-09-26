"""
statistics.py

Statistical helper functions for evaluating differences between CONTROL (Feedback OFF)
and FEEDBACK (Feedback ON) WRF-Chem numerical experiments.
"""

import numpy as np


def difference(feedback, control):
    return np.asarray(feedback) - np.asarray(control)


def mean_difference(feedback, control):
    delta = difference(feedback, control)
    return float(np.nanmean(delta))


def absolute_mean_difference(feedback, control):
    delta = difference(feedback, control)
    return float(np.nanmean(np.abs(delta)))


def percent_change(feedback, control):
    feedback = np.asarray(feedback, dtype=float)
    control = np.asarray(control, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = (feedback - control) / np.abs(control) * 100.0
    return result


def summary(feedback, control, name):
    delta = difference(feedback, control)
    return {
        "variable": name,
        "control_mean": float(np.nanmean(control)),
        "feedback_mean": float(np.nanmean(feedback)),
        "mean_difference": float(np.nanmean(delta)),
        "absolute_mean_difference": float(np.nanmean(np.abs(delta))),
        "minimum_difference": float(np.nanmin(delta)),
        "maximum_difference": float(np.nanmax(delta)),
    }
