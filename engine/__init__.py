"""This package controls all aspects of ShootPoints’ communications with the total station and processing and saving data."""

import configparser
import glob
import importlib
import serial

from . import tripod
from . import prism
from . import angle_math
from . import database


configs = None
def _load_configs():
    """This function loads the configurations from the configs.ini file."""
    global configs
    configs = configparser.RawConfigParser()
    configfile = 'configs.ini'
    try:
        configs.read(configfile)
    except:
        exit(f'FATAL ERROR: The config file ({configfile}) was not found.')


serialport = None
def _initialize_serial_port():
    """This function finds the name of the serial port."""
    global serialport
    if configs['SERIAL']['port'] == 'demo':
        from .total_stations import demo as total_station
    elif configs['SERIAL']['port'] == 'auto':
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


total_station = None
def _load_total_station_model():
    """This function loads the given total station and opens the serial port."""
    global total_station
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


sessionid = None
def _load_session():
    """
    This function loads the active surveying session from the database, prompting 
    the surveyor to start a new session or create a new station record if necessary.
    """
    global sessionid
    sql = "SELECT * FROM stations"
    result = database.read_from_database(sql)
    if result['success']:
        if result['results']:
            sql = "SELECT id FROM sessions WHERE ended IS NULL ORDER BY started DESC LIMIT 1"
            result = database.read_from_database(sql)
            if result['success']:
                if result['results']:
                    sessions_id = result['results'][0]['id']
                    sql = (
                        "SELECT\n"
                        "   curr.sessions_id,\n"
                        "   sess.stations_id_occupied,\n"
                        "   sta.northing,\n"
                        "   sta.easting,\n"
                        "   sta.elevation,\n"
                        "   sess.instrumentheight,\n"
                        "   curr.prism_vertical_distance,\n"
                        "   curr.prism_latitude_distance,\n"
                        "   curr.prism_longitude_distance,\n"
                        "   curr.prism_radial_distance,\n"
                        "   curr.prism_tangent_distance\n"
                        "FROM currentstate curr\n"
                        "JOIN sessions sess ON curr.sessions_id = sess.id\n"
                        "JOIN stations sta ON sess.stations_id_occupied = sta.id\n"
                        f"WHERE curr.sessions_id = {sessions_id}"
                    )
                    result = database.read_from_database(sql)
                    if result['success']:
                        sessionid =  sessions_id
                        # Because these data are being read directly from the database,
                        # they are presumed to be clean, and don't need to go through the
                        # normal setters.
                        tripod._occupied_point['n'] = result['results'][0]['northing']
                        tripod._occupied_point['e'] = result['results'][0]['easting']
                        tripod._occupied_point['z'] = result['results'][0]['elevation']
                        tripod._instrument_height = result['results'][0]['instrumentheight']
                        prism._offsets['vertical_distance'] = result['results'][0]['prism_vertical_distance']
                        prism._offsets['latitude_distance'] = result['results'][0]['prism_latitude_distance']
                        prism._offsets['longitude_distance'] = result['results'][0]['prism_longitude_distance']
                        prism._offsets['radial_distance'] = result['results'][0]['prism_radial_distance']
                        prism._offsets['tangent_distance'] = result['results'][0]['prism_tangent_distance']
                    else:
                        exit(f'FATAL ERROR: An error occurred reading the ShootPoints database.')
                else:
                    # TODO: There is no active session, so prompt the user to start a new session.
                    # start_surveying_session()
                    pass
            else:
                exit(f'FATAL ERROR: An error occurred reading the ShootPoints database.')
        else:
            # TODO: No stations have been created (i.e., this is a new DB), so prompt the user to create the first station.
            # tripod.save_station()
            pass
    else:
        exit(f'FATAL ERROR: An error occurred reading the ShootPoints database.')


def start_surveying_session(label: str, surveyor: str, occupied_point: int, backsight_station: int=0, instrument_height: float=0, prism_height: int=0, azimuth: dict={}) -> dict:
    """This function starts a new surveying session and saves it to the database."""
    global sessionid
    errors = []
    sql = f"SELECT northing, easting, elevation FROM stations WHERE id = ?"
    result = database.read_from_database(sql, (occupied_point,))
    if result['success']:
        occupied_northing = result['results']['northing']
        occupied_easting = result['results']['easting']
        occupied_elevation = result['results']['elevation']
        tripod.set_occupied_point(occupied_northing, occupied_easting, occupied_elevation)
        if backsight_station:
            # Azimuth and instrument height are being set up with a backsight shot.
            sql = f"SELECT northing, easting, elevation FROM stations WHERE id = ?"
            result = database.read_from_database(sql, (backsight_station,))
            if result['success']:
                if prism_height > 0:
                    prism.set_prism_offset(**{'vertical_distance': prism_height, 'vertical_direction': 'Down'})
                    backsight_northing = result['results']['northing']
                    backsight_easting = result['results']['easting']
                    backsight_elevation = result['results']['elevation']
                    azimuth = angle_math.calculate_azimuth(
                        (occupied_northing, occupied_easting),
                        (backsight_northing, backsight_easting)
                    )
                    degrees, remainder = divmod(azimuth, 1)
                    minutes, remainder = divmod(remainder * 60, 1)
                    seconds = round(remainder * 60)
                    setazimuth = total_station.set_azimuth(degrees, minutes, seconds)
                    if result['success']:
                        measurement = total_station.take_measurement()
                        if measurement['success']:
                            elev_diff_of_points = occupied_elevation - backsight_elevation
                            delta_z_to_point = measurement['measurement']['delta_z'] - prism_height
                            instrument_height = elev_diff_of_points + delta_z_to_point
                            tripod.set_instrument_height(instrument_height)
                        else:
                            errors.extend(measurement['errors'])
                    else:
                        errors.extend(setazimuth['errors'])
                else:
                    errors.append(f'An invalid prism height ({prism_height}m) was entered.')
            else:
                errors.extend(result['errors'])
        else:
            # Azimuth and instrument height are being set manually.
            setinstrumentheight = tripod.set_instrument_height(instrument_height)
            if setinstrumentheight['success']:
                degrees = azimuth['degrees']
                minutes = azimuth['minutes']
                seconds = azimuth['seconds']
                setazimuth = total_station.set_azimuth(degrees, minutes, seconds)
                if not setazimuth['success']:
                    errors.extend(setazimuth['errors'])
            else:
                errors.extend(setinstrumentheight['errors'])
    else:
        errors.append(f'A problem occurred reading station id {occupied_point} from the database.')
    if not errors:
        if not backsight_station:
            backsight_station = None
        sql = (
            "INSERT INTO sessions SET\n"
            "   label=?,\n"
            "   started=CURRENT_TIMESTAMP,\n"
            "   surveyor=?,\n"
            "   stations_id_occupied=?,\n"
            "   stations_id_backsight=?,\n"
            "   azimuth=?,\n"
            "   instrumentheight=?\n"
        )
        sessiondata = (
            label,
            surveyor,
            occupied_point,
            backsight_station,
            f'{degrees}° {minutes}\' {seconds}"',
            instrument_height,
        )
        if database.save_to_database(sql, sessiondata)['success']:
            sessionid = database.read_from_database("SELECT last_insert_rowid()", ())['results'][0]['last_insert_rowid()']
        else:
            errors.append(f'A problem occurred while saving the new session to the database.')
    result = {'success': not errors}
    if errors:
        result['errors'] = errors
    else:
        sessionid = 0
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


# The following need to happen every time that the program is run or restarted.
if not configs:
    _load_configs()

if not serialport:
    _initialize_serial_port()

if not total_station:
    _load_total_station_model()

if not sessionid:
    _load_session()
