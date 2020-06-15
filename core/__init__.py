"""This package controls all aspects of ShootPoints’ communications with the total station and processing and saving data."""
# TODO: De-complexify EVERYTHING by moving all state information to the database.
# TODO: Make sure that you always expect outcome['errors'] and outcome['results'] to be lists, and handle them correctly.
# TODO: Add testing to this application.
# TODO: Create a module in this package (surveying.py?) for taking shots and handling metadata.
# TODO: If the round trips to the DB cause too much latency or instability, consider saving certain values as global variables, maybe in their own module.
# TODO: Revisit the sub-modules' functions to make sure that existing session/station/etc. prerequisites are in place before proceeding.

import configparser
import shutil
import glob
import importlib
import serial
import math


from . import tripod
from . import prism
from . import calculations
from . import database as _database


configs = None
totalstation = None
serialport = None


def _load_configs_from_file() -> dict:
    """
    This function loads the configurations from the configs.ini file.
    If that file doesn't exist, it creates one from configs.ini.example.
    """
    global configs
    outcome = {'errors': [], 'results': []}
    configs = configparser.ConfigParser()
    try:
        with open('configs.ini', 'r') as f:
            pass
    except FileNotFoundError:
        shutil.copy('configs.ini.example', 'configs.ini')
    configs.read('configs.ini')
    if configs.sections():
        outcome['results'] = 'Configurations loaded successfully.'
    else:
        configs.read('configs.ini.example')
        with open('configs.ini', 'w') as f:
            configs.write(f)
        error = 'The config.ini file was not found, so one was created from the example file. Update your configs before proceeding.'
        outcome['errors'].append(error)
        _database._record_setup_error(error)
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}


def _load_total_station_model() -> dict:
    """This function loads the indicated total station."""
    global configs
    global totalstation
    outcome = {'errors': [], 'results': []}
    if configs['SERIAL']['port'] == 'demo':
        from .total_stations import demo as totalstation
        outcome['results'] = 'Demo total station loaded.'
    else:
        make = configs['TOTAL STATION']['make'].replace(' ', '_').lower()
        make = make.replace('-', '_').lower()
        model = configs['TOTAL STATION']['model'].replace(' ', '_').lower()
        model = model.replace('-', '_').lower()
        # All Topcon GTS-300 series total stations use the same communications protocols.
        if make == 'topcon' and model[:6] == 'gts_30':
            model = 'gts_300_series'
        try:
            totalstation = importlib.import_module(f'{__name__}.total_stations.{make}.{model}', package='core')
            outcome['results'] = f"{configs['TOTAL STATION']['make']} {configs['TOTAL STATION']['model']} total station loaded."
        except ModuleNotFoundError:
            error = f'File total_stations/{make}/{model}.py does not exist. Specify the correct total station make and model in configs.ini before proceeding.'
            outcome['errors'].append(error)
            _database._record_setup_error(error)
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}


def _load_serial_port() -> dict:
    """
    This function finds the appropriate serial port and initializes it
    with the communication parameters for the total station model.
    """
    global configs
    global serialport
    outcome = {'errors': [], 'results': []}
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
            outcome['errors'].append('No valid serial port found. Specify the correct serial port in configs.ini before proceeding.')
    else:  # Port is specified explicitly in configs.ini file.
        serialport = configs['SERIAL']['port']
    if configs['SERIAL']['port'] != 'demo' and not outcome['errors']:
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
            outcome['results'] = f'Serial port {serialport} opened.'
        except:
            outcome['errors'].append('Serial port {serialport} could not be opened. Check your serial adapter and cable connections before proceeding')
    for each in outcome['errors']:
        _database._record_setup_error(each)
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}


def load_application() -> dict:
    """This function runs the private loader funtions (above) and clears setup errors if they run cleanly."""
    outcome = {'errors': [], 'results': []}
    loaders = [_load_configs_from_file, _load_total_station_model, _load_serial_port]
    for each in loaders:
        loaderoutcome = each()
        if 'results' in loaderoutcome:
            outcome['results'].append(loaderoutcome['results'])
        elif 'errors' in each():
            outcome['errors'].extend(loaderoutcome['errors'])
    outcome['success'] = not outcome['errors']
    if outcome['success']:
        _database._clear_setup_errors()
    return {key: val for key, val in outcome.items() if type(val) != list or val}


print(load_application())


def _load_station_from_database(id: int) -> dict:
    """"This function returns the name and coordinates of the indicated station from the database."""
    outcome = {'errors': [], 'results': []}
    sql = 'SELECT name, northing, easting, elevation FROM stations WHERE id = ?'
    query = _database.read_from_database(sql, (id,))
    if query['success'] and 'results' in query:
        coords = query['results'][0]
        outcome['results'] = (coords['name'], coords['northing'], coords['easting'], coords['elevation'])
    else:
        outcome['errors'].append(f'Station id {id} was not found in the database.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}


def save_config_file(port: str='', make: str='', model: str='', limit: int=0) -> dict:
    """
    This function creates the configs.ini and sets its values. Any parameters not passed
    when this function is called will stay what they currently are in the config.ini file.
    """
    if port:
        configs['SERIAL']['port'] = port
    if make:
        configs['TOTAL STATION']['make'] = make
    if model:
        configs['TOTAL STATION']['model'] = model
    if limit:
        configs['BACKSIGHT ERROR']['limit'] = limit
    with open('configs.ini', 'w') as f:
        configs.write(f)
    outcome = load_application()
    if outcome['success']:
        outcome['results'] = 'Configurations saved and reloaded.'
    return outcome


def _save_new_session(data: tuple) -> int:
    """This function saves the surveying session information to the database."""
    sql = (
        'INSERT INTO sessions '
        '(label, started, surveyor, stations_id_occupied, stations_id_backsight, azimuth, instrumentheight) '
        'VALUES(?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)'
    )
    if _database.save_to_database(sql, data)['success']:
        sessionid = _database.read_from_database('SELECT last_insert_rowid()', ())['results'][0]['last_insert_rowid()']
    else:
        sessionid = 0
    return sessionid


def start_surveying_session_with_backsight(label: str, surveyor: str, occupied_point_id: int, backsight_station_id: int, prism_height: float) -> dict:
    """This function starts a new surveying session with a backsight to a known point."""
    global configs
    outcome = {'errors': [], 'results': []}
    end_surveying_session()  # End the current session, if it's still open.
    if occupied_point_id == backsight_station_id:
        outcome['errors'].append(f'The Occupied Point and Backsight Station are the same (id = {occupied_point_id}).')
    occupiedpointcoordinates = _load_station_from_database(occupied_point_id)
    if occupiedpointcoordinates['success']:
        occupied_name, occupied_northing, occupied_easting, occupied_elevation = occupiedpointcoordinates['results']
    else:
        outcome['errors'].extend(occupiedpointcoordinates['errors'])
    backsightstationcoordinates = _load_station_from_database(backsight_station_id)
    if backsightstationcoordinates['success']:
        backsight_name, backsight_northing, backsight_easting, backsight_elevation = backsightstationcoordinates['results']
    else:
        outcome['errors'].extend(backsightstationcoordinates['errors'])
    if occupied_northing == backsight_northing and occupied_easting == backsight_easting:
        outcome['errors'].append(f'The coordinates of the Occupied Point ({occupied_name}) and the Backsight Station ({backsight_name}) are the same.')
    if prism_height < 0:
        outcome['errors'].append(f'An invalid prism height ({prism_height}m) was entered.')
    if not outcome['errors']:
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
                    outcome['errors'].append(f'The measured distance between the Occupied Point and the Backsight Station ({variance}cm) exceeds the limit set in configs.ini ({limit}cm).')
                elev_diff_of_points = occupied_elevation - backsight_elevation
                delta_z_to_point = measurement['measurement']['delta_z'] - prism_height
                instrument_height = elev_diff_of_points + delta_z_to_point
                validateinstrumentheight = tripod.validate_instrument_height(instrument_height)
                if not validateinstrumentheight['success']:
                    outcome['errors'].extend(validateinstrumentheight['errors'])
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
        if _save_new_session(data):
            outcome['results'] = f'Session {sessionid} started.'
        else:
            outcome['errors'].append('A problem occurred while saving the new session to the database.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}


def start_surveying_session_with_azimuth(label: str, surveyor: str, occupied_point_id: int, instrument_height: float, degrees: int, minutes: int, seconds: int) -> dict:
    """This function starts a new surveying session with an azimuth to a landmark."""
    backsight_station_id = None  # There is no backsight station in this setup, so the database expects a NULL.
    outcome = {'errors': _database.get_setup_errors(), 'results': []}
    if not outcome['errors']:
        end_surveying_session()  # End the current session, if it's still open.
        occupiedpointcoordinates = _load_station_from_database(occupied_point_id)
        if not occupiedpointcoordinates['success']:
            outcome['errors'].extend(occupiedpointcoordinates['errors'])
        validinstrumentheight = tripod.validate_instrument_height(instrument_height)
        if not validinstrumentheight['success']:
            outcome['errors'].extend(validinstrumentheight['errors'])
        if not outcome['errors']:
            setazimuth = totalstation.set_azimuth(degrees, minutes, seconds)
            if setazimuth['success']:
                data = (
                    label,
                    surveyor,
                    occupied_point_id,
                    backsight_station_id,
                    f'{degrees}° {minutes}\' {seconds}"',
                    instrument_height,
                )
                sessionid = _save_new_session(data)
                if sessionid:
                    outcome['results'] = f'Session {sessionid} started.'
                else:
                    outcome['errors'].append(f'A problem occurred while saving the new session to the database.')
            else:
                outcome['errors'].extend(setazimuth['errors'])
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}


def end_surveying_session() -> dict:
    """This function ends a surveying session."""
    outcome = {'errors': [], 'results': []}
    sessionid = _database.get_current_session_id()
    if sessionid:
        sql = "UPDATE sessions SET ended = CURRENT_TIMESTAMP WHERE id = ?"
        if _database.save_to_database(sql, (sessionid,))['success']:
            outcome['results'] = f'Session {sessionid} ended.'
        else:
            outcome['errors'].append(f'An error occurred closing the session. Session {sessionid} is still active.')
    else:
        outcome['errors'].append('There is no currently active surveying session.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}


def save_station(name: str, coordinatesystem: str, coordinates: dict) -> bool:
    """This function creates a new station record in the database with the given name and coordinates."""
    outcome = {'errors': [], 'results': []}
    # Check that the given elevation is valid.
    try:
        elevation = float(coordinates['elevation'])
    except KeyError:
        outcome['errors'].append(f'Station elevation not given.')
    except ValueError:
        outcome['errors'].append(f'Non-numeric elevation given ({elevation}).')
    if coordinatesystem == 'Site' or coordinatesystem == 'UTM':
        # Check that the given northing is valid.
        try:
            northing = float(coordinates['northing'])
        except KeyError:
            outcome['errors'].append(f'Station northing not given.')
        except ValueError:
            outcome['errors'].append(f"Non-numeric northing given ({coordinates['northing']}).")
        else:
            if coordinatesystem == 'UTM' and not 0 <= northing <= 10000000:
                outcome['errors'].append(f'Northing given ({northing}) is out of range (0–10000000m).')
        # Check that the given easting is valid.
        try:
            easting = float(coordinates['easting'])
        except KeyError:
            outcome['errors'].append(f'Station easting not given.')
        except ValueError:
            outcome['errors'].append(f"Non-numeric easting given ({coordinates['easting']}).")
        else:
            if coordinatesystem == 'UTM' and not 100000 <= easting <= 999999:
                outcome['errors'].append(f'Easting given ({easting}) is out of range (100000–999999m).')
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
                outcome['errors'].append(f'UTM Zone not given.')
            except ValueError:
                outcome['errors'].append(f'Non-numeric UTM Zone number given ({utmzonenumber}).')
            else:
                if not 1 <= utmzonenumber <= 60:
                    outcome['errors'].append(f'Invalid UTM Zone number given ({utmzonenumber}).')
                else:
                    utmzoneletter = utmzone[-1]
                    if utmzoneletter not in 'CDEFGHJKLMNPQRSTUVWX':
                        outcome['errors'].append(f'Invalid UTM Zone letter given ({utmzoneletter}).')
                    else:
                        latitude, longitude = calculations.convert_utm_to_latlon(northing, easting, utmzonenumber, utmzoneletter)
    elif coordinatesystem == 'Lat/Lon':
        # Check that the given latitude is valid.
        try:
            latitude = float(coordinates['latitude'])
        except KeyError:
            outcome['errors'].append('Station latitude not given.')
        except ValueError:
            outcome['errors'].append(f"Non-numeric latitude given ({coordinates['latitude']}).")
        else:
            if not 0 <= latitude <= 90:
                outcome['errors'].append('Latitude given is out of range (0–90°).')
        # Check that the given longitude is valid.
        try:
            longitude = float(coordinates['longitude'])
        except KeyError:
            outcome['errors'].append('Station longitude not given.')
        except ValueError:
            outcome['errors'].append(f"Non-numeric latitude given ({coordinates['longitude']}).")
        else:
            if not -180 <= longitude <= 180:
                outcome['errors'].append('Longitude given is out of range (-180–180°).')
        if not outcome['errors']:
            northing, easting, utmzone = calculations.convert_latlon_to_utm(latitude, longitude)
    else:
        outcome['errors'].append(f'Invalid coordinate system given ({coordinatesystem}) It should be one of Site, UTM, or Lat/Lon.')
    if not outcome['errors']:
        sql = (
            f'INSERT INTO stations '
            f'(name, northing, easting, elevation, utmzone, latitude, longitude) '
            f'VALUES (?, ?, ?, ?, ?, ?, ?)'
        )
        newstation = (name, northing, easting, elevation, utmzone, latitude, longitude)
        if _database.save_to_database(sql, newstation)['success']:
            outcome['results'] = f'Station {name} saved to the database.'
        else:
            outcome['errors'].append(f'Station ({name}) could not be saved to the database.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}


def summarize_application_state() -> dict:
    """
    This function returns the state of the global variables and
    summary data from the ShootPoints database.
    """
    global configs
    global totalstation
    global serialport
    summary = {
        'setup_errors': None,
        'serial_port': 'N/A',
        'total_station': 'N/A',
        'num_stations_in_db': _database.read_from_database('SELECT count(*) FROM stations')['results'][0]['count(*)'],
        'num_sessions_in_db': _database.read_from_database('SELECT count(*) FROM sessions')['results'][0]['count(*)'],
        'current_session': {}, #id, occupied point, IH
        'prism_offsets': {},
        'num_points_in_db': 0,
        'num_points_in_current_session': 0,
    }
    setuperrors = _database.get_setup_errors()
    if setuperrors:
        summary['setup_errors'] = setuperrors
    if configs['SERIAL']['port'] == 'demo':
        summary['total_station'] = 'demo'
    elif serialport:
        summary['serial_port'] = configs['SERIAL']['port']
        if totalstation:
            summary['total_station'] = f"{configs['TOTAL STATION']['make']} {configs['TOTAL STATION']['model']}"
    sessionid = _database.get_current_session_id()
    sql = (
        'SELECT '
            'sess.id, '
            'sess.stations_id_occupied, '
            'sta.northing, '
            'sta.easting, '
            'sta.elevation, '
            'sess.instrumentheight '
        'FROM sessions sess '
        'JOIN stations sta ON sess.stations_id_occupied = sta.id '
        'WHERE sess.id = ?'
    )
    try:
        summary['current_session'] = _database.read_from_database(sql, (sessionid,))['results'][0]
        summary['prism_offsets'] = prism.get_prism_offsets(True)['results']
        summary['num_points_in_db'] = _database.read_from_database('SELECT count(*) FROM shots')['results'][0]['count(*)']
        summary['num_points_in_current_session'] = _database.read_from_database('SELECT count(*) FROM shots WHERE sessions_id = ?', (sessionid,))['results'][0]['count(*)']
        # TODO: Also, add in counts of groupings in db and session?
    except:
        pass
    return summary
