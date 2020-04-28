import configparser
import glob
import importlib
import serial

from . import station
from . import prism
from . import angle_math
from . import data




# TODO: initialized will reset whenever the flask instance is restarted or the app is opened in a new browser/window--in which case you'll have to re-load prism and station from the DB
initialized = False
# Load the configs.
configs = configparser.RawConfigParser()
configs.read('configs.ini')


# Initialize the serial port.
total_station = None
if configs['SERIAL']['port'] == 'demo':
    from .total_stations import demo as total_station
elif configs['SERIAL']['port'] == 'auto':
    if glob.glob('/dev/cu.ttyAMA*'):  # Linux with RS232 adapter
        PORT = glob.glob('/dev/cu.ttyAMA*')[0]
    elif glob.glob('/dev/ttyUSB*'):  # Linux with USB adapter
        PORT = glob.glob('/dev/cu.ttyUSB*')[0]
    elif glob.glob('/dev/cu.usbserial*'):  # Mac with USB adapter
        PORT = glob.glob('/dev/cu.usbserial*')[0]
    else:  # Serial port not found.
        exit('FATAL ERROR: No valid serial port found.')
else:  # Port is specified explicitly in configs.ini file.
    PORT = configs['SERIAL']['port']


if not total_station:
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
            port=PORT,
            baudrate=total_station.BAUDRATE,
            parity=total_station.PARITY,
            bytesize=total_station.BYTESIZE,
            stopbits=total_station.STOPBITS,
            timeout=total_station.TIMEOUT,
        )
        total_station.port = port
    except:
        exit(f'FATAL ERROR: Serial port {PORT} could not be opened.')


def start_surveying_session(setup_type: str, occupied_point: dict, **kwargs):
    global initialized
    station.set_occupied_point(occupied_point['n'], occupied_point['e'], occupied_point['z'])
    if setup_type == 'Backsight':
        # TODO: check that all the necessary data has been entered properly before proceeding
        prism_height = kwargs['prism_height']
        prism.set_prism_offset({'vertical_distance': prism_height, 'vertical_direction': 'Down'})
        azimuth = angle_math.calculate_azimuth(
            (occupied_point['n'], occupied_point['e']),
            (kwargs['backsight_n'], kwargs['backsight_e'])
        )
        degrees, remainder = divmod(azimuth, 1)
        minutes, remainder = divmod(remainder * 60, 1)
        seconds = round(remainder * 60)
        # TODO: abort if any of the next three commands fail
        total_station.set_mode_hr()
        total_station.set_azimuth(degrees, minutes, seconds)
        measurement = total_station.take_measurement()
        elev_diff_of_points = occupied_point['z'] - kwargs['backsight_z']
        delta_z_to_point = measurement['measurement']['delta_z'] - prism_height
        instrument_height = elev_diff_of_points + delta_z_to_point
        station.set_instrument_height(instrument_height)
    elif setup_type == 'Backsight':
        degrees = kwargs['azimuth_degrees']
        minutes = kwargs['azimuth_minutes']
        seconds = kwargs['azimuth_seconds']
        total_station.set_mode_hr()
        total_station.set_azimuth(degrees, minutes, seconds)
        # TODO: warn the surveyor to set the prism height before shooting points
    # TODO: if any of the above commincations fail, then catch the error and don't set initialized to True
    initialized = True


# Order of operations:
# 0. Enter data for at least one station.
# 1. Start surveying session.
# 2. Set "initialized" flag and save session info.
