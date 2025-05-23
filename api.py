"""This module contains the API for ShootPoints."""

from typing import Optional
from fastapi import FastAPI, Form, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import datetime, os, time

import core


app = FastAPI()

app.mount(
    "/webapp",
    StaticFiles(directory="../frontend", html=True),
    name="webapp",
)


@app.get("/", status_code=301)
async def redirect(response: Response):
    """This function redirects requests to the ShootPoints web interface."""
    response.headers["Location"] = "/webapp"
    return


##########################
# RASPBERRY PI ENDPOINTS #
##########################


@app.get("/raspberrypi/")
async def check_for_raspberrypi():
    """This function checks that ShootPoints is running on a Raspberry Pi."""
    raspberrypi = False
    try:
        with open("/proc/device-tree/model", "r") as f:
            content = f.read()
            if "Raspberry Pi" in content:
                raspberrypi = True
    except FileNotFoundError:
        pass
    return raspberrypi


@app.get("/raspberrypi/reboot/")
async def reboot_rpi():
    """This function reboots the Raspberry Pi."""
    os.system("sudo reboot")


@app.get("/raspberrypi/shutdown/")
async def shut_down_rpi():
    """This function shuts down the Raspberry Pi."""
    os.system("sudo shutdown -h now")


@app.get("/raspberrypi/clock/")
async def get_rpi_time():
    """This function checks the clock on Raspberry Pi hosts."""
    return int(time.time() * 1000)


@app.put("/raspberrypi/clock/")
async def set_rpi_clock(
    datetimestring: str = Form(...),
):
    """This function sets the date and time on the Raspberry Pi."""
    os.system(f"sudo date -s '{datetimestring}'")
    return {"result": "Raspberry Pi clock updated."}


##################
# CORE ENDPOINTS #
##################


@app.get("/configs/")
async def get_configs():
    """This function gets the current configs in the configs.ini file and the available ports and total station models."""
    return core.get_configs()


@app.put("/configs/", status_code=201)
async def set_configs(
    response: Response,
    port: str = Form(None),
    make: str = Form(None),
    model: str = Form(None),
    limit: float = Form(0.0),
):
    """This function sets the application configs in the configs.ini file."""
    outcome = core.save_config_file(port, make, model, limit)
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.get("/version/")
async def get_version():
    """This function gets the version of ShootPoints-Web app and database."""
    return {"version": core.__version__}


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


@app.get("/database/")
async def download_entire_database():
    """This function downloads the ShootPoints database SQLite file in its entirety."""
    date = str(datetime.datetime.now()).split(" ")[0]
    core.exporters.export_database_file()
    return FileResponse(
        "exports/database.zip",
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=ShootPoints Database {date}.zip"
        },
    )


@app.get("/export/{sessions_id}")
async def export_session_data(response: Response, sessions_id: int):
    """This function downloads a ZIP file of the requested session and its shots."""
    sql = "SELECT label FROM sessions WHERE id = ?"
    sessionlabel = (
        core.database._read_from_database(sql, (sessions_id,))["results"][0]["label"]
        .replace("/", "_")
        .replace(":", "_")
        .replace("\\", "_")
    )
    core.exporters.export_session_data(sessions_id)
    return FileResponse(
        "exports/export.zip",
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=ShootPoints Data ({sessionlabel}).zip"
        },
    )


@app.get("/setuperrors/")
async def get_setup_errors():
    """This function returns any ShootPoints setup errors."""
    print(core._load_application())
    return core.database.get_setup_errors()


@app.delete("/reset/")
async def reset_database(
    preservesitesandstations: bool = Form(False),
    preserveclassesandsubclasses: bool = Form(False),
    ignore: str = Form("ignore"),
):
    """This function resets the ShootPoints database."""
    return core.database.reset_database(
        preservesitesandstations, preserveclassesandsubclasses
    )


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
    vertical_distance: float = Form(0),
    vertical_direction: int = Form(...),
    latitude_distance: float = Form(0),
    latitude_direction: int = Form(...),
    longitude_distance: float = Form(0),
    longitude_direction: int = Form(...),
    radial_distance: float = Form(0),
    radial_direction: int = Form(...),
    tangent_distance: float = Form(0),
    tangent_direction: int = Form(...),
    wedge_distance: float = Form(0),
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


@app.get("/abort/")
async def abort_resection():
    """This function stops a measurement in progress."""
    outcome = core.survey.abort_resection()
    return outcome


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
    geometries_id: int = Form(...),
    subclasses_id: int = Form(...),
    label: str = Form(...),
    description: str = Form(None),
):
    """This function saves a new grouping to the database."""
    outcome = core.survey.start_new_grouping(
        geometries_id, subclasses_id, label, description
    )
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.put("/grouping/")
async def end_current_grouping(response: Response):
    """This function ends the current grouping."""
    outcome = core.survey.end_current_grouping()
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.get("/livemap/")
async def export_session_for_livemap(sessions_id: Optional[int] = None):
    """This function gets a survey data from a session to be plotted by leafletjs."""
    return core.survey.export_session_for_livemap(sessions_id)


@app.get("/session/")
async def get_current_session():
    """This function gets basic information about the currently active surveying session."""
    return core.survey.get_current_session()


@app.get("/sessions/")
async def get_all_sessions():
    """This function gets basic identifying information about all the surveying sessions in the database."""
    return core.survey.get_all_sessions()


@app.post("/session/", status_code=201)
def start_new_session(
    response: Response,
    label: str = Form(...),
    surveyor: str = Form(...),
    sites_id: int = Form(...),
    temperature: int = Form(...),
    pressure: int = Form(...),
    sessiontype: str = Form(...),
    occupied_point_id: int = Form(0),
    backsight_station_id: int = Form(0),
    new_station_name: str = Form(""),
    backsight_station_1_id: int = Form(0),
    backsight_station_2_id: int = Form(0),
    prism_height: float = Form(0.00),
    instrument_height: float = Form(0.00),
    azimuth: float = Form(0.0000),  # ddd.mmss format
):
    """This function saves a new surveying session to the database."""
    outcome = {}
    sessiontype = sessiontype.capitalize()
    if sessiontype == "Backsight":
        outcome = core.survey.start_surveying_session_with_backsight(
            label,
            surveyor,
            sites_id,
            occupied_point_id,
            backsight_station_id,
            prism_height,
            temperature,
            pressure,
        )
    elif sessiontype == "Azimuth":
        outcome = core.survey.start_surveying_session_with_azimuth(
            label,
            surveyor,
            sites_id,
            occupied_point_id,
            instrument_height,
            azimuth,
            temperature,
            pressure,
        )
    elif sessiontype == "Resection":
        outcome = core.survey.start_surveying_session_with_resection(
            label,
            surveyor,
            sites_id,
            new_station_name,
            backsight_station_1_id,
            backsight_station_2_id,
            instrument_height,
            prism_height,
            temperature,
            pressure,
        )
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.put("/session/")
async def end_current_session(response: Response):
    """This function ends the current surveying session."""
    outcome = core.survey.end_current_session()
    if "errors" in outcome:
        response.status_code = 400
    return outcome


@app.delete("/session/")
async def delete_session(
    response: Response,
    sessions_id: int = Form(...),
):
    """This function deletes the indicated session from the database, plus all its shots and groupings."""
    outcome = core.survey.delete_session(sessions_id)
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
    comment: str = Form(None),
):
    """This function saves the last shot to the database."""
    outcome = core.survey.save_last_shot(comment)
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
    coordinates = {}
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
