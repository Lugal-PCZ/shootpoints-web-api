"""This module contains utility functions for code readability that couldn’t be included in __init__.py because of circular imports."""


def format_outcome(outcome: dict, special_key: str = ""):
    """
    This function formats the output dictionary from shootpoints-web-api functions in the manner that
    shootpoints-web-frontend expects. Empty values are discarded, except when special_key is specified.
    """
    if special_key:
        return {key: val for key, val in outcome.items() if val or key == special_key}
    else:
        return {key: val for key, val in outcome.items() if val}
