from flask import Flask, request, jsonify
import json

from . import engine

app = Flask(__name__)

@app.route('/')
def index():
    options = [
        'set_mode_hr',
        'set_azimuth',
        'take_measurement',
    ]
    return jsonify({'options': options})


@app.route('/set_mode_hr/')
def set_mode_hr():
    result = engine.total_station.set_mode_hr()
    return jsonify(result)


@app.route('/set_azimuth/')
def set_azimuth():
    degrees = request.args.get('d', 0)
    minutes = request.args.get('m', 0)
    seconds = request.args.get('s', 0)
    return f'{degrees}.{minutes}{seconds}'


@app.route('/take_measurement/')
def take_measurement():
    result = engine.total_station.take_measurement()
    return jsonify(result)


# @app.route('/list/<int:listid>')
# def get_list(listid):
#     # return json.dumps(_on_api_connection().get_list(listid))
#     pass
