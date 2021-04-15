"""This module contains functions for handling the surveying session and associated data."""

from . import _database
from . import _calculations
from . import tripod
from . import prism


backsighterrorlimit = 0.0
totalstation = None
sessionid = 0
groupingid = 0
activeshotdata = {}
activeshotlabel = ''


def _get_setup_errors() -> list:
    outcome = _database.read_from_database('SELECT * FROM setuperrors')
    errors = []
    try:
        for each in outcome['results']:
            errors.append(each['error'])
    except:
        pass
    return errors


def _save_new_session(data: tuple) -> int:
    """This function saves the surveying session information to the database."""
    global sessionid
    global groupingid
    global activeshotdata
    global activeshotlabel
    sql = (
        'INSERT INTO sessions '
        '(label, started, surveyor, sites_id, stations_id_occupied, stations_id_backsight, azimuth, instrumentheight) '
        'VALUES(?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)'
    )
    if _database.save_to_database(sql, data)['success']:
        sessionid = _database.cursor.lastrowid
    else:
        sessionid = 0
    groupingid = 0
    activeshotdata = {}
    activeshotlabel = ''
    return sessionid


def start_surveying_session_with_backsight(label: str, surveyor: str, sites_id: int, occupied_point_id: int, backsight_station_id: int, prism_height: float) -> dict:
    """This function starts a new surveying session with a backsight to a known point."""
    outcome = {'errors': _get_setup_errors(), 'result': ''}
    if not outcome['errors']:
        if occupied_point_id == backsight_station_id:
            outcome['errors'].append(f'The Occupied Point and Backsight Station are the same (id = {occupied_point_id}).')
        occupiedpoint = tripod.get_station(sites_id, occupied_point_id)
        if occupiedpoint['success']:
            occupied_n = occupiedpoint['station']['northing']
            occupied_e = occupiedpoint['station']['easting']
            occupied_z = occupiedpoint['station']['elevation']
        else:
            outcome['errors'].extend(occupiedpoint['errors'])
        backsightstation = tripod.get_station(sites_id, backsight_station_id)
        if backsightstation['success']:
            backsight_n = backsightstation['station']['northing']
            backsight_e = backsightstation['station']['easting']
            backsight_z = backsightstation['station']['elevation']
        else:
            outcome['errors'].extend(backsightstation['errors'])
        if prism_height < 0:
            outcome['errors'].append(f'An invalid prism height ({prism_height}m) was entered.')
        else:
            newoffsets = {each_offset:0 for each_offset in prism.offsets}
            newoffsets['vertical_distance'] = prism_height
            newoffsets['vertical_direction'] = 'Down'
            prism.set_prism_offsets(**newoffsets)
        if not outcome['errors']:
            azimuth = _calculations.calculate_azimuth(
                (occupied_n, occupied_e),
                (backsight_n, backsight_e)
            )
            degrees, remainder = divmod(azimuth, 1)
            minutes, remainder = divmod(remainder * 60, 1)
            seconds = round(remainder * 60)
            degrees, minutes, seconds = int(degrees), int(minutes), int(seconds)
            setazimuth = totalstation.set_azimuth(degrees, minutes, seconds)
            if setazimuth['success']:
                measurement = totalstation.take_measurement()
                if measurement['success']:
                    variance = _calculations.calculate_backsight_variance(
                        occupied_n, 
                        occupied_e,
                        backsight_n,
                        backsight_e,
                        measurement['measurement']['delta_n'],
                        measurement['measurement']['delta_e']
                    )
                    if variance >= backsighterrorlimit:
                        outcome['errors'].append(f'The measured distance between the Occupied Point and the Backsight Station ({variance}cm) exceeds the limit set in configs.ini ({backsighterrorlimit}cm).')
                    elev_diff_of_points = occupied_z - backsight_z
                    delta_z_to_point = measurement['measurement']['delta_z'] - prism_height
                    instrument_height = elev_diff_of_points + delta_z_to_point
                    tripod._validate_instrument_height(instrument_height, outcome['errors'])
                else:
                    outcome['errors'].extend(measurement['errors'])
            else:
                outcome['errors'].extend(setazimuth['errors'])
        if not outcome['errors']:
            data = (
                label,
                surveyor,
                sites_id,
                occupied_point_id,
                backsight_station_id,
                f'{degrees}° {minutes}\' {seconds}"',
                instrument_height,
            )
            if sessionid := _save_new_session(data):
                tripod.occupied_point = {'n': occupied_n, 'e': occupied_e, 'z': occupied_z}
                tripod.instrument_height = instrument_height
                outcome['result'] = f'Session {sessionid} started.'
            else:
                outcome['errors'].append('A problem occurred while saving the new session to the database.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def start_surveying_session_with_azimuth(label: str, surveyor: str, sites_id: int, occupied_point_id: int, instrument_height: float, azimuth: float) -> dict:
    """This function starts a new surveying session with an azimuth to a landmark."""
    outcome = {'errors': _get_setup_errors(), 'result': ''}
    if not outcome['errors']:
        occupiedpoint = tripod.get_station(sites_id, occupied_point_id)
        if occupiedpoint['success']:
            occupied_n = occupiedpoint['station']['northing']
            occupied_e = occupiedpoint['station']['easting']
            occupied_z = occupiedpoint['station']['elevation']
        else:
            outcome['errors'].extend(occupiedpoint['errors'])
        if not outcome['errors']:
            degrees, remainder = divmod(azimuth, 1)
            minutes, remainder = divmod(remainder * 100, 1)
            seconds = round(remainder * 100)
            degrees, minutes, seconds = int(degrees), int(minutes), int(seconds)
            setazimuth = totalstation.set_azimuth(degrees, minutes, seconds)
            if setazimuth['success']:
                data = (
                    label,
                    surveyor,
                    sites_id,
                    occupied_point_id,
                    None,  # There is no backsight station in this setup, but _save_new_session() expects a value.
                    f'{degrees}° {minutes}\' {seconds}"',
                    instrument_height,
                )
                if sessionid := _save_new_session(data):
                    tripod.occupied_point = {'n': occupied_n, 'e': occupied_e, 'z': occupied_z}
                    tripod.instrument_height = instrument_height
                    outcome['result'] = f'Session {sessionid} started.'
                else:
                    outcome['errors'].append(f'A problem occurred while saving the new session to the database.')
            else:
                outcome['errors'].extend(setazimuth['errors'])
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def start_new_grouping(geometry_id: int, subclasses_id: int, label: str=None, comment: str=None) -> dict:
    """This function begins recording a grouping of total station measurements."""
    outcome = {'errors': [], 'result': ''}
    global groupingid
    sql = (
        'INSERT INTO groupings '
        '(sessions_id, geometry_id, subclasses_id, label, comment) '
        'VALUES(?, ?, ?, ?, ?)'
    )
    if _database.save_to_database(sql, (sessionid, geometry_id, subclasses_id, label, comment))['success']:
        groupingid = _database.cursor.lastrowid
    else:
        groupingid = 0
        outcome['errors'].append('An error occurred while starting the new grouping.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def take_shot() -> dict:
    """This function instructs the total station to take a measurement, applies the offsets, and augments it with metadata."""
    outcome = {'errors': [], 'result': ''}
    global activeshotdata
    if not sessionid:
        outcome['errors'].append('No shot taken because there is no active surveying session.')
    elif not groupingid:
        outcome['errors'].append('No shot taken because there is no active shot grouping.')
    else:
        measurement = totalstation.take_measurement()
        if 'notification' in measurement:
            outcome['result'] = measurement['notification']
        elif 'errors' in measurement:
            outcome['errors'] = measurement['errors']
        else:
            outcome['result'] = _calculations.apply_offsets_to_measurement(measurement['measurement'])
            activeshotdata = outcome['result']
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def save_last_shot(label: str=None, comment: str=None) -> dict:
    """This function saves the data from the last shot to the database."""
    outcome = {'errors': [], 'result': ''}
    global activeshotdata
    global activeshotlabel
    if not activeshotdata:
        outcome['errors'].append('Shot not saved because there is no unsaved shot data.')
    else:
        try:
            label = label.strip()
        except AttributeError:
            pass
        data = (
            activeshotdata['delta_n'],
            activeshotdata['delta_e'],
            activeshotdata['delta_z'],
            activeshotdata['calculated_n'],
            activeshotdata['calculated_e'],
            activeshotdata['calculated_z'],
            prism.offsets['vertical_distance'],
            prism.offsets['latitude_distance'],
            prism.offsets['longitude_distance'],
            prism.offsets['radial_distance'],
            prism.offsets['tangent_distance'],
            prism.offsets['wedge_distance'],
            groupingid,
            label,
            comment,
        )
        sql = (
            'INSERT INTO shots '
            '(timestamp, delta_n, delta_e, delta_z, northing, easting, elevation, prismoffset_vertical, prismoffset_latitude, prismoffset_longitude, prismoffset_radial, prismoffset_tangent, prismoffset_wedge, groupings_id, label, comment) '
            'VALUES(CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        )
        if _database.save_to_database(sql, data)['success']:
            activeshotdata = {}
            activeshotlabel = label
            if _database.read_from_database('SELECT geometry_id FROM groupings WHERE id = ?', (groupingid,))['results'] == 1:
                groupingid = 0  # The active shot is an isolated point, so reset the groupingid to 0
        else:
            outcome['errors'].append('An error occurred while saving the last shot.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}
