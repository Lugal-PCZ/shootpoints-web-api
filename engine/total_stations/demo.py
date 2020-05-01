"""
This module contains faked data responses for an imaginary total station,
for when ShootPoints is run in demo mode.
"""

from time import sleep as _sleep
from random import randint as _randint


_canceled = False


def set_mode_hr() -> dict:
    """Sets the total station to V/H mode with Horizontal Right."""
    return {
        'success': True,
        'result': 'Mode set to Horizontal Right.',
    }


def set_azimuth(degrees: int=0, minutes: int=0, seconds: int=0) -> dict:
    """Sets the azimuth reading on the total station."""
    errors = []
    try:
        degrees = int(degrees)
        if not 0 <= degrees <= 359:
            errors.append(f'Degrees entered ({degrees}) is out of range (0 to 359).')
    except ValueError:
        errors.append(f'A non-integer value ({degrees}) was entered for degrees.')
    try:
        minutes = int(minutes)
        if not 0 <= minutes <= 59:
            errors.append(f'Minutes entered ({minutes}) is out of range (0 to 59).')
    except ValueError:
        errors.append(f'A non-integer value ({minutes}) was entered for minutes.')
    try:
        seconds = int(seconds)
        if not 0 <= seconds <= 59:
            errors.append(f'Seconds entered ({seconds}) is out of range (0 to 59).')
    except ValueError:
        errors.append(f'A non-integer value ({seconds}) was entered for seconds.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        result['result'] = f'Azimuth set to {degrees}° {minutes}\' {seconds}"',
    return result


def take_measurement() -> dict:
    """Tells the total station to begin measuring a point."""
    global _canceled
    delay = 5
    for _ in range(delay - 1):
        _sleep(_)
        if _canceled:
            _canceled = False
            return
    delta_n = round((496337 + _randint(-50000, 50000)) / 10000, 3)
    delta_e = round((311930 + _randint(-50000, 50000)) / 10000, 3)
    delta_z = round((95802 + _randint(-10000, 10000)) / 10000, 3)
    return {
        'success': True,
        'result': {'delta_n': delta_n, 'delta_e': delta_e, 'delta_z': delta_z},
    }


def cancel_measurement() -> dict:
    """Cancels a measurement in progress."""
    global _canceled
    _canceled = True
    return {
        'success': True,
        'result': 'Measurement canceled by user.',
    }
