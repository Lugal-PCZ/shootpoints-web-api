"""This module contains utility functions for code readability that couldn’t be included in __init__.py because of circular imports."""


def format_outcome(outcome: dict, special_keys: list = []):
    """
    This function formats the output dictionary from shootpoints-web-api functions in the manner that
    shootpoints-web-frontend expects. Empty values are discarded, except when special_keys are specified.
    """
    if special_keys:
        return {key: val for key, val in outcome.items() if val or key in special_keys}
    else:
        return {key: val for key, val in outcome.items() if val}
