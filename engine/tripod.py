"""This module handles the coordinates of the occupied point and the instrument height."""

from . import database


_occupied_point = {
    'n': 0.0,
    'e': 0.0,
    'z': 0.0,
}

_instrument_height = 0.0


def get_occupied_point() -> dict:
    """This function returns the coordinates of the occupied point."""
    global _occupied_point
    return {
        'success': True,
        'results': _occupied_point
    }


def set_occupied_point(n: float, e: float, z: float) -> dict:
    """This function sets the coordinates of the occupied point."""
    global _occupied_point
    errors = database.get_setup_errors()
    if not errors:
        try:
            n = float(n)
        except ValueError:
            errors.append(f'Northing entered ({n}) is not numeric.')
        try:
            e = float(e)
        except ValueError:
            errors.append(f'Easting entered ({e}) is not numeric.')
        try:
            z = float(z)
        except ValueError:
            errors.append(f'Elevation entered ({z}) is not numeric.')
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        _occupied_point['n'] = n
        _occupied_point['e'] = e
        _occupied_point['z'] = z
        outcome['results'] = f'Occupied Point set to {n}N, {e}E, {z}Z.'
    return outcome


def get_instrument_height() -> dict:
    """This function returns the instrument height above the occupied point."""
    global _instrument_height
    return {
        'success': True,
        'results': _instrument_height
    }


def set_instrument_height(height: float) -> dict:
    """This function set the instrument height above the occupied point and saves it to the database."""
    global _instrument_height
    errors = database.get_setup_errors()
    if not errors:
        try:
            height = float(height)
            if height < 0:
                errors.append(f'Instrument height entered ({height}m) is negative.')
            elif height >= 2:
                errors.append(f'Instrument height entered ({height}m) is unrealistically high.')
        except ValueError:
            errors.append(f'Instrument height entered ({height}m) is not numeric.')
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        _instrument_height = height
        outcome['results'] = f'Instrument height set to {height}m.'
    return outcome
