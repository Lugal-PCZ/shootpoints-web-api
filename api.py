"""This module contains the API for ShootPoints."""

from fastapi import FastAPI, Response

import engine


app = FastAPI()


@app.post('/azimuth/')
def azimuth_set(response: Response, degrees: int=0, minutes: int=0, seconds: int=0):
    """Sets the azimuth on the total station."""
    result = engine.total_station.set_azimuth(degrees, minutes, seconds)
    if 'errors' in result:
        response.status_code = 422
    return result


@app.get('/instrument_height/')
def instrument_height_get():
    """"Gets the instrument height above the occupied point."""
    result = engine.tripod.get_instrument_height()
    return result


@app.post('/instrument_height/')
def instrument_height_set(response: Response, height: float):
    """"Gets the instrument height above the occupied point."""
    result = engine.tripod.set_instrument_height(height)
    if 'errors' in result:
        response.status_code = 422
    return result


@app.get('/cancel/')
def measurement_cancel():
    """Stops a measurement in progress."""
    result = engine.total_station.cancel_measurement()
    return result


@app.get('/measurement/')
def measurement_take(response: Response):
    """Tells the total station to start measuring a point."""
    # TODO: warn the user if prism offsets are all zero
    result = engine.total_station.take_measurement()
    if 'errors' in result:
        response.status_code = 422
    else:
        result = engine.data.apply_offsets_to_measurement(result)
    return result


@app.post('/mode_hr/')
def mode_hr_set(response: Response):
    """Sets the total station to horizontal right mode."""
    result = engine.total_station.set_mode_hr()
    if 'errors' in result:
        response.status_code = 422
    return result


@app.get('/occupied_point/')
def occupied_point_get():
    """Gets the coordinates of the occupied point."""
    result = engine.tripod.get_occupied_point()
    return result


@app.post('/occupied_point/')
def occupied_point_set(response: Response, northing: float, easting: float, elevation: float):
    """Sets the coordinates of the occupied point."""
    result = engine.tripod.set_occupied_point(northing, easting, elevation)
    if 'errors' in result:
        response.status_code = 422
    return result


@app.get('/prism_offset/')
def prism_offset_get():
    """Gets the prism offsets."""
    result = engine.prism.get_prism_offset()
    return result


@app.post('/prism_offset/')
def prism_offset_set(response: Response, offsets: dict):
    """Sets the prism offsets."""
    result = engine.prism.set_prism_offset(**offsets)
    if 'errors' in result:
        response.status_code = 422
    return result


@app.post('/session/')
def session_start(response: Response, label: str, surveyor: str, occupied_point: int, backsight_station: int=0, instrument_height: float=0, prism_height: int=0, azimuth: dict={}):
    """Starts a new surveying session."""
    result = engine.start_surveying_session(
        label,
        surveyor,
        occupied_point,
        backsight_station,
        instrument_height,
        prism_height,
        azimuth,
    )
    if 'errors' in result:
        response.status_code = 422
    return result
