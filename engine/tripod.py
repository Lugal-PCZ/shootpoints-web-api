# TODO: rename this file to tripod.py
from . import angle_math
from . import data


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
        'result': _occupied_point
    }


def set_occupied_point(n: float, e: float, z: float) -> dict:
    global _occupied_point
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
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        _occupied_point['n'] = n
        _occupied_point['e'] = e
        _occupied_point['z'] = z
        result['result'] = f'Occupied Point set to {n}N, {e}E, {z}Z.'
    return result


def get_instrument_height() -> dict:
    global _instrument_height
    return {
        'success': True,
        'result': _instrument_height
    }


def set_instrument_height(height: float) -> dict:
    global _instrument_height
    errors = []
    try:
        height = float(height)
        if height < 0:
            errors.append(f'Instrument height entered ({height}m) is negative.')
        elif height >= 2:
            errors.append(f'Instrument height entered ({height}m) is unrealistically high.')
    except ValueError:
        errors.append(f'Instrument height entered ({height}m) is not numeric.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        _instrument_height = height
        result['result'] = f'Instrument height set to {height}m.'
    return result


def save_station(name: str, coordinatesystem: str, coordinates: dict) -> bool:
    """Saves the given station name and coordinates to the database"""
    errors = []
    # Check that the given elevation is valid.
    try:
        elevation = float(coordinates['elevation'])
    except KeyError:
        errors.append(f'Station elevation not given.')
    except ValueError:
        errors.append(f'Non-numeric elevation given ({elevation}).')
    if coordinatesystem == 'Site' or coordinatesystem == 'UTM':
        # Check that the given northing is valid.
        try:
            northing = float(coordinates['northing'])
        except KeyError:
            errors.append(f'Station northing not given.')
        except ValueError:
            errors.append(f"Non-numeric northing given ({coordinates['northing']}).")
        else:
            if 0 <= northing <= 10000000:
                errors.append('Northing given is out of range (0–10000000m).')
        # Check that the given easting is valid.
        try:
            easting = float(coordinates['easting'])
        except KeyError:
            errors.append(f'Station easting not given.')
        except ValueError:
            errors.append(f"Non-numeric easting given ({coordinates['easting']}).")
        else:
            if 0 <= easting <= 1000000:
                errors.append('Easting given is out of range (0–1000000m).')
        if coordinatesystem == 'Site':
            # Latitude, longitude, and UTM zone are not needed or 
            # calculated when the coordinate system is 'Site'.
            latitude = None
            longitude = None
            utmzone = None
        elif coordinatesystem == 'UTM':
            # Check that the given UTM zone is valid.
            try:
                utmzone = str(coordinates['utmzone']).upper()
                utmzonenumber = int(utmzone[:-1])
            except KeyError:
                errors.append(f'UTM Zone not given.')
            except ValueError:
                errors.append(f'Non-numeric UTM Zone number given ({utmzonenumber}).')
            else:
                if not 1 <= utmzonenumber <= 60:
                    errors.append(f'Invalid UTM Zone number given ({utmzonenumber}).')
                else:
                    utmzoneletter = utmzone[-1]
                    if utmzoneletter not in 'CDEFGHJKLMNPQRSTUVWX':
                        errors.append(f'Invalid UTM Zone letter given ({utmzoneletter}).')
                    else:
                        latitude, longitude = angle_math.convert_utm_to_latlon(northing, easting, utmzonenumber, utmzoneletter)
    elif coordinatesystem == 'Lat/Lon':
        # Check that the given latitude is valid.
        try:
            latitude = float(coordinates['latitude'])
        except KeyError:
            errors.append('Station latitude not given.')
        except ValueError:
            errors.append(f"Non-numeric latitude given ({coordinates['latitude']}).")
        else:
            if 0 <= latitude <= 90:
                errors.append('Latitude given is out of range (0–90°).')
        # Check that the given longitude is valid.
        try:
            longitude = float(coordinates['longitude'])
        except KeyError:
            errors.append('Station longitude not given.')
        except ValueError:
            errors.append(f"Non-numeric latitude given ({coordinates['longitude']}).")
        else:
            if -180 <= longitude <= 180:
                errors.append('Longitude given is out of range (-180–180°).')
            else:
                northing, easting, utmzone = angle_math.convert_latlon_to_utm(latitude, longitude)
    else:
        errors.append(
            f'Invalid coordinate system given ({coordinatesystem}).'
            f' It should be one of Site, UTM, or Lat/Lon.'
        )
    if not errors:
        sql = (
            f'INSERT INTO stations '
            f'(name, northing, easting, elevation, utmzone, latitude, longitude) '
            f'VALUES (?, ?, ?, ?, ?, ?, ?)'
        )
        newstation = (name, northing, easting, elevation, utmzone, latitude, longitude)
        if not data.save_to_database(sql, newstation)['success']:
            errors.append(f'Station ({name}) not saved to the database.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        result['result'] = f'Station {name} saved to the database.'
    return result
