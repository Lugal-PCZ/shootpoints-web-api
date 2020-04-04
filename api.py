from flask import Flask, request, jsonify
import json

from . import engine

app = Flask(__name__)

@app.route('/')
def index():
    routes = [
        f'{request.url}mode_hr/',  # POST
        f'{request.url}azimuth/',  # POST
        f'{request.url}measurement/',  # GET
        f'{request.url}occupied_point/',  # GET, POST
        f'{request.url}instrument_height/',  # GET, POST
        f'{request.url}prism_offset/',  # GET, POST
    ]
    return jsonify(routes)


# Set the total station to horizontal right mode.
@app.route('/mode_hr/', methods=['POST'])
def mode_hr():
    result = engine.total_station.set_mode_hr()
    return jsonify(result)


# Set the azimuth on the total station.
@app.route('/azimuth/', methods=['POST'])
def azimuth():
    degrees = request.args.get('degrees', 0)
    minutes = request.args.get('minutes', 0)
    seconds = request.args.get('seconds', 0)
    return f'{degrees}.{minutes}{seconds}'


# Tell the total station to start measuring a point.
@app.route('/measurement/', methods=['GET'])
def measurement():
    result = engine.total_station.take_measurement()
    return jsonify(result)


# Get or set the coordinates of the occupied point.
@app.route('/occupied_point/', methods=['GET', 'POST'])
def occupied_point():
    if request.method == 'POST':
        engine.station.occupied_point ['n'] = request.form['n']
        engine.station.occupied_point ['e'] = request.form['e']
        engine.station.occupied_point ['z'] = request.form['z']
    return jsonify(engine.station.occupied_point)


# Get or set the instrument height above the occupied point.
@app.route('/instrument_height/', methods=['GET', 'POST'])
def instrument_height():
    if request.method == 'POST':
        engine.station.instrument_height = request.form['h']
    return jsonify(engine.station.instrument_height)


# Get or set the prism offset.
@app.route('/prism_offset/', methods=['GET', 'POST'])
def prism_offset():
    if request.method == 'POST':
        pass
    return jsonify(engine.prism.offset)
