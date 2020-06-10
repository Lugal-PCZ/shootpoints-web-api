"""This module contains the API for ShootPoints."""

from fastapi import FastAPI, Response

import engine


state = engine._load_application_state()

app = FastAPI()


@app.get('/')
def show_summary():
    """This function gives summary data about the active """
    return engine.summarize_application_state()


@app.post('/azimuth/')
def azimuth_set(response: Response, degrees: int=0, minutes: int=0, seconds: int=0):
    """This function sets the azimuth on the total station."""
    try:
        outcome = engine.totalstation.set_azimuth(degrees, minutes, seconds)
        if 'errors' in outcome:
            response.status_code = 422
    except:
        outcome = state
        response.status_code = 403
    return outcome


@app.post('/configs/')
def configs_set(response: Response, port: str='', make: str='', model: str='', limit: int=0):
    global state
    try:
        outcome = engine.save_config_file(port, make, model, limit)
        state = engine._load_application_state()
        if 'errors' in outcome:
            response.status_code = 422
    except:
        outcome = state
        response.status_code = 403
    return state


@app.get('/instrument_height/')
def instrument_height_get():
    """"This function gets the instrument height above the occupied point."""
    return engine.tripod.get_instrument_height()


@app.post('/instrument_height/')
def instrument_height_set(response: Response, height: float):
    """"This function gets the instrument height above the occupied point."""
    try:
        outcome = engine.totalstation.set_azimuth(degrees, minutes, seconds)
        if 'errors' in outcome:
            response.status_code = 422
    except:
        outcome = state
        response.status_code = 403
    return outcome


@app.get('/cancel/')
def measurement_cancel():
    """This function stops a measurement in progress."""
    outcome = engine.totalstation.cancel_measurement()
    return outcome


@app.get('/measurement/')
def measurement_take(response: Response):
    """This function tells the total station to start measuring a point."""
    try:
        if engine.prism.get_prism_offset()['results']:
            outcome = engine.totalstation.take_measurement()
        else:
            outcome = {'success': False, 'errors': ['Set a prism offset before proceeding.']}
        if 'errors' in outcome:
            response.status_code = 422
        else:
            outcome = engine.calculations.apply_offsets_to_measurement(outcome)
    except:
        outcome = state
        response.status_code = 403
    return outcome


# @app.post('/mode_hr/')
# def mode_hr_set(response: Response):
#     """This function sets the total station to horizontal right mode."""
#     outcome = engine._load_application_state()
#     if outcome['success']:
#         outcome = engine.totalstation.set_mode_hr()
#     if 'errors' in outcome:
#         response.status_code = 422
#     return outcome


# @app.get('/occupied_point/')
# def occupied_point_get():
#     """This function gets the coordinates of the occupied point."""
#     outcome = engine._load_application_state()
#     if outcome['success']:
#         outcome = engine.tripod.get_occupied_point()
#     if 'errors' in outcome:
#         response.status_code = 422
#     return outcome


# @app.post('/occupied_point/')
# def occupied_point_set(response: Response, northing: float, easting: float, elevation: float):
#     """This function sets the coordinates of the occupied point."""
#     outcome = engine._load_application_state()
#     if outcome['success']:
#         outcome = engine.tripod.set_occupied_point(northing, easting, elevation)
#     if 'errors' in outcome:
#         response.status_code = 422
#     return outcome


# @app.get('/prism_offset/')
# def prism_offset_get(response: Response):
#     """This function gets the prism offsets."""
#     outcome = engine._load_application_state()
#     if outcome['success']:
#         outcome = engine.prism.get_prism_offset()
#     if 'errors' in outcome:
#         response.status_code = 422
#     return outcome


# @app.post('/prism_offset/')
# def prism_offset_set(response: Response, offsets: dict):
#     """This function sets the prism offsets."""
#     outcome = engine._load_application_state()
#     if outcome['success']:
#         outcome = engine.prism.set_prism_offset(**offsets)
#     if 'errors' in outcome:
#         response.status_code = 422
#     return outcome


# @app.post('/session/')
# def session_start(response: Response, label: str, surveyor: str, occupied_point_id: int, backsight_station_id: int=0, instrument_height: float=0.0, prism_height: float=0.0, degrees: int=0, minutes: int=0, seconds: int=0):
#     """This function starts a new surveying session."""
#     outcome = engine._load_application_state()
#     if outcome['success']:
#         if backsight_station_id:
#             outcome = engine.start_surveying_session_with_backsight(
#                 label,
#                 surveyor,
#                 occupied_point_id,
#                 backsight_station_id,
#                 prism_height,
#             )
#         else:
#             outcome = engine.start_surveying_session_with_azimuth(
#                 label,
#                 surveyor,
#                 occupied_point_id,
#                 instrument_height,
#                 degrees,
#                 minutes,
#                 seconds,
#             )
#     if 'errors' in outcome:
#         response.status_code = 422
#     return outcome
