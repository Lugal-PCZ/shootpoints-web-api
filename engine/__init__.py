import configparser
import glob
import importlib
import serial

from . import station
from . import prism
from . import angle_math
from . import data


# Load the configs.
config = configparser.RawConfigParser()
config.read('config.ini')


# Initialize the serial port.
total_station = None
if config['SERIAL']['port'] == 'demo':
    from .total_stations import demo as total_station
elif config['SERIAL']['port'] == 'auto':
    if glob.glob('/dev/cu.ttyAMA*'):  # Linux with RS232 adapter
        PORT = glob.glob('/dev/cu.ttyAMA*')[0]
    elif glob.glob('/dev/ttyUSB*'):  # Linux with USB adapter
        PORT = glob.glob('/dev/cu.ttyUSB*')[0]
    elif glob.glob('/dev/cu.usbserial*'):  # Mac with USB adapter
        PORT = glob.glob('/dev/cu.usbserial*')[0]
    else:  # Serial port not found.
        exit('FATAL ERROR: No valid serial port found.')
else:  # Port is specified explicitly in config.ini file.
    PORT = config['SERIAL']['port']

if not total_station:
    make = config['TOTAL STATION']['make'].replace(' ', '_').lower()
    make = config['TOTAL STATION']['make'].replace('-', '_').lower()
    model = config['TOTAL STATION']['model'].replace(' ', '_').lower()
    model = config['TOTAL STATION']['model'].replace('-', '_').lower()
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
