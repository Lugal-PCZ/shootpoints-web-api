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
def set_configs(
        response: Response,
        port: str=None,
        make: str=None,
        model: str=None,
        limit: int=0
    ):
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
def create_new_class(
        response: Response,
        name: str,
        description: str=None
    ):
    """This function saves a new class to the database."""
    outcome = core.classifications.create_new_class(name, description)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.delete('/class/{id}')
def delete_class(
        response: Response,
        id: int
    ):
    """This function deletes the indicated class from the database."""
    outcome = core.classifications.delete_class(id)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.post('/class/{classes_id}')
def create_new_subclass(
        response: Response,
        classes_id: int,
        name: str,
        description: str=None
    ):
    """This function saves a new subclass to the database."""
    outcome = core.classifications.create_new_subclass(classes_id, name, description)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.delete('/class/{classes_id}/{id}')
def delete_subclass(
        response: Response,
        classes_id: int,
        id: int
    ):
    """This function deletes the indicated subclass from the database."""
    outcome = core.classifications.delete_subclass(classes_id, id)
    if not outcome['success']:
        response.status_code = 422
    return outcome


#####################
## PRISM ENDPOINTS ##
#####################

@app.get('/offsets/')
def get_offset_types_and_directions():
    """This function gets the types of prism offsets and their applicable directions."""
    return core.prism.get_offset_types_and_directions()


@app.get('/prism/')
def get_prism_offsets(response: Response):
    """This function gets the prism offsets."""
    outcome = core.prism.get_readable_offsets()
    if not outcome['offsets']:
        response.status_code = 422
    return outcome


@app.post('/prism/')
def set_prism_offsets(
        response: Response,
        offsets: dict
    ):
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
def get_all_sites(response: Response):
    """This function gets all the sites in the database."""
    outcome = core.sites.get_all_sites()
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.get('/site/{id}')
def get_site(
        response: Response,
        id: int
    ):
    """This function gets the site indicated."""
    outcome = core.sites.get_site(id)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.post('/site/')
def create_new_site(
        response: Response,
        name: str,
        description: str=None
    ):
    """This function saves a new site to the database."""
    outcome = core.sites.save_site(name, description)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.delete('/site/{id}')
def delete_site(
        response: Response,
        id: int,
    ):
    """This function deletes the indicated site from the database."""
    outcome = core.sites.delete_site(id)
    if not outcome['success']:
        response.status_code = 422
    return outcome


######################
## SURVEY ENDPOINTS ##
######################

@app.post('/grouping/')
def start_new_grouping(
        response: Response,
        geometry_id: int,
        subclasses_id: int,
        label: str,
        comment: str=None
    ):
    """This function saves a new grouping to the database."""
    outcome = core.survey.start_new_grouping(geometry_id, subclasses_id, label, comment)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.post('/session/{sites_id}')
def start_surveying_session(
        response: Response,
        label: str,
        surveyor: str,
        sites_id: int,
        occupied_point_id: int,
        sessiontype: str=Query(..., enum=['Backsight', 'Azimuth']),
        backsight_station_id: int=0,
        prism_height: float=0.0,
        instrument_height: float=0.0,
        azimuth: float=0.0000  # dd.mmss format
    ):
    """This function saves a new surveying session to the database."""
    if sessiontype == 'Backsight':
        outcome = core.survey.start_surveying_session_with_backsight(label, surveyor, sites_id, occupied_point_id, backsight_station_id, prism_height)
    elif sessiontype == 'Azimuth':
        outcome = core.survey.start_surveying_session_with_azimuth(label, surveyor, sites_id, occupied_point_id, instrument_height, azimuth)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.get('/shot/')
def take_shot(response: Response):
    """This function tells the total station to start measuring a point."""
    outcome = core.survey.take_shot()
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.post('/shot/')
def save_last_shot(
        response: Response,
        label: str=None,
        comment: str=None
    ):
    """This function saves the last shot to the database."""
    # Note: the front end should not prompt the user for label or comment in cases where groupings.geometry_id = 1 (= isolate point).
    outcome = core.survey.save_last_shot(label, comment)
    if not outcome['success']:
        response.status_code = 422
    return outcome


#############################
## TOTAL STATION ENDPOINTS ##
#############################

@app.get('/cancel/')
def cancel_shot():
    """This function stops a measurement in progress."""
    outcome = core.totalstation.cancel_measurement()
    return outcome


######################
## TRIPOD ENDPOINTS ##
######################

@app.get('/station/{sites_id}')
def get_all_station_at_site(
        response: Response,
        sites_id: int
    ):
    """This function gets all the stations in the database at the indicated site."""
    outcome = core.tripod.get_all_station_at_site(sites_id)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.get('/station/{sites_id}/{id}')
def get_station(
        response: Response,
        sites_id: int,
        id: int
    ):
    """This function gets the station indicated."""
    outcome = core.tripod.get_station(sites_id, id)
    if not outcome['success']:
        response.status_code = 422
    return outcome


@app.post('/station/{sites_id}')
def save_survey_station(
        response: Response,
        sites_id: int,
        name: str,
        coordinatesystem: str = Query(..., enum=['Site', 'UTM', 'Lat/Lon']),
        northing: float=None,
        easting: float=None,
        elevation: float=None,
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


@app.delete('/station/{sites_id}/{id}')
def delete_class(
        response: Response,
        sites_id: int,
        id: int
    ):
    """This function deletes the indicated station from the database."""
    outcome = core.tripod.delete_station(sites_id, id)
    if not outcome['success']:
        response.status_code = 422
    return outcome
