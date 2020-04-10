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
@app.route('/azimuth/', methods=['GET'])
def azimuth():
    degrees = request.form.get('degrees', 0)
    minutes = request.form.get('minutes', 0)
    seconds = request.form.get('seconds', 0)
    result = engine.total_station.set_azimuth(degrees, minutes, seconds)
    return result


# Tell the total station to start measuring a point.
@app.route('/measurement/', methods=['GET'])
def measurement():
    result = engine.total_station.take_measurement()
    return jsonify(result)


# Get or set the coordinates of the occupied point.
@app.route('/occupied_point/', methods=['GET', 'POST'])
def occupied_point():
    if request.method == 'GET':
        result = engine.station.get_occupied_point()
    elif request.method == 'POST':
        northing = request.form.get('northing')
        easting = request.form.get('easting')
        elevation = request.form.get('elevation')
        result = engine.station.set_occupied_point(northing, easting, elevation)
    return jsonify(result)


# Get or set the instrument height above the occupied point.
@app.route('/instrument_height/', methods=['GET', 'POST'])
def instrument_height():
    if request.method == 'GET':
        result = engine.station.get_instrument_height()
    elif request.method == 'POST':
        height = request.form.get('height')
        result = engine.station.set_instrument_height(height)
    return jsonify(result)


# Get or set the prism offset.
@app.route('/prism_offset/', methods=['GET', 'POST'])
def prism_offset():
    if request.method == 'GET':
        result = engine.prism.get_prism_offset()
    elif request.method == 'POST':
        args = dict(request.form)
        result = engine.prism.set_prism_offset(**args)
    return result
