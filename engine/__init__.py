"""This package controls all aspects of ShootPoints’ communications with the total station and processing and saving data."""
# TODO: Create a module in this package for taking shots and handling metadata.

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
totalstation = None
serialport = None
sessionid = None


def _load_configs_from_file() -> dict:
    """This function loads the configurations from the configs.ini file."""
    global configs
    errors = []
    try:
        configs = configparser.ConfigParser()
        configs.read('configs.ini')
    except:
            configs = None
            errors.append('The config.ini file was not found. Create one before proceeding.')
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
        database._record_setup_error(errors[0])
    else:
        outcome['results'] = 'Configurations loaded successfully.'
    return outcome


def _load_total_station_model():
    """This function loads the indicated total station."""
    global configs
    global totalstation
    errors = []
    if not totalstation:
        if configs['SERIAL']['port'] == 'demo':
            from .total_stations import demo as totalstation
        else:
            make = configs['TOTAL STATION']['make'].replace(' ', '_').lower()
            make = make.replace('-', '_').lower()
            model = configs['TOTAL STATION']['model'].replace(' ', '_').lower()
            model = model.replace('-', '_').lower()
            if make == 'topcon' and model[:6] == 'gts_30':
                model = 'gts_300_series'
            try:
                totalstation = importlib.import_module(f'{__name__}.total_stations.{make}.{model}', package='engine')
            except ModuleNotFoundError:
                errors.append(f'File total_stations/{make}/{model}.py does not exist. Specify the correct total station make and model in configs.ini before proceeding.')
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
        database._record_setup_error(errors[0])
    else:
        outcome['results'] = 'Total station loaded.'
    return outcome


def _initialize_serial_port():
    """
    This function finds the appropriate serial port and initializes it
    with the communication parameters for the total station model.
    """
    global configs
    global serialport
    errors = []
    if not serialport:
        if configs['SERIAL']['port'] == 'demo':
            pass
        elif configs['SERIAL']['port'] == 'auto':
            if glob.glob('/dev/cu.ttyAMA*'):  # Linux with RS232 adapter
                serialport = glob.glob('/dev/cu.ttyAMA*')[0]
            elif glob.glob('/dev/ttyUSB*'):  # Linux with USB adapter
                serialport = glob.glob('/dev/cu.ttyUSB*')[0]
            elif glob.glob('/dev/cu.usbserial*'):  # Mac with USB adapter
                serialport = glob.glob('/dev/cu.usbserial*')[0]
            else:  # Serial port not found.
                errors.append('FATAL ERROR: No valid serial port found.')
        else:  # Port is specified explicitly in configs.ini file.
            serialport = configs['SERIAL']['port']
        if configs['SERIAL']['port'] != 'demo' and not errors:
            try:
                port = serial.Serial(
                    port=serialport,
                    baudrate=totalstation.BAUDRATE,
                    parity=totalstation.PARITY,
                    bytesize=totalstation.BYTESIZE,
                    stopbits=totalstation.STOPBITS,
                    timeout=totalstation.TIMEOUT,
                )
                totalstation.port = port
            except:
                errors.append(f'FATAL ERROR: Serial port {serialport} could not be opened.')
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
        database._record_setup_error(errors[0])
    else:
        outcome['results'] = f'Serial port {serialport} opened.'
    return outcome


def _load_session_from_database() -> dict:
    """
    This function loads the active surveying session from the database, prompting 
    the surveyor to start a new session or create a new station record if necessary.
    """
    global sessionid
    errors = []
    sql = "SELECT id FROM sessions WHERE ended IS NULL ORDER BY started DESC LIMIT 1"
    currentsession = database.read_from_database(sql)
    if currentsession['success']:
        if len(currentsession['results']) > 0:
            sessionid = currentsession['results'][0]['id']
            if database.update_current_state({'sessions_id': sessionid})['success']:
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
                sessioninfo = database.read_from_database(sql, (sessionid,))
                if sessioninfo['success']:
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
                else:
                    errors.append('FATAL ERROR: Because of problems reading the ShootPoints database, we could not retrieve any session information.')
            else:
                errors.append('FATAL ERROR: Because of problems writing to the ShootPoints database, the current session could not be saved.')
        else:
            sessioninfo = 'There is no active surveying session.'
    else:
        errors.append('FATAL ERROR: Because of problems reading the ShootPoints database, we could not determine the current session id.')
    if not errors:
        sql = "SELECT count(*) AS numstations FROM stations"
        numstations = database.read_from_database(sql)
        if numstations['success']:
            if numstations['results'][0]['numstations'] == 0:
                errors.append('There are no stations in the database. Please enter at least one before proceeding.')
        else:
            errors.append('FATAL ERROR: Because of problems reading the ShootPoints database, we could not determine the number of previously saved stations.')
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
        database._record_setup_error(errors[0])
        sessionid = 0
    else:
        outcome['results'] = sessioninfo
    return outcome


def _load_application_state() -> dict:
    """
    This function checks the state of the global variables, and reloads them from
    the ShootPoints database, if necessary.
    """
    errors = []
    loadconfigs = _load_configs_from_file()
    if not loadconfigs['success']:
        errors.extend(loadconfigs['errors'])
    else:
        loadtotalstation = _load_total_station_model()
        if not loadtotalstation['success']:
            errors.extend(loadtotalstation['errors'])
        initializeserialport = _initialize_serial_port()
        if not initializeserialport['success']:
            errors.extend(initializeserialport['errors'])
        if not errors:
            loadsession = _load_session_from_database()
            if not loadsession['success']:
                errors.extend(loadsession['errors'])
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        outcome['results'] = 'Configs and state loaded successfully.'
        database._clear_setup_errors()
    return outcome


def _load_station_from_database(id: int) -> dict:
    """"This function returns the name and coordinates of the indicated station from the database."""
    errors = []
    sql = 'SELECT name, northing, easting, elevation FROM stations WHERE id = ?'
    query = database.read_from_database(sql, (id,))
    if query['success']:
        if len(query['results']):
            coords = query['results'][0]
            tripod.set_occupied_point(coords['northing'], coords['easting'], coords['elevation'])
        else:
            errors.append('There are no saved stations in the database.')
    else:
        errors.append(f'A problem occurred reading station id {id} from the database.')
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        outcome['results'] = (coords['name'], coords['northing'], coords['easting'], coords['elevation'])
    return outcome


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


def save_config_file(port: str='', make: str='', model: str='', limit: int=0) -> dict:
    """This function creates the configs.ini and sets its values."""
    configs = configparser.ConfigParser()
    # If any of the parameters aren't set when this function is called, then defaul to those in the example file.
    configs.read('configs.ini.example')
    if port:
        configs['SERIAL'] = {'port': port}
    if make:
        configs['TOTAL STATION'] = {'make': make}
    if model:
        configs['TOTAL STATION'] = {'model': model}
    if limit:
        configs['BACKSIGHT ERROR'] = {'limit': limit}
    with open('configs.ini', 'w') as f:
        configs.write(f)
    outcome = {
        'success': True,
        'results': 'Configurations saved. Be sure to re-load the application state.'
    }
    return outcome


def start_surveying_session_with_backsight(label: str, surveyor: str, occupied_point_id: int, backsight_station_id: int, prism_height: float) -> dict:
    """This function starts a new surveying session with a backsight to a known point."""
    global configs
    errors = []
    end_surveying_session()  # End the current session, if it's still open.
    occupied_point_coordinates = _load_station_from_database(occupied_point_id)
    if occupied_point_coordinates['success']:
        occupied_name, occupied_northing, occupied_easting, occupied_elevation = occupied_point_coordinates['results']
    else:
        errors.extend(occupied_point_coordinates['errors'])
    backsight_station_coordinates = _load_station_from_database(backsight_station_id)
    if backsight_station_coordinates['success']:
        backsight_name, backsight_northing, backsight_easting, backsight_elevation = backsight_station_coordinates['results']
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
        setazimuth = totalstation.set_azimuth(degrees, minutes, seconds)
        if setazimuth['success']:
            measurement = totalstation.take_measurement()
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
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        outcome['results'] = f'Session {sessionid} started.'
    return outcome


def start_surveying_session_with_azimuth(label: str, surveyor: str, occupied_point_id: int, instrument_height: float, degrees: int, minutes: int, seconds: int) -> dict:
    """This function starts a new surveying session with an azimuth to a landmark."""
    backsight_station_id = None  # There is no backsight station in this setup, so the database expects a NULL.
    global sessionid
    errors = []
    end_surveying_session()  # End the current session, if it's still open.
    occupied_point_coordinates = _load_station_from_database(occupied_point_id)
    if not occupied_point_coordinates['success']:
        errors.extend(occupied_point_coordinates['errors'])
    setinstrumentheight = tripod.set_instrument_height(instrument_height)
    if not setinstrumentheight['success']:
        errors.extend(setinstrumentheight['errors'])
    setazimuth = totalstation.set_azimuth(degrees, minutes, seconds)
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
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        outcome['results'] = f'Session {sessionid} started.'
    return outcome


def end_surveying_session() -> dict:
    """This function ends a surveying session."""
    global sessionid
    errors = []
    sql = "UPDATE sessions SET ended = CURRENT_TIMESTAMP WHERE id = ?"
    if not database.save_to_database(sql, (sessionid,))['success']:
        errors.append(f'An error occurred closing the session. Session {sessionid} is still active.')
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        sessionid = 0
        outcome['results'] = f'Session {sessionid} ended.'
    return outcome


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
            if coordinatesystem != 'Site' and not 0 <= northing <= 10000000:
                errors.append(f'Northing given ({northing}) is out of range (0–10000000m).')
        # Check that the given easting is valid.
        try:
            easting = float(coordinates['easting'])
        except KeyError:
            errors.append(f'Station easting not given.')
        except ValueError:
            errors.append(f"Non-numeric easting given ({coordinates['easting']}).")
        else:
            if coordinatesystem != 'Site' and not 100000 <= easting <= 999999:
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
    outcome = {'success': not errors}
    if errors:
        outcome['errors'] = errors
    else:
        outcome['results'] = f'Station {name} saved to the database.'
    return outcome


def summarize_application_state() -> dict:
    """
    This function checks the state of the global variables, and reloads them from
    the ShootPoints database, if necessary.
    """
    global configs
    global totalstation
    global serialport
    global sessionid
    summary = {
        'valid_config': False,
        'serial_port': 'N/A',
        'total_station': 'N/A',
        'num_stations_in_db': 0,
        'num_sessions_in_db': 0,
        'current_session': {}, #id, occupied point, IH, POs...
        'num_points_in_db': 0,
        'num_points_in_current_session': 0,
    }
    _load_application_state()
    if _load_configs_from_file()['success']:
        summary['valid_config'] = True
        if serialport:
            summary['serial_port'] = serialport
        if configs['SERIAL']['port'] == 'demo':
            summary['total_station'] = 'demo'
        elif totalstation:
            summary['total_station'] = f"{configs['TOTAL STATION']['make']} {configs['TOTAL STATION']['model']}"
        summary['num_stations_in_db'] = database.read_from_database('SELECT count(*) FROM stations')['results'][0]['count(*)']
        summary['num_sessions_in_db'] = database.read_from_database('SELECT count(*) FROM sessions')['results'][0]['count(*)']
        if sessionid:
            # TODO: Get some of the following with the getters, instead of just from the DB, for increased readability.
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
            summary['current_session'] = database.read_from_database(sql, (sessionid,))['results'][0]
        summary['num_points_in_db'] = database.read_from_database('SELECT count(*) FROM shots')['results'][0]['count(*)']
        summary['num_points_in_current_session'] = database.read_from_database('SELECT count(*) FROM shots WHERE sessions_id = ?', (sessionid,))['results'][0]['count(*)']
    return summary
