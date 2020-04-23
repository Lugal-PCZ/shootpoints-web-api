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


def save_station(name: str, coordinatesystem: str, coordinates: dict) -> bool:
    """Saves the given station name and coordinates to the database"""
    errors = []
    # Latitude, longitude, and UTM zone are not needed or 
    # calculated when the coordinate system is 'Site'.
    latitude = None
    longitude = None
    utmzone = None
    if coordinatesystem == 'Site' or coordinatesystem == 'UTM':
        try:
            northing = float(coordinates['northing'])
            easting = float(coordinates['easting'])
        except ValueError as badvalue:
            badvalue = str(badvalue)[36:-1]
            errors.append(f'Non-numeric northing or easting given ({badvalue}).')
        else:
            if coordinatesystem == 'UTM':
                try:
                    if 0 <= northing <= 10000000:
                        raise InvalidUTMCoordinate
                    if 0 <= easting <= 1000000:
                        raise InvalidUTMCoordinate
                    utmzone = coordinates['utmzone'].upper()
                    utmzonenumber = int(utmzone[:-1])
                    if not 1 <= utmzonenumber <= 60:
                        raise InvalidUTMZoneNumber
                    utmzoneletter = utmzone[-1]
                    if utmzoneletter not in 'CDEFGHJKLMNPQRSTUVWX':
                        raise InvalidUTMZoneLetter
                except InvalidUTMCoordinate:
                    errors.append(f'Northing or Easting given is out of range.')
                except KeyError:
                    errors.append(f'UTM Zone not given.')
                except ValueError:
                    errors.append(f'Non-numeric UTM Zone number given ({utmzonenumber}).')
                except InvalidUTMZoneNumber:
                    errors.append(f'Invalid UTM Zone number given ({utmzonenumber}).')
                except InvalidUTMZoneLetter:
                    errors.append(f'Invalid UTM Zone letter given ({utmzoneletter}).')
                else:
                    latitude, longitude = angle_math.convert_utm_to_latlon(northing, easting, utmzonenumber, utmzoneletter)
    elif coordinatesystem == 'Lat/Lon':
        try:
            latitude = float(coordinates['latitude'])
            longitude = float(coordinates['longitude'])
        except KeyError as missingkey:
            errors.append(f'Station {missingkey} not given.')
        except ValueError as badvalue:
            errors.append(f'Non-numeric latitude or longitude given ({badvalue}).')
        else:
            northing, easting, utmzone = angle_math.convert_latlon_to_utm(latitude, longitude)
    else:
        message = (
            f'Invalid coordinate system given ({coordinatesystem}).'
            f' Should be one of Site, UTM, or Lat/Lon.'
        )
        errors.append(message)
    try:
        elevation = float(coordinates['elevation'])
    except KeyError:
        errors.append(f'Station elevation not given.')
    except ValueError:
        errors.append(f'Non-numeric elevation given ({elevation}).')
    if not errors:
        sql = (
            f'INSERT INTO stations '
            f'(name, northing, easting, elevation, utmzone, latitude, longitude) '
            f'VALUES (?, ?, ?, ?, ?, ?, ?)'
        )
        if not data.save_to_database(sql, (name, northing, easting, elevation, utmzone, latitude, longitude)):
            errors.append(f'Station ({name}) not saved to the database.')
    if errors:
        result = {'success': False, 'errors': errors}
    else:
        result = {'success': True, 'result': f'Station {name} saved to the database.'}
    return result


class InvalidUTMZoneNumber(Exception):
    """Raised when the UTM Zone Number is not between 1 and 60 (inclusive)."""
    pass


class InvalidUTMZoneLetter(Exception):
    """Raised when the UTM Zone Letter is not one of CDEFGHJKLMNPQRSTUVWX."""
    pass


class InvalidUTMCoordinate(Exception):
    """Raised when a UTM coordinate is negative."""
    pass
