"""This package controls all aspects of ShootPoints’ communications with the total station and processing and saving data."""

import configparser
import glob
import importlib
import serial

from . import tripod
from . import prism
from . import calculations
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
        occupied_northing = result['results'][0]['northing']
        occupied_easting = result['results'][0]['easting']
        occupied_elevation = result['results'][0]['elevation']
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
                    azimuth = calculations.calculate_azimuth(
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
                northing, easting, utmzone = calculations.convert_latlon_to_utm(latitude, longitude)
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

if not serialport:
    _initialize_serial_port()

if not total_station:
    _load_total_station_model()

if not sessionid:
    _load_session()
