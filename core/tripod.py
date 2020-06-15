"""This module handles the coordinates of the occupied point and the instrument height."""

from . import database as _database


def get_occupied_point() -> dict:
    """
    This function returns the coordinates of the occupied point.
    (Note that there is no analogous setter function because the 
    coordinates of the occupied point are those of the occupied
    station.)
    """
    outcome = {'errors': _database.get_setup_errors(), 'results': []}
    if not outcome['errors']:
        sessionid = _database.get_current_session_id()
        sql = (
            'SELECT '
                'sta.northing AS n, '
                'sta.easting AS e, '
                'sta.elevation AS z '
            'FROM sessions sess '
            'JOIN stations sta ON sess.stations_id_occupied = sta.id '
            'WHERE sess.id = ?'
        )
        outcome = _database.read_from_database(sql, (sessionid,))
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}


def get_instrument_height() -> dict:
    """This function returns the instrument height above the occupied point."""
    outcome = {'errors': _database.get_setup_errors(), 'results': []}
    if not outcome['errors']:
        sessionid = _database.get_current_session_id()
        sql = ('SELECT instrumentheight FROM sessions WHERE is = ?')
        outcome = _database.read_from_database(sql, (sessionid,))
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}


def validate_instrument_height(height: float) -> dict:
    """This function checks the sanity of the instrument height above the occupied point."""
    outcome = {'errors': [], 'results': []}
    try:
        height = float(height)
        if height < 0:
            outcome['errors'].append(f'Instrument height entered ({height}m) is negative.')
        elif height >= 2:
            outcome['errors'].append(f'Instrument height entered ({height}m) is unrealistically high.')
    except ValueError:
        outcome['errors'].append(f'Instrument height entered ({height}m) is not numeric.')
    if not outcome['errors']:
        outcome['results'] = f'{height}m is a valid instrument height.'
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}
