"""This module contains the API for ShootPoints."""

from fastapi import FastAPI, Response, Query
from fastapi.responses import HTMLResponse

import core


app = FastAPI()


@app.get('/')
def homepage():
    """This is the homepage for the ShootPoints Web API."""
    return HTMLResponse(content='<a href="/docs">Click here for documentation of this API</a>')


## CORE ENDPOINTS ##

@app.post('/configs/')
def configs_set(response: Response, port: str='', make: str='', model: str='', limit: int=0):
    outcome = core.save_config_file(port, make, model, limit)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.get('/summary/')
def show_summary():
    """This function gives summary data about the current state of ShootPoints."""
    return core.summarize_application_state()


## CLASSIFICATIONS ENDPOINTS ##

@app.get('/classes/')
def classifications_get(response: Response):
    """This function returns all the classes and subclasses in the database."""
    outcome = core.classifications.get_classes_and_subclasses()
    if not outcome['success']:
        response.status_code = 422
    return outcome


## PRISM ENDPOINTS ##

@app.get('/prism_offset/')
def prism_offset_get(response: Response):
    """This function gets the prism offsets."""
    outcome = core.prism.get_readable_offsets()
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.post('/prism_offset/')
def prism_offset_set(response: Response, offsets: dict):
    # TODO: Update this endpoint to take each type of offset and construct the offsets dictionary
    """This function sets the prism offsets."""
    outcome = core.prism.set_prism_offsets(**offsets)
    if not outcome['success']:
        response.status_code = 422
    return outcome


## SITES ENDPOINTS ##

@app.get('/site/')
def site_get(response: Response, id: int=None):
    """This function gets the site indicate or all sites, if the id isn’t passed."""
    if id:
        outcome = core.sites.get_site(id)
    else:
        outcome = core.sites.get_all_sites()
    if not outcome['success']:
        response.status_code = 422
    return outcome


## SURVEY ENDPOINTS ##

@app.post('/session/')
def surveying_session_start(
        response: Response,
        label: str,
        surveyor: str,
        occupied_point_id: int,
        sessiontype: str=Query(..., enum=['Backsight', 'Azimuth']),
        backsight_station_id: int=0,
        prism_height: float=0.0,
        instrument_height: float=0.0,
        azimuth: float=0.0000  # dd.mmss format
    ):
    if sessiontype == 'Backsight':
        outcome = core.survey.start_surveying_session_with_backsight(label, surveyor, occupied_point_id, backsight_station_id, prism_height)
    elif sessiontype == 'Azimuth':
        outcome = core.survey.start_surveying_session_with_azimuth(label, surveyor, occupied_point_id, instrument_height, azimuth)
    """This function starts a new surveying session."""
    if not outcome['success']:
        response.status_code = 422
    return outcome


## TOTAL STATION ENDPOINTS ##

@app.get('/cancel/')
def measurement_cancel():
    """This function stops a measurement in progress."""
    outcome = core.totalstation.cancel_measurement()
    return outcome


@app.get('/measurement/')
def measurement_take(response: Response):
    """This function tells the total station to start measuring a point."""
    outcome = core.survey.take_shot()
    if not outcome['success']:
        response.status_code = 422
    return outcome


## TRIPOD ENDPOINTS ##

@app.post('/station/')
def survey_station_save(
        response: Response,
        name: str,
        elevation: float,
        coordinatesystem: str = Query('Site', enum=['Site', 'UTM', 'Lat/Lon']),
        northing: float=0.0,
        easting: float=0.0,
        utmzone: str='',
        latitude: float=0.0,
        longitude: float=0.0
    ):
    if coordinatesystem == 'Site':
        coordinates = {'northing': northing, 'easting': easting, 'elevation': elevation}
    elif coordinatesystem == 'UTM':
        coordinates = {'northing': northing, 'easting': easting, 'elevation': elevation, 'utmzone': utmzone}
    elif coordinatesystem == 'Lat/Lon':
        coordinates = {'latitude': latitude, 'longitude': longitude, 'elevation': elevation}
    """This function saves a new survey station to the database."""
    outcome = core.tripod.save_station(name, coordinatesystem, coordinates)
    if not outcome['success']:
        response.status_code = 422
    return outcome
