"""This package controls all aspects of ShootPoints’ communications with the total station and processing and saving data."""

import configparser
import glob
import importlib
import serial
import math

from . import tripod
from . import prism
from . import calculations
from . import database


configs = None
serialport = None
total_station = None
sessionid = None


def _load_configs():
    """This function loads the configurations from the configs.ini file."""
    global configs
    configs = configparser.RawConfigParser()
    configfile = 'configs.ini'
    try:
        configs.read(configfile)
    except:
        exit(f'FATAL ERROR: The config file ({configfile}) was not found.')


def _load_total_station_model():
    """This function loads the indicated total station."""
    global total_station
    if configs['SERIAL']['port'] == 'demo':
        from .total_stations import demo as total_station
    else:
        make = configs['TOTAL STATION']['make'].replace(' ', '_').lower()
        make = configs['TOTAL STATION']['make'].replace('-', '_').lower()
        model = configs['TOTAL STATION']['model'].replace(' ', '_').lower()
        model = configs['TOTAL STATION']['model'].replace('-', '_').lower()
        if make == 'topcon' and model[:6] == 'gts_30':
            model = 'gts_300_series'
        try:
            total_station = importlib.import_module(f'{__name__}.total_stations.{make}.{model}', package='engine')
        except ModuleNotFoundError:
            exit(f'FATAL ERROR: File total_stations/{make}/{model}.py does not exist.')


def _initialize_serial_port():
    """
    This function finds the appropriate serial port and initializes it
    with the communication parameters for the total station model.
    """
    global serialport
    if configs['SERIAL']['port'] == 'demo':
        return
    if total_station == 'demo':
        return
    if configs['SERIAL']['port'] == 'auto':
        if glob.glob('/dev/cu.ttyAMA*'):  # Linux with RS232 adapter
            serialport = glob.glob('/dev/cu.ttyAMA*')[0]
        elif glob.glob('/dev/ttyUSB*'):  # Linux with USB adapter
            serialport = glob.glob('/dev/cu.ttyUSB*')[0]
        elif glob.glob('/dev/cu.usbserial*'):  # Mac with USB adapter
            serialport = glob.glob('/dev/cu.usbserial*')[0]
        else:  # Serial port not found.
            exit('FATAL ERROR: No valid serial port found.')
    else:  # Port is specified explicitly in configs.ini file.
        serialport = configs['SERIAL']['port']
    try:
        port = serial.Serial(
            port=serialport,
            baudrate=total_station.BAUDRATE,
            parity=total_station.PARITY,
            bytesize=total_station.BYTESIZE,
            stopbits=total_station.STOPBITS,
            timeout=total_station.TIMEOUT,
        )
        total_station.port = port
    except:
        exit(f'FATAL ERROR: Serial port {serialport} could not be opened.')


def _load_session():
    """
    This function loads the active surveying session from the database, prompting 
    the surveyor to start a new session or create a new station record if necessary.
    """
    global sessionid
    sql = "SELECT count(*) AS numstations FROM stations"
    numstations = database.read_from_database(sql)
    if numstations['success']:
        if numstations['results'][0]['numstations']:
            sql = "SELECT id FROM sessions WHERE ended IS NULL ORDER BY started DESC LIMIT 1"
            currentsession = database.read_from_database(sql)
            if currentsession['success']:
                if len(currentsession['results']) > 0:
                    sessions_id = currentsession['results'][0]['id']
                    database.update_current_state({'sessions_id': sessions_id})
                    sql = (
                        'SELECT '
                            'curr.sessions_id, '
                            'sess.stations_id_occupied, '
                            'sta.northing, '
                            'sta.easting, '
                            'sta.elevation, '
                            'sess.instrumentheight, '
                            'curr.vertical_distance, '
                            'curr.latitude_distance, '
                            'curr.longitude_distance, '
                            'curr.radial_distance, '
                            'curr.tangent_distance '
                        'FROM currentstate curr '
                        'JOIN sessions sess ON curr.sessions_id = sess.id '
                        'JOIN stations sta ON sess.stations_id_occupied = sta.id '
                        'WHERE curr.sessions_id = ?'
                    )
                    sessioninfo = database.read_from_database(sql, (sessions_id,))
                    if sessioninfo['success']:
                        sessionid =  sessions_id
                        # Because these data are being read directly from the database,
                        # they are presumed to be clean, and don't need to go through the
                        # normal setters.
                        tripod._occupied_point['n'] = sessioninfo['results'][0]['northing']
                        tripod._occupied_point['e'] = sessioninfo['results'][0]['easting']
                        tripod._occupied_point['z'] = sessioninfo['results'][0]['elevation']
                        tripod._instrument_height = sessioninfo['results'][0]['instrumentheight']
                        prism._offsets['vertical_distance'] = sessioninfo['results'][0]['vertical_distance']
                        prism._offsets['latitude_distance'] = sessioninfo['results'][0]['latitude_distance']
                        prism._offsets['longitude_distance'] = sessioninfo['results'][0]['longitude_distance']
                        prism._offsets['radial_distance'] = sessioninfo['results'][0]['radial_distance']
                        prism._offsets['tangent_distance'] = sessioninfo['results'][0]['tangent_distance']
# TODO: Replace the following exits with proper dictionary errors, so that the front end can display the error for the user to fix.
                    else:
                        exit(f'FATAL ERROR: An error occurred reading the ShootPoints database.')
                else:
                    # TODO: There is no active session, so prompt the user to start a new session.
                    print('There is no active surveying session.')
            else:
                exit(f'FATAL ERROR: An error occurred reading the ShootPoints database.')
        else:
            # TODO: No stations have been created (i.e., this is a new DB), so prompt the user to create the first station.
            # tripod.save_station()
            print('There are no stations in the database.')
    else:
        exit(f'FATAL ERROR: An error occurred reading the ShootPoints database.')


def _load_station(id: int) -> dict:
    """"This function returns the name and coordinates of the indicated station from the database."""
    errors = []
    sql = 'SELECT name, northing, easting, elevation FROM stations WHERE id = ?'
    query = database.read_from_database(sql, (id,))
    if query['success']:
        coords = query['results'][0]
        tripod.set_occupied_point(coords['northing'], coords['easting'], coords['elevation'])
    else:
        errors.append(f'A problem occurred reading station id {id} from the database.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        result['result'] = (coords['name'], coords['northing'], coords['easting'], coords['elevation'])
    return result


def _save_new_session(data: tuple) -> bool:
    """This function saves the surveying session information to the database."""
    global sessionid
    sql = (
        'INSERT INTO sessions '
        '(label, started, surveyor, stations_id_occupied, stations_id_backsight, azimuth, instrumentheight) '
        'VALUES(?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)'
    )
    if database.save_to_database(sql, data)['success']:
        sessionid = database.read_from_database('SELECT last_insert_rowid()', ())['results'][0]['last_insert_rowid()']
    else:
        sessionid = 0
    if not database.save_to_database('UPDATE currentstate SET sessions_id = ?', (sessionid,))['success']:
        sessionid = 0
    return bool(sessionid)


def start_surveying_session_with_backsight(label: str, surveyor: str, occupied_point_id: int, backsight_station_id: int, prism_height: int) -> dict:
    """This function starts a new surveying session with a backsight to a known point."""
    errors = []
    occupied_point_coordinates = _load_station(occupied_point_id)
    if occupied_point_coordinates['success']:
        occupied_name, occupied_northing, occupied_easting, occupied_elevation = occupied_point_coordinates['result']
    else:
        errors.extend(occupied_point_coordinates['errors'])
    backsight_station_coordinates = _load_station(backsight_station_id)
    if backsight_station_coordinates['success']:
        backsight_name, backsight_northing, backsight_easting, backsight_elevation = backsight_station_coordinates['result']
    else:
        errors.extend(backsight_station_coordinates['errors'])
    if occupied_point_id == backsight_station_id:
        errors.append(f'The Occupied Point and Backsight Station are the same (id = {occupied_point_id}).')
    if occupied_northing == backsight_northing and occupied_easting == backsight_easting:
        errors.append(f'The coordinates of the Occupied Point ({occupied_name}) and the Backsight Station ({backsight_name}) are the same.')
    if prism_height < 0:
        errors.append(f'An invalid prism height ({prism_height}m) was entered.')
    if not errors:
        azimuth = calculations.calculate_azimuth(
            (occupied_northing, occupied_easting),
            (backsight_northing, backsight_easting)
        )
        degrees, remainder = divmod(azimuth, 1)
        minutes, remainder = divmod(remainder * 60, 1)
        seconds = round(remainder * 60)
        setazimuth = total_station.set_azimuth(degrees, minutes, seconds)
        if setazimuth['success']:
            measurement = total_station.take_measurement()
            if measurement['success']:
                expected_distance = math.hypot(occupied_northing - backsight_northing, occupied_easting - backsight_easting)
                measured_distance = math.hypot(measurement['delta_n'], measurement['delta_e'])
                variance = abs(expected_distance - measured_distance) * 100
                limit = configs['BACKSIGHT ERROR']['limit']
                if variance >= limit:
                    errors.append(f'The measured distance between the Occupied Point and the Backsight Station ({variance}cm) exceeds the limit set in configs.ini ({limit}cm).')
                elev_diff_of_points = occupied_elevation - backsight_elevation
                delta_z_to_point = measurement['measurement']['delta_z'] - prism_height
                instrument_height = elev_diff_of_points + delta_z_to_point
                setinstrumentheight = tripod.set_instrument_height(instrument_height)
                if not setinstrumentheight['success']:
                    errors.extend(setinstrumentheight['errors'])
            else:
                errors.extend(measurement['errors'])
        else:
            errors.extend(setazimuth['errors'])
    if not errors:
        data = (
            label,
            surveyor,
            occupied_point_id,
            backsight_station_id,
            f'{degrees}° {minutes}\' {seconds}"',
            instrument_height,
        )
        if not _save_new_session(data):
            errors.append('A problem occurred while saving the new session to the database.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        result['result'] = f'Session {sessionid} started.'
    return result


def start_surveying_session_with_azimuth(label: str, surveyor: str, occupied_point_id: int, instrument_height: float, degrees: int, minutes: int, seconds: int) -> dict:
    """This function starts a new surveying session with an azimuth to a landmark."""
    # There is no backsight station in this setup, so set its ID to None.
    backsight_station_id = None
    global sessionid
    errors = []
    occupied_point_coordinates = _load_station(occupied_point_id)
    if not occupied_point_coordinates['success']:
        errors.extend(occupied_point_coordinates['errors'])
    setinstrumentheight = tripod.set_instrument_height(instrument_height)
    if not setinstrumentheight['success']:
        errors.extend(setinstrumentheight['errors'])
    setazimuth = total_station.set_azimuth(degrees, minutes, seconds)
    if not setazimuth['success']:
        errors.extend(setazimuth['errors'])
    if not errors:
        data = (
            label,
            surveyor,
            occupied_point_id,
            backsight_station_id,
            f'{degrees}° {minutes}\' {seconds}"',
            instrument_height,
        )
        if not _save_new_session(data):
            errors.append(f'A problem occurred while saving the new session to the database.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        result['result'] = f'Session {sessionid} started.'
    return result


def end_surveying_session() -> dict:
    """This function ends a surveying session."""
    global sessionid
    errors = []
    sql = "UPDATE sessions SET ended = CURRENT_TIMESTAMP WHERE id = ?"
    if not database.save_to_database(sql, (sessionid,))['success']:
        errors.append(f'An error occurred closing the session. Session {sessionid} is still active.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        sessionid = 0
        result['result'] = f'Session {sessionid} ended.'
    return result


def save_station(name: str, coordinatesystem: str, coordinates: dict) -> bool:
    """This function creates a new station record in the database with the given name and coordinates."""
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
            if not 0 <= northing <= 10000000:
                errors.append(f'Northing given ({northing}) is out of range (0–10000000m).')
        # Check that the given easting is valid.
        try:
            easting = float(coordinates['easting'])
        except KeyError:
            errors.append(f'Station easting not given.')
        except ValueError:
            errors.append(f"Non-numeric easting given ({coordinates['easting']}).")
        else:
            if not 100000 <= easting <= 999999:
                errors.append(f'Easting given ({easting}) is out of range (100000–999999m).')
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
                        latitude, longitude = calculations.convert_utm_to_latlon(northing, easting, utmzonenumber, utmzoneletter)
    elif coordinatesystem == 'Lat/Lon':
        # Check that the given latitude is valid.
        try:
            latitude = float(coordinates['latitude'])
        except KeyError:
            errors.append('Station latitude not given.')
        except ValueError:
            errors.append(f"Non-numeric latitude given ({coordinates['latitude']}).")
        else:
            if not 0 <= latitude <= 90:
                errors.append('Latitude given is out of range (0–90°).')
        # Check that the given longitude is valid.
        try:
            longitude = float(coordinates['longitude'])
        except KeyError:
            errors.append('Station longitude not given.')
        except ValueError:
            errors.append(f"Non-numeric latitude given ({coordinates['longitude']}).")
        else:
            if not -180 <= longitude <= 180:
                errors.append('Longitude given is out of range (-180–180°).')
        if not errors:
            northing, easting, utmzone = calculations.convert_latlon_to_utm(latitude, longitude)
    else:
        errors.append(f'Invalid coordinate system given ({coordinatesystem}) It should be one of Site, UTM, or Lat/Lon.')
    if not errors:
        sql = (
            f'INSERT INTO stations '
            f'(name, northing, easting, elevation, utmzone, latitude, longitude) '
            f'VALUES (?, ?, ?, ?, ?, ?, ?)'
        )
        newstation = (name, northing, easting, elevation, utmzone, latitude, longitude)
        if not database.save_to_database(sql, newstation)['success']:
            errors.append(f'Station ({name}) not saved to the database.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        result['result'] = f'Station {name} saved to the database.'
    return result


# The following need to happen every time that the program is run or restarted.
if not configs:
    _load_configs()

if not total_station:
    _load_total_station_model()

if not serialport:
    _initialize_serial_port()

if not sessionid:
    _load_session()
