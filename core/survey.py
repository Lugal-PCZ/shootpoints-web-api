"""This module contains functions for handling the surveying session and associated data."""

from . import _database
from . import _calculations
from . import tripod
from . import prism


backsighterrorlimit = 0.0
totalstation = None
sessionid = 0
groupingid = 0
lastshotdata = {}
lastshotsequence = 0
lastshotlabel = ''


def get_setup_errors() -> list:
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
    global lastshotdata
    global lastshotsequence
    global lastshotlabel
    sql = (
        'INSERT INTO sessions '
        '(label, started, surveyor, stations_id_occupied, stations_id_backsight, azimuth, instrumentheight) '
        'VALUES(?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)'
    )
    if _database.save_to_database(sql, data)['success']:
        sessionid = _database.cursor.lastrowid
    else:
        sessionid = 0
    groupingid = 0
    lastshotdata = {}
    lastshotsequence = 0
    lastshotlabel = ''
    return sessionid


def start_surveying_session_with_backsight(label: str, surveyor: str, occupied_point_id: int, backsight_station_id: int, prism_height: float) -> dict:
    """This function starts a new surveying session with a backsight to a known point."""
    outcome = {'errors': get_setup_errors(), 'result': ''}
    if not outcome['errors']:
        end_surveying_session()  # End the current session, if it's still open.
        if occupied_point_id == backsight_station_id:
            outcome['errors'].append(f'The Occupied Point and Backsight Station are the same (id = {occupied_point_id}).')
        occupiedpoint = tripod.get_station(occupied_point_id)
        if occupiedpoint['success']:
            occupied_n = occupiedpoint['station']['northing']
            occupied_e = occupiedpoint['station']['easting']
            occupied_z = occupiedpoint['station']['elevation']
        else:
            outcome['errors'].extend(occupiedpoint['errors'])
        backsightstation = tripod.get_station(backsight_station_id)
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


def start_surveying_session_with_azimuth(label: str, surveyor: str, occupied_point_id: int, instrument_height: float, azimuth: float) -> dict:
    """This function starts a new surveying session with an azimuth to a landmark."""
    outcome = {'errors': get_setup_errors(), 'result': ''}
    if not outcome['errors']:
        end_surveying_session()  # End the current session, if it's still open.
        occupiedpoint = tripod.get_station(occupied_point_id)
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


def end_surveying_session() -> dict:
    """This function ends a surveying session."""
    outcome = {'errors': [], 'result': ''}
    global sessionid
    if sessionid:
        sql = "UPDATE sessions SET ended = CURRENT_TIMESTAMP WHERE id = ?"
        if _database.save_to_database(sql, (sessionid,))['success']:
            outcome['result'] = f'Session {sessionid} ended.'
        else:
            outcome['errors'].append(f'An error occurred closing the session. Session {sessionid} is still active.')
    else:
        outcome['errors'].append('There is no currently active surveying session.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def start_new_grouping(geometry_id: int, subclasses_id: int, label: str=None) -> dict:
    """This function begins recording a grouping of total station measurements."""
    outcome = {'errors': [], 'result': ''}
    global groupingid
    sql = (
        'INSERT INTO groupings '
        '(sessions_id, geometry_id, subclasses_id, label) '
        'VALUES(?, ?, ?, ?)'
    )
    if _database.save_to_database(sql, (sessionid, geometry_id, subclasses_id, label))['success']:
        groupingid = _database.cursor.lastrowid
    else:
        groupingid = 0
        outcome['errors'].append('An error occurred while starting the new grouping.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def take_shot() -> dict:
    """This function instructs the total station to take a measurement, applies the offsets, and augments it with metadata."""
    outcome = {'errors': [], 'result': ''}
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
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}


def save_shot(label: str=None, comment: str=None) -> dict:
    outcome = {'errors': [], 'result': ''}
    global lastshotdata
    global lastshotsequence
    global lastshotlabel
    data = (
        lastshotdata['delta_n'],
        lastshotdata['delta_e'],
        lastshotdata['delta_z'],
        lastshotdata['calculated_n'],
        lastshotdata['calculated_e'],
        lastshotdata['calculated_z'],
        prism.offsets['vertical_distance'],
        prism.offsets['latitude_distance'],
        prism.offsets['longitude_distance'],
        prism.offsets['radial_distance'],
        prism.offsets['tangent_distance'],
        groupingid,
        lastshotsequence + 1,
        label,
        comment,
    )
    sql = (
        'INSERT INTO shots '
        '(timestamp, delta_n, delta_e, delta_z, northing, easting, elevation, prismoffset_vertical, prismoffset_latitude, prismoffset_longitude, prismoffset_radial, prismoffset_tangent, groupings_id, sequenceingroup, label, comment) '
        'VALUES(CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    )
    if _database.save_to_database(sql, data)['success']:
        lastshotdata = {}
        lastshotlabel = label
        lastshotsequence += 1
    else:
        outcome['errors'].append('An error occurred while saving the last shot.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}