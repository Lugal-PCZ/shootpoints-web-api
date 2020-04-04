from flask import Flask, request, jsonify
import json

from . import engine

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    actions = [
        {
            'description': 'Set the total station to horizontal right mode.',
            'route': '/mode_hr/set/',
        },
        {
            'description': 'Set the azimuth on the total station.',
            'route': '/azimuth/set/',
        },
        {
            'description': 'Tell the total station to start measuring a point.',
            'route': '/measurement/get/',
        },
        {
            'description': 'Get the prism offset.',
            'route': '/prism/get/',
        },
        {
            'description': 'Set the prism offset.',
            'route': '/prism/set/',
        },
        {
            'description': 'Get the coordinates of the occupied point.',
            'route': '/occupied_point/get/',
        },
        {
            'description': 'Set the coordinates of the occupied point.',
            'route': '/occupied_point/set/',
        },
    ]
    for each in actions:
        each['url'] = f'{request.url}{each["route"][1:]}'
    return jsonify({'actions': actions})


@app.route('/mode_hr/set/', methods=['POST'])
def set_mode_hr():
    result = engine.total_station.set_mode_hr()
    return jsonify(result)


@app.route('/azimuth/set/', methods=['POST'])
def set_azimuth():
    degrees = request.args.get('degrees', 0)
    minutes = request.args.get('minutes', 0)
    seconds = request.args.get('seconds', 0)
    return f'{degrees}.{minutes}{seconds}'


@app.route('/measurement/get/', methods=['GET'])
def take_measurement():
    result = engine.total_station.take_measurement()
    return jsonify(result)


@app.route('/occupied_point/get/', methods=['GET'])
def get_occupied_point():
    result = engine.station.occupied_point
    return jsonify(result)


@app.route('/occupied_point/set/', methods=['POST'])
def set_occupied_point():
    try:
        engine.station.occupied_point ['n'] = request.form['n']
        engine.station.occupied_point ['e'] = request.form['e']
        engine.station.occupied_point ['z'] = request.form['z']
    except:
        pass
    return get_occupied_point()


@app.route('/prism/get/', methods=['GET'])
def get_prism_offset():
    result = engine.prism.offset
    return jsonify(result)


@app.route('/prism/set/', methods=['POST'])
def set_prism_offset():
    result = engine.prism.offset
    return jsonify(result)
