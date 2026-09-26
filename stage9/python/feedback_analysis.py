"""
feedback_analysis.py

High-level analysis module for evaluating aerosol-meteorology feedback responses across variables.
"""

try:
    from statistics import summary
except ImportError:
    from python.statistics import summary


def analyze_variable(control, feedback, variable):
    return summary(feedback, control, variable)


def analyze_experiment(control_data, feedback_data):
    variables = [
        "PM25",
        "PBLH",
        "T2",
        "SWDOWN",
        "O3",
        "U10",
        "V10",
    ]

    records = []
    for variable in variables:
        if variable not in control_data or variable not in feedback_data:
            continue

        result = analyze_variable(
            control_data[variable],
            feedback_data[variable],
            variable,
        )
        records.append(result)

    return records
