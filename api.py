"""This module contains the API for ShootPoints."""
from fastapi import FastAPI, Form, Response
from fastapi.staticfiles import StaticFiles


import core


app = FastAPI()

app.mount(
    "/webapp",
    StaticFiles(directory="../shootpoints-web-frontend", html="index.html"),
    name="webapp",
)


##################
# CORE ENDPOINTS #
##################


@app.put("/config/", status_code=201)
async def set_configs(
    response: Response,
    port: str = Form(None),
    make: str = Form(None),
    model: str = Form(None),
    limit: int = Form(0),
):
    outcome = core.save_config_file(port, make, model, limit)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


#############################
# CLASSIFICATIONS ENDPOINTS #
#############################


@app.get("/class/")
async def get_classes(response: Response):
    """This function returns all the classes in the database."""
    outcome = core.classifications.get_all_classes()
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.get("/subclass/{classes_id}")
async def get_subclasses(response: Response, classes_id: int):
    """This function returns all the subclasses of the indicated class in the database."""
    outcome = core.classifications.get_subclasses(classes_id)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.post("/class/", status_code=201)
async def save_new_class(
    response: Response, name: str = Form(...), description: str = Form(None)
):
    """This function saves a new class to the database."""
    outcome = core.classifications.save_new_class(name, description)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.delete("/class/")
async def delete_class(
    response: Response,
    classes_id: int = Form(...),
):
    """This function deletes the indicated class from the database."""
    outcome = core.classifications.delete_class(classes_id)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.post("/subclass/", status_code=201)
async def save_new_subclass(
    response: Response,
    classes_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(None),
):
    """This function saves a new subclass to the database."""
    outcome = core.classifications.save_new_subclass(classes_id, name, description)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.delete("/subclass/")
async def delete_subclass(
    response: Response, classes_id: int = Form(...), subclasses_id: int = Form(...)
):
    """This function deletes the indicated subclass from the database."""
    outcome = core.classifications.delete_subclass(classes_id, subclasses_id)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


######################
# DATABASE ENDPOINTS #
######################


@app.get("/setuperrors/")
async def get_setup_errors():
    """This function returns any ShootPoints setup errors."""
    return core.database.get_setup_errors()


###################
# PRISM ENDPOINTS #
###################


@app.get("/offsets/")
async def get_offset_types_and_directions():
    """This function gets the types of prism offsets and their applicable directions."""
    return core.prism.get_offset_types_and_directions()


@app.get("/prism/")
async def get_readable_prism_offsets(response: Response):
    """This function gets the prism offsets."""
    outcome = ", ".join(core.prism.get_readable_prism_offsets()["offsets"])
    return outcome


@app.get("/prism_raw/")
async def get_raw_prism_offsets(response: Response):
    """This function gets the prism offsets."""
    outcome = core.prism.get_raw_prism_offsets()
    return outcome


@app.put("/prism/", status_code=201)
async def set_prism_offsets(
    response: Response,
    vertical_distance: float = Form(None),
    vertical_direction: int = Form(...),
    latitude_distance: float = Form(None),
    latitude_direction: int = Form(...),
    longitude_distance: float = Form(None),
    longitude_direction: int = Form(...),
    radial_distance: float = Form(None),
    radial_direction: int = Form(...),
    tangent_distance: float = Form(None),
    tangent_direction: int = Form(...),
    wedge_distance: float = Form(None),
    wedge_direction: int = Form(...),
):
    """This function sets the prism offsets."""
    outcome = core.prism.set_prism_offsets(
        vertical_distance * vertical_direction,
        latitude_distance * latitude_direction,
        longitude_distance * longitude_direction,
        radial_distance * radial_direction,
        tangent_distance * tangent_direction,
        wedge_distance * wedge_direction,
    )
    if "errors" in outcome:
        response.status_code = 400
    else:
        outcome["result"] = "Prism offsets updated."
    return outcome


###################
# SITES ENDPOINTS #
###################


@app.get("/site/")
async def get_all_sites(response: Response):
    """This function gets all the sites in the database."""
    outcome = core.sites.get_all_sites()
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.post("/site/", status_code=201)
async def save_new_site(
    response: Response,
    name: str = Form(...),
    description: str = Form(None),
):
    """This function saves a new site to the database."""
    outcome = core.sites.save_site(name, description)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.delete("/site/")
async def delete_site(
    response: Response,
    sites_id: int = Form(...),
):
    """This function deletes the indicated site from the database."""
    outcome = core.sites.delete_site(sites_id)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


####################
# SURVEY ENDPOINTS #
####################


@app.get("/atmosphere/")
async def get_atmospheric_conditions():
    """This function gets the pressure and temperature, as last set and saved to the ShootPoints database."""
    return core.survey.get_atmospheric_conditions()


@app.put("/atmosphere/", status_code=201)
async def set_atmospheric_conditions(
    response: Response,
    temperature: int = Form(...),
    pressure: int = Form(...),
):
    """This function sets the pressure and temperature, for use in atmospheric corrections when taking shots."""
    outcome = core.survey.set_atmospheric_conditions(temperature, pressure)
    if "errors" in outcome:
        response.status_code = 400
    else:
        outcome["result"] = "Atmospheric conditions updated."
    return outcome


@app.get("/geometry/")
async def get_geometries():
    """This function gets the geometries in the ShootPoints database, for use when creating a new grouping."""
    return core.survey.get_geometries()


@app.get("/grouping/")
async def get_current_grouping():
    """This function gets basic information about the currently active point grouping."""
    return core.survey.get_current_grouping()


@app.post("/grouping/", status_code=201)
async def start_new_grouping(
    response: Response,
    geometry_id: int = Form(...),
    subclasses_id: int = Form(...),
    label: str = Form(...),
    description: str = Form(None),
):
    """This function saves a new grouping to the database."""
    outcome = core.survey.start_new_grouping(
        geometry_id, subclasses_id, label, description
    )
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.get("/session/")
async def get_current_session():
    """This function gets basic information about the currently active surveying session."""
    return core.survey.get_current_session()


@app.post("/session/", status_code=201)
async def start_new_surveying_session(
    response: Response,
    label: str = Form(...),
    surveyor: str = Form(...),
    sites_id: int = Form(...),
    occupied_point_id: int = Form(...),
    sessiontype: str = Form(...),
    backsight_station_id: int = Form(0),
    prism_height: float = Form(0.00),
    instrument_height: float = Form(0.00),
    azimuth: float = Form(0.0000),  # ddd.mmss format
):
    """This function saves a new surveying session to the database."""
    if sessiontype == "Backsight":
        outcome = core.survey.start_surveying_session_with_backsight(
            label,
            surveyor,
            sites_id,
            occupied_point_id,
            backsight_station_id,
            prism_height,
        )
    elif sessiontype == "Azimuth":
        outcome = core.survey.start_surveying_session_with_azimuth(
            label, surveyor, sites_id, occupied_point_id, instrument_height, azimuth
        )
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.get("/shot/")
def take_shot(response: Response):
    """This function tells the total station to start measuring a point."""
    outcome = core.survey.take_shot()
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.post("/shot/", status_code=201)
async def save_last_shot(
    response: Response,
    label: str = Form(None),
    comment: str = Form(None),
):
    """This function saves the last shot to the database."""
    # Note: the front end should not prompt the user for label or comment in cases where groupings.geometry_id = 1 (= isolate point).
    outcome = core.survey.save_last_shot(label, comment)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


###########################
# TOTAL STATION ENDPOINTS #
###########################


@app.get("/cancel/")
def cancel_shot():
    """This function stops a measurement in progress."""
    outcome = core.totalstation.cancel_measurement()
    return outcome


####################
# TRIPOD ENDPOINTS #
####################


@app.get("/station/{sites_id}")
async def get_stations(response: Response, sites_id: int):
    """This function gets all the stations in the database at the indicated site."""
    outcome = core.tripod.get_stations(sites_id)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.post("/station/", status_code=201)
async def save_new_station(
    response: Response,
    sites_id: int = Form(...),
    name: str = Form(...),
    coordinatesystem: str = Form(...),
    northing: float = Form(None),
    easting: float = Form(None),
    elevation: float = Form(None),
    utmzone: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
    description: str = Form(None),
):
    """This function saves a new survey station to the database."""
    if coordinatesystem == "Site":
        coordinates = {"northing": northing, "easting": easting, "elevation": elevation}
    elif coordinatesystem == "UTM":
        coordinates = {
            "northing": northing,
            "easting": easting,
            "elevation": elevation,
            "utmzone": utmzone,
        }
    elif coordinatesystem == "Lat/Lon":
        coordinates = {
            "latitude": latitude,
            "longitude": longitude,
            "elevation": elevation,
        }
    outcome = core.tripod.save_new_station(
        sites_id,
        name,
        coordinatesystem,
        coordinates,
        description,
    )
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.delete("/station/")
async def delete_station(
    response: Response,
    sites_id: int = Form(...),
    stations_id: int = Form(...),
):
    """This function deletes the indicated station from the database."""
    outcome = core.tripod.delete_station(sites_id, stations_id)
    if "errors" in outcome:
        response.status_code = 400
    return outcome
