"""This module contains the API for ShootPoints."""

from fastapi import FastAPI, Response, Query
from fastapi.responses import HTMLResponse

import core


app = FastAPI()


@app.get('/')
def homepage():
    """This is the homepage for the ShootPoints Web API."""
    return HTMLResponse(content='<a href="/docs">Click here for documentation of this API</a>')


####################
## CORE ENDPOINTS ##
####################

@app.post('/config/')
def set_configs(response: Response, port: str='', make: str='', model: str='', limit: int=0):
    outcome = core.save_config_file(port, make, model, limit)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.get('/summary/')
def show_summary():
    """This function gives summary data about the current state of ShootPoints."""
    return core.summarize_application_state()


###############################
## CLASSIFICATIONS ENDPOINTS ##
###############################

@app.get('/class/')
def get_all_classes_and_subclasses(response: Response):
    """This function returns all the classes and subclasses in the database."""
    outcome = core.classifications.get_all_classes_and_subclasses()
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.post('/class/')
def create_new_class(response: Response, name: str, description: str=None):
    """This function saves a new class to the database."""
    outcome = core.classifications.create_new_class(name, description)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.delete('/class/')
def delete_class(response: Response, id: int):
    """This function deletes a class from the database."""
    outcome = core.classifications.delete_class(id)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.post('/subclass/')
def create_new_subclass(response: Response, classes_id: int, name: str, description: str=None):
    """This function saves a new subclass to the database."""
    outcome = core.classifications.create_new_subclass(classes_id, name, description)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.delete('/subclass/')
def delete_subclass(response: Response, id: int):
    """This function deletes a subclass from the database."""
    outcome = core.classifications.delete_subclass(id)
    if not outcome['success']:
        response.status_code = 422
    return outcome


#####################
## PRISM ENDPOINTS ##
#####################

@app.get('/prism/')
def get_prism_offsets(response: Response):
    """This function gets the prism offsets."""
    outcome = core.prism.get_readable_offsets()
    if not outcome['offsets']:
        response.status_code = 422
    return outcome


@app.post('/prism/')
def set_prism_offsets(response: Response, offsets: dict):
    # TODO: Update this endpoint to take each type of offset and construct the offsets dictionary
    """This function sets the prism offsets."""
    outcome = core.prism.set_prism_offsets(**offsets)
    if not outcome['success']:
        response.status_code = 422
    return outcome


#####################
## SITES ENDPOINTS ##
#####################

@app.get('/site/')
def get_site(response: Response, id: int=None):
    """This function gets the site indicate or all sites, if the id isn’t passed."""
    if id:
        outcome = core.sites.get_site(id)
    else:
        outcome = core.sites.get_all_sites()
    if not outcome['success']:
        response.status_code = 422
    return outcome


######################
## SURVEY ENDPOINTS ##
######################

@app.post('/session/')
def start_surveying_session(
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


#############################
## TOTAL STATION ENDPOINTS ##
#############################

@app.get('/cancel/')
def cancel_measurement():
    """This function stops a measurement in progress."""
    outcome = core.totalstation.cancel_measurement()
    return outcome


@app.get('/measurement/')
def take_measurement(response: Response):
    """This function tells the total station to start measuring a point."""
    outcome = core.survey.take_shot()
    if not outcome['success']:
        response.status_code = 422
    return outcome


######################
## TRIPOD ENDPOINTS ##
######################

@app.post('/station/')
def save_survey_station(
        response: Response,
        sites_id: int,
        name: str,
        elevation: float,
        coordinatesystem: str = Query('Site', enum=['Site', 'UTM', 'Lat/Lon']),
        northing: float=None,
        easting: float=None,
        utmzone: str=None,
        latitude: float=None,
        longitude: float=None,
        description: str=None,
    ):
    """This function saves a new survey station to the database."""
    if coordinatesystem == 'Site':
        coordinates = {'northing': northing, 'easting': easting, 'elevation': elevation}
    elif coordinatesystem == 'UTM':
        coordinates = {'northing': northing, 'easting': easting, 'elevation': elevation, 'utmzone': utmzone}
    elif coordinatesystem == 'Lat/Lon':
        coordinates = {'latitude': latitude, 'longitude': longitude, 'elevation': elevation}
    outcome = core.tripod.save_station(sites_id, name, coordinatesystem, coordinates)
    if not outcome['success']:
        response.status_code = 422
    return outcome
