# Set the default setup station coordinates and instrument height.

_occupied_point = {
    'n': 0.0,
    'e': 0.0,
    'z': 0.0,
}

_instrument_height = 0.0


def get_occupied_point() -> dict:
    global _occupied_point
    return {
        'success': True,
        'coordinates': _occupied_point
    }

def set_occupied_point(n: float=None, e: float=None, z: float=None) -> dict:
# TODO: save occupied point to DB for stability.
    global _occupied_point
    if not n:
        n = _occupied_point['n']
    if not e:
        e = _occupied_point['e']
    if not z:
        z = _occupied_point['z']
    errors = []
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
    if errors:
        result = {'success': False, 'errors': errors}
    else:
        _occupied_point['n'] = n
        _occupied_point['e'] = e
        _occupied_point['z'] = z
        result = get_occupied_point()
    return result

def get_instrument_height() -> dict:
    global _instrument_height
    return {
        'success': True,
        'instrument_height': _instrument_height
    }

def set_instrument_height(height: float=None) -> dict:
# TODO: save instrument height to DB for stability.
    global _instrument_height
    if not height:
        height = _instrument_height
    errors = []
    try:
        height = float(height)
    except ValueError:
        errors.append(f'Instrument height entered ({height}m) is not numeric.')
    else:
        if height < 0:
            errors.append(f'Instrument height entered ({height}m) is negative.')
        elif height >= 2:
            errors.append(f'Instrument height entered ({height}m) is unrealistically high.')
    if errors:
        result = {'success': False, 'errors': errors}
    else:
        _instrument_height = height
        result = get_instrument_height()
    return result
