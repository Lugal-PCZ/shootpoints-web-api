"""This module contains functions for handling the surveying session and associated data."""

from . import database
from . import calculations
from . import tripod
from . import prism


SESSIONTYPES = ["Backsight", "Azimuth"]

backsighterrorlimit = 0.0
totalstation = None
sessionid = 0
groupingid = 0
activeshotdata = {}
activeshotlabel = ""
pressure = 760
temperature = 15


def _save_new_session(data: tuple) -> int:
    """This function saves the surveying session information to the database."""
    global sessionid
    global groupingid
    global activeshotdata
    global activeshotlabel
    sql = (
        "INSERT INTO sessions "
        "(label, started, surveyor, stations_id_occupied, stations_id_backsight, azimuth, instrumentheight) "
        "VALUES(?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)"
    )
    saved = database.save_to_database(sql, data)
    if "errors" not in saved:
        sessionid = database.cursor.lastrowid
    else:
        sessionid = 0
    groupingid = 0
    activeshotdata = {}
    activeshotlabel = ""
    return sessionid


def _save_new_station() -> dict:
    """This function checks if the last shot was a survey station, and if so saves it to the stations database table."""
    outcome = None
    currentgrouping = database.read_from_database(
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
        occupiedstation = database.read_from_database(sql, (sessionid,))["results"][0]
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


def get_geometries() -> list:
    """This function returns the types of geometry saved in the database, for use by the application front end."""
    outcome = {"errors": [], "sites": {}}
    query = database.read_from_database("SELECT * FROM geometry")
    if "errors" not in query:
        outcome["geometries"] = query["results"]
    return {key: val for key, val in outcome.items() if val or key == "geometries"}


def get_atmospheric_conditions() -> dict:
    """This function returns the current air pressure and temperature, as most recently set by the surveyor."""
    return {"pressure": pressure, "temperature": temperature}


def set_atmospheric_conditions(temp: int, press: int) -> dict:
    """This function sets the current air pressure and temperature, for correcting the raw total station measurements."""
    outcome = {"errors": [], "result": ""}
    global temperature
    global pressure
    try:
        if not 720 <= int(press) <= 800:
            outcome["errors"].append(
                f"The value given for atmospheric pressure ({press}mmHg) is outside the normal range (720mmHg to 800mmHg)."
            )
    except ValueError:
        outcome["errors"].append(
            f"The value given for atmospheric pressure ({press}) is not numeric."
        )
    try:
        if not -10 <= int(temp) <= 40:
            outcome["errors"].append(
                f"The value given for air temperature ({temp}°C) is outside reasonable limits (-10°C to 40°C)."
            )
    except ValueError:
        outcome["errors"].append(
            f"The value given for air temperature ({temp}) is not numeric."
        )
    if not outcome["errors"]:
        sql = "UPDATE savedstate SET pressure = ?, temperature = ?"
        database.save_to_database(sql, (press, temp))
        pressure = press
        temperature = temp
        outcome[
            "result"
        ] = f"Ambient temperature is now set to {temp}°C and atmospheric pressure is now set to {press}mmHg."
    return {key: val for key, val in outcome.items() if val}


def start_surveying_session_with_backsight(
    label: str,
    surveyor: str,
    sites_id: int,
    occupied_point_id: int,
    backsight_station_id: int,
    prism_height: float,
) -> dict:
    """This function starts a new surveying session with a backsight to a known point."""
    outcome = {"errors": database.get_setup_errors(), "result": ""}
    if not outcome["errors"]:
        if occupied_point_id == backsight_station_id:
            outcome["errors"].append(
                f"The Occupied Point and Backsight Station are the same (id = {occupied_point_id})."
            )
        occupiedpoint = tripod.get_station(sites_id, occupied_point_id)
        if "errors" not in occupiedpoint:
            occupied_n = occupiedpoint["station"]["northing"]
            occupied_e = occupiedpoint["station"]["easting"]
            occupied_z = occupiedpoint["station"]["elevation"]
        else:
            outcome["errors"].extend(occupiedpoint["errors"])
        backsightstation = tripod.get_station(sites_id, backsight_station_id)
        if "errors" not in backsightstation:
            backsight_n = backsightstation["station"]["northing"]
            backsight_e = backsightstation["station"]["easting"]
            backsight_z = backsightstation["station"]["elevation"]
        else:
            outcome["errors"].extend(backsightstation["errors"])
        if prism_height < 0:
            outcome["errors"].append(
                f"An invalid prism height ({prism_height}m) was entered."
            )
        if not outcome["errors"]:
            azimuth = calculations._calculate_azimuth(
                (occupied_n, occupied_e), (backsight_n, backsight_e)
            )
            degrees, remainder = divmod(azimuth, 1)
            minutes, remainder = divmod(remainder * 60, 1)
            seconds = round(remainder * 60)
            degrees, minutes, seconds = int(degrees), int(minutes), int(seconds)
            setazimuth = totalstation.set_azimuth(degrees, minutes, seconds)
            if "errors" not in setazimuth:
                measurement = totalstation.take_measurement()
                if "errors" not in measurement:
                    variance = calculations._calculate_backsight_variance(
                        occupied_n,
                        occupied_e,
                        backsight_n,
                        backsight_e,
                        measurement["measurement"]["delta_n"],
                        measurement["measurement"]["delta_e"],
                    )
                    if variance >= float(backsighterrorlimit):
                        outcome["errors"].append(
                            f"The measured distance between the Occupied Point and the Backsight Station ({variance}cm) exceeds the limit set in configs.ini ({backsighterrorlimit}cm)."
                        )
                    elev_diff_of_points = occupied_z - backsight_z
                    delta_z_to_point = (
                        measurement["measurement"]["delta_z"] - prism_height
                    )
                    instrument_height = elev_diff_of_points + delta_z_to_point
                    tripod._validate_instrument_height(
                        instrument_height, outcome["errors"]
                    )
                else:
                    outcome["errors"].extend(measurement["errors"])
            else:
                outcome["errors"].extend(setazimuth["errors"])
        if not outcome["errors"]:
            data = (
                label,
                surveyor,
                occupied_point_id,
                backsight_station_id,
                f"{degrees}° {minutes}' {seconds}\"",
                instrument_height,
            )
            if sessionid := _save_new_session(data):
                tripod.occupied_point = {
                    "n": occupied_n,
                    "e": occupied_e,
                    "z": occupied_z,
                }
                tripod.instrument_height = instrument_height
                newoffsets = {each_offset: 0 for each_offset in prism.offsets}
                newoffsets["vertical_distance"] = prism_height * -1
                prism.set_prism_offsets(**newoffsets)
                outcome[
                    "result"
                ] = f"New session started. Please confirm that the measured instrument height ({instrument_height}m) is accurate before proceeding."
            else:
                outcome["errors"].append(
                    "A problem occurred while saving the new session to the database."
                )
    return {key: val for key, val in outcome.items() if val}


def start_surveying_session_with_azimuth(
    label: str,
    surveyor: str,
    sites_id: int,
    occupied_point_id: int,
    instrument_height: float,
    azimuth: float,
) -> dict:
    """This function starts a new surveying session with an azimuth to a landmark."""
    outcome = {"errors": database.get_setup_errors(), "result": ""}
    if not outcome["errors"]:
        occupiedpoint = tripod.get_station(sites_id, occupied_point_id)
        if "errors" not in occupiedpoint:
            occupied_n = occupiedpoint["station"]["northing"]
            occupied_e = occupiedpoint["station"]["easting"]
            occupied_z = occupiedpoint["station"]["elevation"]
        else:
            outcome["errors"].extend(occupiedpoint["errors"])
        if not outcome["errors"]:
            degrees, remainder = divmod(azimuth, 1)
            minutes, remainder = divmod(remainder * 100, 1)
            seconds = round(remainder * 100)
            degrees, minutes, seconds = int(degrees), int(minutes), int(seconds)
            setazimuth = totalstation.set_azimuth(degrees, minutes, seconds)
            if "errors" not in setazimuth:
                data = (
                    label,
                    surveyor,
                    occupied_point_id,
                    None,  # There is no backsight station in this setup, but _save_new_session() expects a value.
                    f"{degrees}° {minutes}' {seconds}\"",
                    instrument_height,
                )
                if sessionid := _save_new_session(data):
                    tripod.occupied_point = {
                        "n": occupied_n,
                        "e": occupied_e,
                        "z": occupied_z,
                    }
                    tripod.instrument_height = instrument_height
                    outcome["result"] = f"New session started."
                else:
                    outcome["errors"].append(
                        f"A problem occurred while saving the new session to the database."
                    )
            else:
                outcome["errors"].extend(setazimuth["errors"])
    return {key: val for key, val in outcome.items() if val}


def get_current_session() -> dict:
    """This function returns information about the current active surveying session."""
    outcome = {"errors": [], "result": ""}
    if sessionid:
        sql = (
            "SELECT "
            "  sess.label, "
            "  sess.started, "
            "  sites.name AS sites_name, "
            "  sta.name AS stations_name, "
            "  printf('%.2f', sess.instrumentheight) AS instrumentheight "
            "FROM sessions sess "
            "JOIN stations sta ON sess.stations_id_occupied = sta.id "
            "JOIN sites on sta.sites_id = sites.id "
            "WHERE sess.id = ?"
        )
        outcome = database.read_from_database(sql, (sessionid,))["results"][0]
    return {key: val for key, val in outcome.items()}


def get_current_grouping() -> dict:
    """This function returns information about the current active point grouping."""
    outcome = {"errors": [], "result": ""}
    if sessionid:
        sql = (
            "SELECT "
            "  grp.label, "
            "  geo.name AS geometry_name, "
            "  cl.name AS classes_name, "
            "  scl.name AS subclasses_name, "
            "  grp.description, "
            "  count(shots.id) as num_shots "
            "FROM groupings grp "
            "JOIN geometry geo ON grp.geometry_id = geo.id "
            "JOIN subclasses scl ON grp.subclasses_id = scl.id "
            "JOIN classes cl ON scl.classes_id = cl.id "
            "LEFT OUTER JOIN shots ON grp.id = shots.groupings_id "
            "WHERE grp.id = ?"
        )
        outcome = database.read_from_database(sql, (groupingid,))["results"][0]
    return {key: val for key, val in outcome.items()}


def start_new_grouping(
    geometry_id: int, subclasses_id: int, label: str, description: str = None
) -> dict:
    """This function begins recording a grouping of total station measurements."""
    outcome = {"errors": [], "result": ""}
    global groupingid
    if sessionid:
        label = label.strip() if label else None
        description = description.strip() if description else None
        sql = (
            "INSERT INTO groupings "
            "(sessions_id, geometry_id, subclasses_id, label, description) "
            "VALUES(?, ?, ?, ?, ?)"
        )
        saved = database.save_to_database(
            sql, (sessionid, geometry_id, subclasses_id, label, description)
        )
        if "errors" not in saved:
            groupingid = database.cursor.lastrowid
            outcome["result"] = f"New grouping started."
        else:
            groupingid = 0
            outcome["errors"].append(
                "An error occurred while starting the new grouping."
            )
    else:
        outcome["errors"].append("There is no active surveying session.")
    return {key: val for key, val in outcome.items() if val}


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
        measurement = totalstation.take_measurement()
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
            activeshotdata = outcome["result"]
    return {key: val for key, val in outcome.items() if val}


def save_last_shot(label: str = None, comment: str = None) -> dict:
    """This function saves the data from the last shot to the database.

    Note: isolated points (geometry_id = 1) should only have the label and description
    applied to the grouping, and not for the shot.
    """
    outcome = {"errors": [], "result": ""}
    global groupingid
    global activeshotdata
    global activeshotlabel
    if not activeshotdata:
        outcome["errors"].append(
            "Shot not saved because there is no unsaved shot data."
        )
    else:
        label = label.strip() if label else None
        comment = comment.strip() if comment else None
        if (
            database.read_from_database(
                "SELECT geometry_id FROM groupings WHERE id = ?", (groupingid,)
            )["results"][0]["geometry_id"]
            == 1
        ):
            label = None  # Set label to None, if this is an isolated point.
            comment = None  # Set comment to None, if this is an isolated point.
        data = (
            activeshotdata["delta_n"],
            activeshotdata["delta_e"],
            activeshotdata["delta_z"],
            activeshotdata["calculated_n"],
            activeshotdata["calculated_e"],
            activeshotdata["calculated_z"],
            prism.offsets["vertical_distance"],
            prism.offsets["latitude_distance"],
            prism.offsets["longitude_distance"],
            prism.offsets["radial_distance"],
            prism.offsets["tangent_distance"],
            prism.offsets["wedge_distance"],
            groupingid,
            label,
            comment,
        )
        sql = (
            "INSERT INTO shots "
            "(timestamp, delta_n, delta_e, delta_z, northing, easting, elevation, prismoffset_vertical, prismoffset_latitude, prismoffset_longitude, prismoffset_radial, prismoffset_tangent, prismoffset_wedge, groupings_id, label, comment) "
            "VALUES(CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        saved = database.save_to_database(sql, data)
        if "errors" not in saved:
            outcome[
                "result"
            ] = "The last shot was saved to the shots table in the database."
            newstation = _save_new_station()
            if "errors" in newstation:
                outcome["errors"].append(newstation["errors"][0])
            else:
                outcome[
                    "result"
                ] = "The last shot was saved to the database and added to the stations table."
            activeshotdata = {}
            activeshotlabel = label  # Note: this is so that when a group like topo points is being shot, each shot label can be pre-populated on the front-end.
            if (
                database.read_from_database(
                    "SELECT geometry_id FROM groupings WHERE id = ?", (groupingid,)
                )["results"][0]["geometry_id"]
                == 1
            ):
                groupingid = 0  # The active shot is an isolated point, so reset the groupingid to 0
        else:
            outcome["errors"].append("An error occurred while saving the last shot.")
    return {key: val for key, val in outcome.items() if val}
