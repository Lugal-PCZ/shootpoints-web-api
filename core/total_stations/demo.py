"""
This module contains faked data responses for an imaginary total station,
for when ShootPoints is run in demo mode.
"""

from time import sleep as _sleep
from random import randint as _randint


_canceled = False


def set_mode_hr() -> dict:
    """This function sets the total station to V/H mode with Horizontal Right."""
    outcome = {"errors": [], "result": ""}
    outcome["result"] = "Mode set to Horizontal Right."
    return {key: val for key, val in outcome.items() if val}


def set_azimuth(degrees: int = 0, minutes: int = 0, seconds: int = 0) -> dict:
    """This function sets the azimuth reading on the total station."""
    outcome = {"errors": [], "result": ""}
    try:
        degrees = int(degrees)
        if not 0 <= degrees <= 359:
            outcome["errors"].append(
                f"Degrees entered ({degrees}) is out of range (0 to 359)."
            )
    except ValueError:
        outcome["errors"].append(
            f"A non-integer value ({degrees}) was entered for degrees."
        )
    try:
        minutes = int(minutes)
        if not 0 <= minutes <= 59:
            outcome["errors"].append(
                f"Minutes entered ({minutes}) is out of range (0 to 59)."
            )
    except ValueError:
        outcome["errors"].append(
            f"A non-integer value ({minutes}) was entered for minutes."
        )
    try:
        seconds = int(seconds)
        if not 0 <= seconds <= 59:
            outcome["errors"].append(
                f"Seconds entered ({seconds}) is out of range (0 to 59)."
            )
    except ValueError:
        outcome["errors"].append(
            f"A non-integer value ({seconds}) was entered for seconds."
        )
    if not outcome["errors"]:
        outcome["result"] = f"Azimuth set to {degrees}° {minutes}' {seconds}\""
    return {key: val for key, val in outcome.items() if val}


def take_measurement() -> dict:
    """This function tells the total station to begin measuring a point."""
    outcome = {"errors": [], "measurement": {}, "notification": ""}
    global _canceled
    if _canceled:
        _canceled = not _canceled
    delay = 4
    for i in range(delay - 1):
        _sleep(i)
        if _canceled:
            _canceled = False
            return
    delta_n = round((496337 + _randint(-50000, 50000)) / 10000, 3)
    delta_e = round((311930 + _randint(-50000, 50000)) / 10000, 3)
    delta_z = round((95802 + _randint(-10000, 10000)) / 10000, 3)
    outcome["measurement"] = {
        "delta_n": delta_n,
        "delta_e": delta_e,
        "delta_z": delta_z,
    }
    return {key: val for key, val in outcome.items() if val}


def cancel_measurement() -> dict:
    """This function cancels a measurement in progress."""
    global _canceled
    _canceled = True
    return {"notification": "Measurement canceled by user."}
