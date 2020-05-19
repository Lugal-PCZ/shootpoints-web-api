"""This module contains the API for ShootPoints."""

from fastapi import FastAPI, Response

import engine


app = FastAPI()


@app.get('/')
def show_summary():
    """This function gives summary data about the active """
    return engine.summarize_application_state()


@app.post('/azimuth/')
def azimuth_set(response: Response, degrees: int=0, minutes: int=0, seconds: int=0):
    """This function sets the azimuth on the total station."""
    result = engine.check_application_state()
    if result['success']:
        result = engine.total_station.set_azimuth(degrees, minutes, seconds)
    if 'errors' in result:
        response.status_code = 422
    return result


@app.post('/configs/')
def configs_set(response: Response, port: str='', make: str='', model: str='', limit: int=0):
    result = engine.create_config_file(port, make, model, limit)
    if 'errors' in result:
        response.status_code = 422
    return result


@app.get('/instrument_height/')
def instrument_height_get():
    """"This function gets the instrument height above the occupied point."""
    result = engine.tripod.get_instrument_height()
    return result


@app.post('/instrument_height/')
def instrument_height_set(response: Response, height: float):
    """"This function gets the instrument height above the occupied point."""
    result = engine.check_application_state()
    if result['success']:
        result = engine.tripod.set_instrument_height(height)
    if 'errors' in result:
        response.status_code = 422
    return result


@app.get('/cancel/')
def measurement_cancel():
    """This function stops a measurement in progress."""
    result = engine.total_station.cancel_measurement()
    return result


@app.get('/measurement/')
def measurement_take(response: Response):
    """This function tells the total station to start measuring a point."""
    result = engine.check_application_state()
    if result['success']:
        if engine.prism.get_prism_offset()['result']:
            result = engine.total_station.take_measurement()
        else:
            result = {'success': False, 'errors': ['Set a prism offset before proceeding.']}
        if 'errors' in result:
            response.status_code = 422
        else:
            result = engine.calculations.apply_offsets_to_measurement(result)
    return result


@app.post('/mode_hr/')
def mode_hr_set(response: Response):
    """This function sets the total station to horizontal right mode."""
    result = engine.check_application_state()
    if result['success']:
        result = engine.total_station.set_mode_hr()
    if 'errors' in result:
        response.status_code = 422
    return result


@app.get('/occupied_point/')
def occupied_point_get():
    """This function gets the coordinates of the occupied point."""
    result = engine.tripod.get_occupied_point()
    return result


@app.post('/occupied_point/')
def occupied_point_set(response: Response, northing: float, easting: float, elevation: float):
    """This function sets the coordinates of the occupied point."""
    result = engine.check_application_state()
    if result['success']:
        result = engine.tripod.set_occupied_point(northing, easting, elevation)
    if 'errors' in result:
        response.status_code = 422
    return result


@app.get('/prism_offset/')
def prism_offset_get():
    """This function gets the prism offsets."""
    result = engine.prism.get_prism_offset()
    return result


@app.post('/prism_offset/')
def prism_offset_set(response: Response, offsets: dict):
    """This function sets the prism offsets."""
    result = engine.check_application_state()
    if result['success']:
        result = engine.prism.set_prism_offset(**offsets)
    if 'errors' in result:
        response.status_code = 422
    return result


@app.post('/session/')
def session_start(response: Response, label: str, surveyor: str, occupied_point_id: int, backsight_station_id: int=0, instrument_height: float=0.0, prism_height: float=0.0, degrees: int=0, minutes: int=0, seconds: int=0):
    """This funciton starts a new surveying session."""
    result = engine.check_application_state()
    if result['success']:
        if backsight_station_id:
            result = engine.start_surveying_session_with_backsight(
                label,
                surveyor,
                occupied_point_id,
                backsight_station_id,
                prism_height,
            )
        else:
            result = engine.start_surveying_session_with_azimuth(
                label,
                surveyor,
                occupied_point_id,
                instrument_height,
                degrees,
                minutes,
                seconds,
            )
    if 'errors' in result:
        response.status_code = 422
    return result
