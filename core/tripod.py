"""This module handles the coordinates of the occupied point and the instrument height."""

from . import _database
from . import _calculations


occupied_point = {
    'n': 0.0,
    'e': 0.0,
    'z': 0.0,
}

instrument_height = 0.0


def _validate_elevation(elevation: float, errors: list) -> None:
    """This function verifies that the elevation given is a float."""
    try:
        float(elevation)
    except ValueError:
        errors.append(f'Non-numeric elevation given ({elevation}).')


def _validate_site_coordinates(northing: float, easting: float, errors: list) -> None:
    """This function verifies that the northing and easting given are floats."""
    try:
        float(northing)
    except ValueError:
        errors.append(f'Non-numeric northing given ({northing}).')
    try:
        float(easting)
    except ValueError:
        errors.append(f'Non-numeric easting given ({easting}).')


def _validate_utm_coordinates(northing: float, easting: float, utmzone: str, errors: list) -> None:
    """This function verifies the validity of the UTM coordinates given."""
    try:
        float(northing)
    except ValueError:
        errors.append(f'Non-numeric northing given ({northing}).')
    else:
        if not 0 <= northing <= 10000000:
            errors.append(f'Northing given ({northing}) is out of range (0–10000000m).')
    try:
        float(easting)
    except ValueError:
        errors.append(f'Non-numeric easting given ({easting}).')
    else:
        if not 100000 <= easting <= 999999:
            errors.append(f'Easting given ({easting}) is out of range (100000–999999m).')
    try:
        utmzone = str(utmzone).upper()
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


def _validate_latlong_coordinates(latitude: float, longitude: float, errors: list) -> None:
    """This function verifies the validity of the Latitude and Longitude coordinates given."""
    try:
        latitude = float(latitude)
    except ValueError:
        errors.append(f"Non-numeric latitude given ({latitude}).")
    else:
        if not 0 <= latitude <= 90:
            errors.append('Latitude given is out of range (0–90°).')
    try:
        longitude = float(longitude)
    except ValueError:
        errors.append(f"Non-numeric latitude given ({longitude}).")
    else:
        if not -180 <= longitude <= 180:
            errors.append('Longitude given is out of range (±180°).')


def _validate_uniqueness_of_station(sites_id: int, name: str, northing: float, easting: float, errors: list) -> None:
    """This function verifies that the station name is unique at this site, as is its northing and easting."""
    sitename = _database.read_from_database('SELECT name FROM sites WHERE id = ?', (sites_id,))['results'][0]['name']
    if sitename:
        if _database.read_from_database('SELECT count(*) FROM stations WHERE sites_id = ? AND upper(name) = ?', (sites_id, name.upper()))['results'][0]['count(*)']:
            errors.append(f'The station name “{name}” is not unique at site “{sitename}.”')
        if _database.read_from_database('SELECT count(*) FROM stations WHERE sites_id = ? AND (? BETWEEN northing-0.1 AND northing+0.1) AND (? BETWEEN easting-0.1 AND easting+0.1)', (sites_id, northing, easting))['results'][0]['count(*)']:
            errors.append(f'The station coordinates are not unique at site “{sitename}.”')
    else:
        errors.append(f'There is no site with id {sites_id}.')


def _validate_instrument_height(height: float, errors: list) -> dict:
    """This function checks the sanity of the instrument height above the occupied point."""
    try:
        height = float(height)
        if height < 0:
            errors.append(f'Instrument height entered ({height}m) is negative.')
        elif height >= 2:
            errors.append(f'Instrument height entered ({height}m) is unrealistically high.')
    except ValueError:
        errors.append(f'Instrument height entered ({height}m) is not numeric.')


def get_station(sites_id: int, id: int) -> dict:
    """"This function returns the name and coordinates of the indicated station."""
    outcome = {'errors': [], 'station': {}}
    query = _database.read_from_database('SELECT * FROM stations WHERE sites_id = ? AND id = ?', (sites_id, id,))
    if query['success'] and len(query['results']) > 0:
        outcome['station'] = query['results'][0]
    else:
        outcome['errors'].append(f'Station id {id} was not found at this site.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def get_all_stations_at_site(sites_id: int) -> dict:
    """"This function returns the name and coordinates of all the stations at the indicated site."""
    outcome = {'errors': [], 'stations': {}}
    query = _database.read_from_database('SELECT * FROM stations WHERE sites_id = ?', (sites_id,))
    if query['success'] and len(query['results']) > 0:
        outcome['stations'] = query['results']
    else:
        outcome['errors'].append(f'No stations were found at this site.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def save_station(sites_id: int, name: str, coordinatesystem: str, coordinates: dict, description: str=None) -> dict:
    """This function creates a new station record in the database with the given name and coordinates."""
    outcome = {'errors': [], 'result': ''}
    _validate_elevation(coordinates['elevation'], outcome['errors'])
    if coordinatesystem == 'Site':
        # Note: Latitude, longitude, and UTM zone are not needed or calculated when the coordinate system is 'Site'.
        _validate_site_coordinates(coordinates['northing'], coordinates['easting'], outcome['errors'])
        if not outcome['errors']:
            northing = float(coordinates['northing'])
            easting = float(coordinates['easting'])
            elevation = float(coordinates['elevation'])
            latitude = None
            longitude = None
            utmzone = None
    elif coordinatesystem == 'UTM':
        _validate_utm_coordinates(coordinates['northing'], coordinates['easting'], coordinates['utmzone'], outcome['errors'])
        if not outcome['errors']:
            northing = float(coordinates['northing'])
            easting = float(coordinates['easting'])
            elevation = float(coordinates['elevation'])
            latitude, longitude = _calculations.convert_utm_to_latlon(
                northing,
                easting,
                coordinates['utmzone'][:-1],
                coordinates['utmzone'][-1].upper()
            )
    elif coordinatesystem == 'Lat/Lon':
        _validate_latlong_coordinates(coordinates['latitude'], coordinates['longitude'], outcome['errors'])
        if not outcome['errors']:
            latitude = float(coordinates['latitude'])
            longitude = float(coordinates['longitude'])
            elevation = float(coordinates['elevation'])
            northing, easting, utmzone = _calculations.convert_latlon_to_utm(latitude, longitude)
    else:
        outcome['errors'].append(f'Invalid coordinate system given ({coordinatesystem}) It should be one of Site, UTM, or Lat/Lon.')
    if not outcome['errors']:
        name = name.strip()
        _validate_uniqueness_of_station(sites_id, name, northing, easting, outcome['errors'])
        if not outcome['errors']:
            sql = (
                f'INSERT INTO stations '
                f'(sites_id, name, northing, easting, elevation, utmzone, latitude, longitude, description) '
                f'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
            )
            newstation = (sites_id, name, northing, easting, elevation, utmzone, latitude, longitude, description)
            if _database.save_to_database(sql, newstation)['success']:
                outcome['result'] = f'Station {name} saved to the database.'
            else:
                outcome['errors'].append(f'Station ({name}) could not be saved to the database.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def delete_station(id: int) -> dict:
    """This function deletes the indicated station from the database."""
    outcome = {'errors': [], 'results': ''}
    exists = _database.read_from_database('SELECT name FROM stations WHERE id = ?', (id,))
    if exists['success']:
        try:
            name = exists['results'][0]['name']
            sql = 'DELETE FROM stations WHERE id = ?'
            deleted = _database.delete_from_database(sql, (id,))
            if deleted['success']:
                outcome['result'] = f'Station “{name}” successfully deleted from the database.'
            else:
                outcome['errors'] = deleted['errors']
        except IndexError:
            outcome['errors'].append(f'Station id {id} does not exist.')
        if outcome['errors'][0] == 'FOREIGN KEY constraint failed':
            outcome['errors'][0] = f'Station “{name}” could not be deleted because it is a foreign key for one or more sessions.'
    else:
        outcome['errors'] = exists['errors']
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}
