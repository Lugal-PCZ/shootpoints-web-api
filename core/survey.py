"""This module contains functions for handling the surveying session and associated data."""

import datetime
import math
from typing import Optional

from . import calculations
from . import database
from . import prism
from . import tripod
from .utilities import format_outcome


SESSIONTYPES = ["Backsight", "Azimuth", "Resection"]

backsighterrorlimit = 0.0
totalstation = None
sessionid = 0
groupingid = 0
activeshotdata = {}
pressure = 760
temperature = 15
# cached values for second step of start_surveying_session_with_resection()
resection_instrument_height = 0.0
resection_backsight_1 = {}
resection_backsight_2 = {}
resection_backsight_1_measurement = {}


def _get_timestamp() -> str:
    """This function returns the current timestamp, formatted for saving in the database."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _save_new_session(data: tuple) -> Optional[int]:
    """This function saves the surveying session information to the database."""
    global sessionid
    global groupingid
    global activeshotdata
    sql = (
        "INSERT INTO sessions ("
        " label,"
        " started,"
        " surveyor,"
        " stations_id_occupied,"
        " stations_id_backsight,"
        " stations_id_resection_left,"
        " stations_id_resection_right,"
        " azimuth,"
        " instrumentheight,"
        " pressure,"
        " temperature"
        f") VALUES(?, '{_get_timestamp()}', ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    saved = database._save_to_database(sql, data)
    if "errors" not in saved:
        sessionid = database.cursor.lastrowid
        _ = database._save_to_database(
            "UPDATE savedstate SET currentsession = ?", (sessionid,)
        )
    else:
        sessionid = 0
    activeshotdata = {}
    return sessionid


def _save_shot_as_new_station() -> dict:
    """This function checks if the last shot was a survey station, and if so saves it to the stations database table."""
    outcome = {}
    currentgrouping = database._read_from_database(
        "SELECT * FROM groupings WHERE id = ?",
        (groupingid,),
    )["results"][0]
    if (
        currentgrouping["subclasses_id"] == 1
    ):  # Survey Station is pre-defined to have subclass id 1
        sql = (
            "SELECT "
            "  sta.* "
            "FROM sessions sess "
            "JOIN stations sta ON sess.stations_id_occupied = sta.id "
            "WHERE sess.id = ?"
        )
        occupiedstation = database._read_from_database(sql, (sessionid,))["results"][0]
        coordinatesystem = "UTM"
        if not occupiedstation["utmzone"]:
            coordinatesystem = "Site"
        outcome = tripod.save_new_station(
            occupiedstation["sites_id"],
            currentgrouping["label"],
            coordinatesystem,
            {
                "northing": activeshotdata["calculated_n"],
                "easting": activeshotdata["calculated_e"],
                "elevation": activeshotdata["calculated_z"],
                "utmzone": occupiedstation["utmzone"],
            },
            currentgrouping["description"],
        )
    return outcome


def get_geometries() -> dict:
    """This function returns the types of geometries saved in the database, for use by the application front end."""
    outcome = {"errors": [], "sites": {}}
    query = database._read_from_database("SELECT * FROM geometries")
    if "errors" not in query:
        outcome["geometries"] = query["results"]
    return format_outcome(outcome, ["geometries"])


def get_atmospheric_conditions() -> dict:
    """This function returns the current air pressure and temperature, as most recently set by the surveyor."""
    return {"pressure": pressure, "temperature": temperature}


def set_atmospheric_conditions(temp: int, press: int) -> dict:
    """This function sets the current air pressure and temperature, for correcting the raw total station measurements."""
    outcome = {"errors": [], "result": ""}
    global temperature
    global pressure
    mintemp = -18
    maxtemp = 50
    minpress = 720
    maxpress = 800
    try:
        if not mintemp <= int(temp) <= maxtemp:
            outcome["errors"].append(
                f"The value given for air temperature ({temp}°C) is outside reasonable limits ({mintemp}°C to {maxtemp}°C)."
            )
    except ValueError:
        outcome["errors"].append(
            f"The value given for air temperature ({temp}) is not numeric."
        )
    try:
        if not minpress <= int(press) <= maxpress:
            outcome["errors"].append(
                f"The value given for atmospheric pressure ({press}mmHg) is outside the normal range ({minpress}mmHg to {maxpress}mmHg)."
            )
    except ValueError:
        outcome["errors"].append(
            f"The value given for atmospheric pressure ({press}) is not numeric."
        )
    if not outcome["errors"]:
        sql = "UPDATE savedstate SET pressure = ?, temperature = ?"
        savetodatabase = database._save_to_database(sql, (press, temp))
        if "errors" in savetodatabase:
            outcome["errors"].append(
                "An error occurred while saving the temperature and pressure to the database."
            )
        else:
            pressure = press
            temperature = temp
            p = press * 106.036
            t = temp + 273.15
            ppm = round((279.66 - (p / t)) * pow(10, -6) * 1000000)
            outcome["result"] = (
                f"Temperature and pressure are now set to {temp}°C and {press}mmHg ({ppm}ppm)."
            )
    return format_outcome(outcome)


def start_surveying_session_with_azimuth(
    label: str,
    surveyor: str,
    sites_id: int,
    occupied_point_id: int,
    instrument_height: float,
    azimuth: float,
    temperature: int,
    pressure: int,
) -> dict:
    """This function starts a new surveying session with an azimuth to a landmark."""

    # check for setup errors, stopping execution if there are any
    setuperrors = database.get_setup_errors()
    if "errors" in setuperrors:
        return setuperrors

    # set the atmospheric conditions
    outcome = {"result": "", "errors": []}
    atmosphere = set_atmospheric_conditions(temperature, pressure)
    if "errors" in atmosphere:
        outcome["errors"].extend(atmosphere["errors"])

    # set the occupied point
    occupiedpoint = tripod.get_station(sites_id, occupied_point_id)
    if "errors" in occupiedpoint:
        outcome["errors"].extend(occupiedpoint["errors"])
    else:
        occupied_n = occupiedpoint["station"]["northing"]
        occupied_e = occupiedpoint["station"]["easting"]
        occupied_z = occupiedpoint["station"]["elevation"]
        utmzone = occupiedpoint["station"]["utmzone"]

    # check that the given instrument height is sane
    instrumentheighterror = tripod._validate_instrument_height(instrument_height)
    if instrumentheighterror:
        outcome["errors"].append(instrumentheighterror)
    else:
        instrument_height = round(instrument_height, 3)

    # stop execution if there were any errors setting the atmospheric conditions, occupied point, or instrument height
    if outcome["errors"]:
        return format_outcome(outcome)

    # set the azimuth on the total station, stopping execution if there are any errors
    degrees, remainder = divmod(azimuth, 1)
    minutes, remainder = divmod(remainder * 100, 1)
    seconds = round(remainder * 100)
    degrees, minutes, seconds = int(degrees), int(minutes), int(seconds)
    setazimuth = totalstation.set_azimuth(degrees, minutes, seconds)  # type: ignore
    if "errors" in setazimuth:
        return format_outcome(setazimuth)

    # start the new session
    azimuthstring = f"{degrees}° {minutes}' {seconds}\""
    data = (
        label,
        surveyor,
        occupied_point_id,
        None,
        None,
        None,
        azimuthstring,
        instrument_height,
        pressure,
        temperature,
    )
    if sessionid := _save_new_session(data):
        tripod.occupied_point = {
            "n": occupied_n,
            "e": occupied_e,
            "z": occupied_z,
            "utmzone": utmzone,
        }
        tripod.instrument_height = instrument_height
        outcome["result"] = f"Azimuth set to {azimuthstring}, and new session started."
    else:
        outcome["errors"].append(
            f"A database error occurred while saving the new session."
        )
    return format_outcome(outcome)


def start_surveying_session_with_backsight(
    label: str,
    surveyor: str,
    sites_id: int,
    occupied_point_id: int,
    backsight_station_id: int,
    prism_height: float,
    temperature: int,
    pressure: int,
) -> dict:
    """This function starts a new surveying session with a backsight to a known point."""

    # check for setup errors, stopping execution if there are any
    setuperrors = database.get_setup_errors()
    if "errors" in setuperrors:
        return setuperrors

    # ensure that the occupied point and backsight station are not the same, stopping execution if they are
    outcome = {"results": "", "errors": []}
    if occupied_point_id == backsight_station_id:
        outcome["errors"] = [
            f"The Occupied Point and Backsight Station are the same (id = {occupied_point_id})."
        ]
        return format_outcome(outcome)

    # set the atmospheric conditions
    outcome = {"result": "", "errors": []}
    atmosphere = set_atmospheric_conditions(temperature, pressure)
    if "errors" in atmosphere:
        outcome["errors"].extend(atmosphere["errors"])

    # set the prism height
    if prism_height < 0:
        outcome["errors"].append(
            f"An invalid prism height ({prism_height}m) was entered."
        )
    else:
        prismoffsets = prism.set_prism_offsets(-prism_height, 0, 0, 0, 0, 0)
        if "errors" in prismoffsets:
            outcome["errors"].extend(prismoffsets["errors"])

    # get the occupied point coordinates
    occupied_n, occupied_e, occupied_z = 0, 0, 0
    occupiedpoint = tripod.get_station(sites_id, occupied_point_id)
    if "errors" in occupiedpoint:
        outcome["errors"].extend(occupiedpoint["errors"])
    else:
        occupied_n = occupiedpoint["station"]["northing"]
        occupied_e = occupiedpoint["station"]["easting"]
        occupied_z = occupiedpoint["station"]["elevation"]
        utmzone = occupiedpoint["station"]["utmzone"]

    # get the backsight station coordinates
    backsight_n, backsight_e, backsight_z = 0, 0, 0
    backsightstation = tripod.get_station(sites_id, backsight_station_id)
    if "errors" in backsightstation:
        outcome["errors"].extend(backsightstation["errors"])
    else:
        backsight_n = backsightstation["station"]["northing"]
        backsight_e = backsightstation["station"]["easting"]
        backsight_z = backsightstation["station"]["elevation"]

    # stop execution if there were any errors setting the atmospheric conditions, occupied point, backsight station, or prism height
    if outcome["errors"]:
        return format_outcome(outcome)

    # set the azimuth on the total station, stopping execution if there are any errors
    degrees, minutes, seconds = calculations._calculate_azimuth(
        (occupied_n, occupied_e), (backsight_n, backsight_e)
    )[1:]
    setazimuth = totalstation.set_azimuth(degrees, minutes, seconds)  # type: ignore
    if "errors" in setazimuth:
        return format_outcome(setazimuth)

    # shoot the backsight, stopping execution if it’s canceled or there are errors
    measurement = totalstation.take_measurement()  # type: ignore
    if "notification" in measurement:
        outcome["result"] = "Backsight shot canceled by user."
        return format_outcome(outcome)
    elif "errors" in measurement:
        outcome["errors"].extend(measurement["errors"])
        return format_outcome(outcome)

    # validate the backsight variance, using fake data so demo mode passes the test
    if totalstation.__name__ == "core.total_stations.demo":
        measurement["measurement"]["delta_n"] = backsight_n - occupied_n
        measurement["measurement"]["delta_e"] = backsight_e - occupied_e
        measurement["measurement"]["delta_z"] = backsight_z - occupied_z
    variance = calculations._calculate_backsight_variance(
        occupied_n,
        occupied_e,
        backsight_n,
        backsight_e,
        measurement["measurement"]["delta_n"],
        measurement["measurement"]["delta_e"],
    )
    if variance >= backsighterrorlimit:
        outcome["errors"].append(
            f"The variance in the distance measured between the Occupied Point and the Backsight Station ({round(variance, 1)}cm) exceeds the limit set in configs.ini ({round(backsighterrorlimit, 1)}cm)."
        )

    # calculate and validate the instrument height, stopping execution if it fails
    instrument_height = (
        prism_height - measurement["measurement"]["delta_z"] + backsight_z - occupied_z
    )
    instrumentheighterror = tripod._validate_instrument_height(instrument_height)
    if instrumentheighterror:
        outcome["errors"].append(instrumentheighterror)
    else:
        instrument_height = round(instrument_height, 3)
    if outcome["errors"]:
        return format_outcome(outcome)

    # start the new session
    azimuthstring = f"{degrees}° {minutes}' {seconds}\""
    data = (
        label,
        surveyor,
        occupied_point_id,
        backsight_station_id,
        None,
        None,
        azimuthstring,
        instrument_height,
        pressure,
        temperature,
    )
    if sessionid := _save_new_session(data):
        tripod.occupied_point = {
            "n": occupied_n,
            "e": occupied_e,
            "z": occupied_z,
            "utmzone": utmzone,
        }
        tripod.instrument_height = instrument_height
        outcome["result"] = (
            f"New session started. Please confirm that the calculated instrument height ({instrument_height}m) and azimuth to the backsight ({azimuthstring}) are correct before proceeding."
        )
    else:
        outcome["errors"].append(
            "A database error occurred while saving the new session."
        )
    return format_outcome(outcome)


def start_surveying_session_with_resection(
    label: str,
    surveyor: str,
    sites_id: int,
    backsight_station_1_id: int,
    backsight_station_2_id: int,
    instrument_height: float,
    temperature: int,
    pressure: int,
) -> dict:
    """
    This function starts a new surveying session by resection with backsights to two
    known points from a setup location with unknown coordinates. From the vantage point
    of the setup station, backsight #1 must be to the left of backsight #2.
    """

    def perform_setup():
        """This function checks all the prerequisites for starting a new session by resection."""
        global resection_instrument_height
        global resection_backsight_1
        global resection_backsight_2
        nonlocal outcome

        # check for setup errors, stopping execution if there are any
        setuperrors = database.get_setup_errors()
        if "errors" in setuperrors:
            return setuperrors["errors"]

        # ensure that backsight stations 1 and 2 not the same, stopping execution if they are
        if backsight_station_1_id == backsight_station_2_id:
            outcome["errors"].append(
                f"The left Backsight Station and right Backsight stations are the same (id = {backsight_station_1_id})."
            )
            return None

        # set the atmospheric conditions
        atmosphere = set_atmospheric_conditions(temperature, pressure)
        if "errors" in atmosphere:
            outcome["errors"].extend(atmosphere["errors"])

        # check that the given instrument height is sane
        instrumentheighterror = tripod._validate_instrument_height(instrument_height)
        if instrumentheighterror:
            outcome["errors"].append(instrumentheighterror)
        else:
            resection_instrument_height = round(instrument_height, 3)

        # get the backsight station 1 and 2 coordinates
        resection_backsight_1 = tripod.get_station(sites_id, backsight_station_1_id)
        if "errors" in resection_backsight_1:
            outcome["errors"].extend(resection_backsight_1["errors"])
        resection_backsight_2 = tripod.get_station(sites_id, backsight_station_2_id)
        if "errors" in resection_backsight_2:
            outcome["errors"].extend(resection_backsight_2["errors"])
        return None

    def take_backsight_1():
        """This function takes the first (left) resection backsight."""
        global resection_backsight_1_measurement
        nonlocal outcome

        # shoot backsight 1, stopping execution if it’s canceled or there are errors
        measurement = totalstation.take_measurement()  # type: ignore
        if "notification" in measurement:
            outcome["result"] = "Backsight shot canceled by user."
        elif "errors" in measurement:
            outcome["errors"].extend(measurement["errors"])
        else:
            resection_backsight_1_measurement = measurement
            outcome["result"] = (
                "Backsight #1 (left) successful. Ready to shoot Backsight #2 (right)."
            )
        return None

    def take_backsight_2():
        """This function takes the second (right) resection backsight and computes the occupied point."""
        global resection_backsight_1
        global resection_backsight_2
        global resection_backsight_1_measurement
        nonlocal outcome
        nonlocal instrument_height
        nonlocal sites_id
        nonlocal backsight_station_1_id

        # retrieve stored values for disabled fields in new session form
        if instrument_height == 0:
            instrument_height = resection_instrument_height
        if sites_id == 0:
            sites_id = resection_backsight_1["station"]["sites_id"]
        if backsight_station_1_id == 0:
            backsight_station_1_id = resection_backsight_1["station"]["id"]

        # shoot backsight 2, stopping execution if it’s canceled or there are errors
        resection_backsight_2_measurement = totalstation.take_measurement()  # type: ignore
        if "notification" in resection_backsight_2_measurement:
            outcome["result"] = "Backsight shot canceled by user."
            return None
        elif "errors" in resection_backsight_2_measurement:
            outcome["errors"].extend(resection_backsight_2_measurement["errors"])
            return None

        # validate the variance between the backsight stations, using fake data so demo mode passes the test
        backsight_z_diff = (
            resection_backsight_1["station"]["elevation"]
            - resection_backsight_2["station"]["elevation"]
        )
        if totalstation.__name__ == "core.total_stations.demo":
            measured_z_diff = backsight_z_diff
        else:
            measured_z_diff = (
                resection_backsight_1_measurement["measurement"]["delta_z"]
                - resection_backsight_2_measurement["measurement"]["delta_z"]
            )
        variance = (backsight_z_diff - measured_z_diff) * 100
        if variance >= backsighterrorlimit:
            outcome["errors"].append(
                f"The measured elevation difference between the Occupied Point and the Backsight Stations ({round(variance, 1)}cm) exceeds the limit set in configs.ini ({round(backsighterrorlimit, 1)}cm)."
            )
            return None

        # calculate the coordinates of the occupied point
        occupied_point_ne_coords = calculations._calculate_coordinates_by_resection(
            (
                resection_backsight_1["station"]["easting"],
                resection_backsight_1["station"]["northing"],
            ),
            (
                resection_backsight_2["station"]["easting"],
                resection_backsight_2["station"]["northing"],
            ),
            math.hypot(
                resection_backsight_1_measurement["measurement"]["delta_e"],
                resection_backsight_1_measurement["measurement"]["delta_n"],
            ),
            math.hypot(
                resection_backsight_2_measurement["measurement"]["delta_e"],
                resection_backsight_2_measurement["measurement"]["delta_n"],
            ),
        )
        occupied_point_elevation = (
            resection_backsight_1["station"]["elevation"]
            - resection_backsight_1_measurement["measurement"]["delta_z"]
            + resection_backsight_2["station"]["elevation"]
            - resection_backsight_2_measurement["measurement"]["delta_z"]
        ) / 2 - instrument_height

        # save the occupied point as a new station in the database, stopping execution on errors
        coordinatesystem = (
            "Site" if not resection_backsight_1["station"]["utmzone"] else "UTM"
        )
        outcome = tripod.save_new_station(
            sites_id,
            f"Free Station ({_get_timestamp()})",
            coordinatesystem,
            {
                "northing": occupied_point_ne_coords[1],
                "easting": occupied_point_ne_coords[0],
                "elevation": occupied_point_elevation,
                "utmzone": resection_backsight_1["station"]["utmzone"],
            },
            "Station set by resection",
        )
        if "errors" in outcome:
            return None

        # set the azimuth on the total station, stopping execution if there are errors
        degrees, minutes, seconds = calculations._calculate_azimuth(
            (occupied_point_ne_coords[1], occupied_point_ne_coords[0]),
            (
                resection_backsight_2["station"]["northing"],
                resection_backsight_2["station"]["easting"],
            ),
        )[1:]
        setazimuth = totalstation.set_azimuth(degrees, minutes, seconds)  # type: ignore
        if "errors" in setazimuth:
            outcome["errors"].extend(setazimuth["errors"])
            return

        # start the new session
        azimuthstring = f"{degrees}° {minutes}' {seconds}\""
        data = (
            label,
            surveyor,
            database.cursor.lastrowid,
            None,
            backsight_station_1_id,
            backsight_station_2_id,
            azimuthstring,
            instrument_height,
            pressure,
            temperature,
        )
        if sessionid := _save_new_session(data):
            tripod.occupied_point = {
                "n": occupied_point_ne_coords[1],
                "e": occupied_point_ne_coords[0],
                "z": occupied_point_elevation,
                "utmzone": resection_backsight_1["station"]["utmzone"],
            }
            tripod.instrument_height = instrument_height
            resection_backsight_1 = {}
            resection_backsight_2 = {}
            resection_backsight_1_measurement = {}
            outcome["result"] = (
                f"New session started. Please confirm that the azimuth to Backsight #2 ({azimuthstring}) is correct before proceeding."
            )
        else:
            outcome["errors"].append(
                f"A database error occurred while saving the new session."
            )

    outcome = {"errors": [], "result": ""}
    if not resection_backsight_1_measurement:
        perform_setup()
        # stop execution if there were any errors setting the atmospheric conditions, instrument height, or backsight 1 or 2
        if not outcome["errors"]:
            take_backsight_1()
    else:
        take_backsight_2()
    return format_outcome(outcome)


def abort_resection() -> dict:
    """This function clears the saved values when a resection has been started, so that the operator can begin fresh."""
    global resection_backsight_1
    global resection_backsight_2
    global resection_backsight_1_measurement
    resection_backsight_1 = {}
    resection_backsight_2 = {}
    resection_backsight_1_measurement = {}
    return {"result": "Resection aborted."}


def end_current_session() -> dict:
    """This function ends the current session."""
    global sessionid
    if "errors" not in end_current_grouping():
        outcome = {"errors": [], "result": ""}
        sessionid = 0
        endcurrentsession = database._save_to_database(
            "UPDATE savedstate SET currentsession = ?", (sessionid,)
        )
        if "errors" in endcurrentsession:
            outcome["errors"] = endcurrentsession["errors"]
        else:
            outcome["result"] = "Session ended."
    return format_outcome(outcome)


def get_all_sessions() -> dict:
    """This function returns basic identifying information about all the sessions in the database."""
    outcome = {"errors": [], "result": ""}
    sql = (
        "SELECT "
        "  sess.id, "
        "  sites.name || '; Started ' || sess.started || ' (' || count(shots.id) || ' shots)' AS description, "
        "  sess.label AS name "
        "FROM sessions sess "
        "LEFT OUTER JOIN stations sta ON sess.stations_id_occupied = sta.id "
        "LEFT OUTER JOIN sites on sta.sites_id = sites.id "
        "LEFT OUTER JOIN groupings grp ON sess.id = grp.sessions_id "
        "LEFT OUTER JOIN shots ON grp.id = shots.groupings_id "
        "GROUP BY sess.id"
    )
    outcome["sessions"] = database._read_from_database(sql)["results"]
    return format_outcome(outcome, ["sessions"])


def get_current_session() -> dict:
    """This function returns information about the current active surveying session."""
    outcome = {"errors": [], "result": ""}
    if sessionid:
        sql = (
            "SELECT "
            "  sess.id, "
            "  sess.label, "
            "  sess.started, "
            "  sites.name AS sites_name, "
            "  sta.name AS stations_name, "
            "  printf('%.3f', sess.instrumentheight) AS instrumentheight "
            "FROM sessions sess "
            "JOIN stations sta ON sess.stations_id_occupied = sta.id "
            "JOIN sites on sta.sites_id = sites.id "
            "WHERE sess.id = ?"
        )
        outcome = database._read_from_database(sql, (sessionid,))["results"][0]
    return format_outcome(outcome)


def export_session_for_livemap(thesession: int = 0) -> dict:
    """This function returns a dictionary of survey data that can be plotted by leafletjs."""
    thesession = thesession or sessionid
    sql = (
        "SELECT "
        "	sessions.label, "
        "	stations.name, "
        "	stations.northing, "
        "	stations.easting, "
        "	stations.latitude, "
        "	stations.longitude, "
        "	stations.utmzone, "
        "	savedstate.currentgrouping "
        "FROM savedstate "
        "LEFT OUTER JOIN sessions ON savedstate.currentsession = sessions.id "
        "LEFT OUTER JOIN stations ON sessions.stations_id_occupied = stations.id "
        "WHERE savedstate.currentsession = ? "
        "LIMIT 1"
    )
    sessioninfo = database._read_from_database(sql, (thesession,))
    if "errors" not in sessioninfo:
        if sessioninfo["results"][0]["name"] is None:
            return {}
        sitelocalcoords = False
        utmzone = sessioninfo["results"][0]["utmzone"]
        lat = sessioninfo["results"][0]["latitude"]
        lon = sessioninfo["results"][0]["longitude"]
        if utmzone is None:
            sitelocalcoords = True
            utmzone = "31N"
            lat, lon = calculations._convert_utm_to_latlon(
                sessioninfo["results"][0]["northing"] + 200000,
                sessioninfo["results"][0]["easting"] + 200000,
                int(utmzone[:-1]),
                utmzone[-1],
            )
        outcome = {
            "occupiedstation": {
                "label": [
                    f"{sessioninfo['results'][0]['label']}",
                    sessioninfo["results"][0]["name"],
                ],
                "sitelocalcoords": sitelocalcoords,
                "coords": [
                    lat,
                    lon,
                ],
            },
            "currentgrouping": sessioninfo["results"][0]["currentgrouping"],
        }
    else:
        return format_outcome(sessioninfo)
    sql = (
        "SELECT "
        "	groupings.id AS groupings_id, "
        "	groupings.geometries_id, "
        "	subclasses.name AS subclass, "
        "	groupings.label, "
        "	shots.northing, "
        "	shots.easting "
        "FROM groupings "
        "JOIN shots ON groupings.id = shots.groupings_id "
        "LEFT OUTER JOIN subclasses ON groupings.subclasses_id = subclasses.id "
        "LEFT OUTER JOIN sessions ON groupings.sessions_id = sessions.id "
        "WHERE groupings.sessions_id = ? "
        "ORDER BY groupings.id"
    )
    surveydata = database._read_from_database(sql, (thesession,))
    if "errors" not in surveydata:
        shots = []
        for each_shot in surveydata["results"]:
            northing = each_shot["northing"]
            easting = each_shot["easting"]
            if sitelocalcoords:
                northing += 200000
                easting += 200000
            lat, lon = calculations._convert_utm_to_latlon(
                northing,
                easting,
                int(utmzone[:-1]),
                utmzone[-1],
            )
            shots.append(
                (
                    each_shot["groupings_id"],
                    each_shot["geometries_id"],
                    [each_shot["subclass"], each_shot["label"]],
                    lat,
                    lon,
                )
            )
        closedpolys = [shot for shot in shots if shot[1] == 4]
        openpolys = [shot for shot in shots if shot[1] == 3]
        leafletpolygons = {}
        for each_shot in closedpolys:
            if each_shot[0] not in leafletpolygons:
                leafletpolygons[each_shot[0]] = {
                    "groupingid": each_shot[0],
                    "label": each_shot[2],
                    "coords": [],
                }
            leafletpolygons[each_shot[0]]["coords"].append([each_shot[3], each_shot[4]])
        leafletpolylines = {}
        for each_shot in openpolys:
            if each_shot[0] not in leafletpolylines:
                leafletpolylines[each_shot[0]] = {
                    "groupingid": each_shot[0],
                    "label": each_shot[2],
                    "coords": [],
                }
            leafletpolylines[each_shot[0]]["coords"].append(
                [each_shot[3], each_shot[4]]
            )
        leafletpoints = []
        for each_shot in shots:
            leafletpoints.append(
                {
                    "groupingid": each_shot[0],
                    "label": each_shot[2],
                    "coords": [each_shot[3], each_shot[4]],
                }
            )
        outcome["polylines"] = list(leafletpolylines.values())
        outcome["polygons"] = list(leafletpolygons.values())
        outcome["points"] = leafletpoints
    else:
        outcome = surveydata
    return format_outcome(outcome, ["polylines", "polygons", "points"])


def delete_session(id: int) -> dict:
    """This function expunges the indicated session from the database."""
    outcome = {"errors": [], "results": ""}
    exists = database._read_from_database(
        "SELECT label FROM sessions WHERE id = ?", (id,)
    )
    if "errors" not in exists:
        if exists[
            "results"
        ]:  # This is an empty list if there are no matches for the above query.
            label = exists["results"][0]["label"]
            groupings = [
                str(x["id"])
                for x in database._read_from_database(
                    "SELECT id FROM groupings WHERE sessions_id = ?", (id,)
                )["results"]
            ]
            shotsdeleted = database._delete_from_database(
                f"DELETE FROM shots WHERE groupings_id in ({','.join(groupings)})", ()
            )
            if "errors" not in shotsdeleted:
                groupingsdeleted = database._delete_from_database(
                    f"DELETE FROM groupings WHERE id in ({','.join(groupings)})", ()
                )
                if "errors" not in groupingsdeleted:
                    sessiondeleted = database._delete_from_database(
                        "DELETE FROM sessions WHERE id = ?", (id,)
                    )
                    if "errors" not in sessiondeleted:
                        outcome["result"] = f"Session “{label}” successfully deleted."
                    else:
                        outcome["errors"].append(sessiondeleted["errors"])
                else:
                    outcome["errors"].append(groupingsdeleted["errors"])
            else:
                outcome["errors"].append(shotsdeleted["errors"])
        else:
            outcome["errors"].append(f"Session id {id} does not exist.")
    else:
        outcome["errors"] = exists["errors"]
    return format_outcome(outcome)


def get_current_grouping() -> dict:
    """This function returns information about the current active point grouping."""
    outcome = {"errors": [], "result": ""}
    if sessionid:
        sql = (
            "SELECT "
            "  grp.id, "
            "  grp.label, "
            "  geo.name AS geometries_name, "
            "  cl.name AS classes_name, "
            "  scl.name AS subclasses_name, "
            "  grp.description, "
            "  count(shots.id) as num_shots "
            "FROM groupings grp "
            "JOIN geometries geo ON grp.geometries_id = geo.id "
            "JOIN subclasses scl ON grp.subclasses_id = scl.id "
            "JOIN classes cl ON scl.classes_id = cl.id "
            "LEFT OUTER JOIN shots ON grp.id = shots.groupings_id "
            "WHERE grp.id = ?"
        )
        outcome = database._read_from_database(sql, (groupingid,))["results"][0]
    return format_outcome(outcome)


def start_new_grouping(
    geometries_id: int,
    subclasses_id: int,
    label: str,
    description: Optional[str] = None,
) -> dict:
    """This function begins recording a grouping of total station measurements."""
    outcome = {"errors": [], "result": ""}
    global groupingid
    if sessionid:
        label = label.strip()
        description = description.strip() if description else None
        sql = (
            "INSERT INTO groupings "
            "(sessions_id, geometries_id, subclasses_id, label, description) "
            "VALUES(?, ?, ?, ?, ?)"
        )
        saved = database._save_to_database(
            sql, (sessionid, geometries_id, subclasses_id, label, description)
        )
        if "errors" not in saved:
            groupingid = database.cursor.lastrowid
            _ = database._save_to_database(
                "UPDATE savedstate SET currentgrouping = ?", (groupingid,)
            )
            outcome["result"] = f"New grouping started."
        else:
            groupingid = 0
            outcome["errors"].append(
                "An error occurred while starting the new grouping."
            )
    else:
        outcome["errors"].append("There is no active surveying session.")
    return format_outcome(outcome)


def end_current_grouping() -> dict:
    """This function ends the current grouping."""
    outcome = {"errors": [], "result": ""}
    global groupingid
    groupingid = 0
    result = database._save_to_database(
        "UPDATE savedstate SET currentgrouping = ?", (groupingid,)
    )
    if "errors" in result:
        outcome["errors"].append("An error occurred while ending the grouping.")
    else:
        outcome["result"] = "Grouping ended."
    return format_outcome(outcome)


def take_shot() -> dict:
    """This function instructs the total station to take a measurement, applies the offsets, and augments it with metadata."""
    outcome = {"errors": [], "result": ""}
    global activeshotdata
    if not sessionid:
        outcome["errors"].append(
            "No shot taken because there is no active surveying session."
        )
    elif not groupingid:
        outcome["errors"].append(
            "No shot taken because there is no active shot grouping."
        )
    else:
        measurement = totalstation.take_measurement()  # type: ignore
        if "notification" in measurement:
            outcome["result"] = measurement["notification"]
        elif "errors" in measurement:
            outcome["errors"] = measurement["errors"]
        else:
            outcome["result"] = calculations._apply_atmospheric_correction(
                measurement["measurement"], pressure, temperature
            )
            outcome["result"] = calculations._apply_offsets_to_measurement(
                measurement["measurement"]
            )
            northing = measurement["measurement"]["calculated_n"]
            easting = measurement["measurement"]["calculated_e"]
            utmzone = tripod.occupied_point["utmzone"]
            if not utmzone:
                northing += 200000
                easting += 200000
                utmzone = "31N"
            outcome["result"]["calculated_lat"], outcome["result"]["calculated_lon"] = (
                calculations._convert_utm_to_latlon(
                    northing,
                    easting,
                    int(utmzone[:-1]),
                    utmzone[-1],
                )
            )
            activeshotdata = outcome["result"]
    return format_outcome(outcome)


def save_last_shot(comment: Optional[str] = None) -> dict:
    """This function saves the data from the last shot to the database."""
    outcome = {"errors": [], "result": ""}
    global groupingid
    global activeshotdata
    if not activeshotdata:
        outcome["errors"].append(
            "Shot not saved because there is no unsaved shot data."
        )
    else:
        comment = comment.strip() if comment else None
        data = (
            activeshotdata["delta_n"],
            activeshotdata["delta_e"],
            activeshotdata["delta_z"],
            activeshotdata["calculated_n"],
            activeshotdata["calculated_e"],
            activeshotdata["calculated_z"],
            pressure,
            temperature,
            prism.offsets["vertical_distance"],
            prism.offsets["latitude_distance"],
            prism.offsets["longitude_distance"],
            prism.offsets["radial_distance"],
            prism.offsets["tangent_distance"],
            prism.offsets["wedge_distance"],
            groupingid,
            comment,
        )
        sql = (
            "INSERT INTO shots "
            "(timestamp, delta_n, delta_e, delta_z, northing, easting, elevation, pressure, temperature, prismoffset_vertical, prismoffset_latitude, prismoffset_longitude, prismoffset_radial, prismoffset_tangent, prismoffset_wedge, groupings_id, comment) "
            f"VALUES('{_get_timestamp()}', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        saved = database._save_to_database(sql, data)
        if "errors" not in saved:
            outcome["result"] = "The last shot was saved."
            newstation = _save_shot_as_new_station()
            if newstation:
                if "errors" in newstation:
                    outcome["errors"].append(newstation["errors"][0])
                else:
                    outcome["result"] = (
                        "The last shot was saved and added to the stations list."
                    )
            activeshotdata = {}
            if (
                database._read_from_database(
                    "SELECT geometries_id FROM groupings WHERE id = ?", (groupingid,)
                )["results"][0]["geometries_id"]
                == 1
            ):
                # The active shot is an isolated point, so end the current grouping
                endcurrentgrouping = end_current_grouping()
                if "errors" in endcurrentgrouping:
                    outcome["errors"].extend(endcurrentgrouping["errors"])
        else:
            outcome["errors"].append("An error occurred while saving the last shot.")
    return format_outcome(outcome)
