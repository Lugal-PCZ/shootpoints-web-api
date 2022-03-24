"""This package controls all aspects of ShootPoints’ communications with the total station and processing and saving data."""

import configparser
import shutil
import glob
import importlib
from datetime import datetime
import serial


from . import calculations
from . import classifications
from . import database
from . import prism
from . import sites
from . import survey
from . import tripod


configs = None
totalstation = None
serialport = None


def _check_system_date() -> None:
    """
    This function halts execution if the sytem date is unrealistic,
    as can easily happen with a Raspberry Pi without a clock module
    and no internet connection.
    """
    if datetime.now() < datetime(2020, 6, 17):
        exit(
            f'FATAL ERROR: Your system date ({datetime.strftime(datetime.now(), "%B %-d, %Y")}) is not set correctly. Fix this in your OS before proceeding.'
        )


def _load_configs_from_file() -> dict:
    """
    This function loads the configurations from the configs.ini file.
    If that file doesn't exist, it creates one from configs.ini.example.
    """
    outcome = {"errors": [], "result": ""}
    global configs
    configs = configparser.ConfigParser()
    try:
        with open("configs.ini", "r") as f:
            pass
    except FileNotFoundError:
        shutil.copy("configs.ini.example", "configs.ini")
    configs.read("configs.ini")
    if configs.sections():
        outcome["result"] = "Configurations loaded successfully."
    else:
        configs.read("configs.ini.example")
        with open("configs.ini", "w") as f:
            configs.write(f)
        error = "The config.ini file was not found, so one was created from the example file. Update your configs before proceeding."
        outcome["errors"].append(error)
        database._record_setup_error(error)
    survey.backsighterrorlimit = configs["BACKSIGHT ERROR"]["limit"]
    return {key: val for key, val in outcome.items() if val}


def _load_total_station_model() -> dict:
    """This function loads the indicated total station."""
    outcome = {"errors": [], "result": ""}
    global totalstation
    if configs["SERIAL"]["port"] == "demo":
        from .total_stations import demo as totalstation

        outcome["result"] = "Demo total station loaded."
    else:
        make = configs["TOTAL STATION"]["make"].replace(" ", "_").lower()
        make = make.replace("-", "_").lower()
        model = configs["TOTAL STATION"]["model"].replace(" ", "_").lower()
        model = model.replace("-", "_").lower()
        # All Topcon GTS-300 series total stations use the same communications protocols.
        if make == "topcon" and model[:6] == "gts_30":
            model = "gts_300_series"
        try:
            totalstation = importlib.import_module(
                f"{__name__}.total_stations.{make}.{model}", package="core"
            )
            outcome[
                "result"
            ] = f"{configs['TOTAL STATION']['make']} {configs['TOTAL STATION']['model']} total station loaded."
        except ModuleNotFoundError:
            error = f"File total_stations/{make}/{model}.py does not exist. Specify the correct total station make and model in configs.ini before proceeding."
            outcome["errors"].append(error)
            database._record_setup_error(error)
    if not outcome["errors"]:
        survey.totalstation = totalstation
    return {key: val for key, val in outcome.items() if val}


def _load_serial_port() -> dict:
    """
    This function finds the appropriate serial port and initializes it
    with the communication parameters for the total station model.
    """
    outcome = {"errors": [], "result": ""}
    global serialport
    if configs["SERIAL"]["port"] == "demo":
        outcome[
            "result"
        ] = "Demo total station loaded, so no physical serial port initialized."
    elif configs["SERIAL"]["port"] == "auto":
        if glob.glob("/dev/ttyUSB*"):  # Linux with USB adapter
            serialport = glob.glob("/dev/ttyUSB*")[0]
        elif glob.glob("/dev/ttyAMA*"):  # Linux with RS232 adapter
            serialport = glob.glob("/dev/ttyAMA*")[0]
        elif glob.glob("/dev/cu.usbserial*"):  # Mac with USB adapter
            serialport = glob.glob("/dev/cu.usbserial*")[0]
        else:  # Serial port not found.
            outcome["errors"].append(
                "No valid serial port found. Specify the correct serial port in configs.ini before proceeding."
            )
    else:  # Port is specified explicitly in configs.ini file.
        serialport = configs["SERIAL"]["port"]
    if configs["SERIAL"]["port"] != "demo" and not outcome["errors"]:
        try:
            port = serial.Serial(
                port=serialport,
                baudrate=totalstation.BAUDRATE,
                parity=totalstation.PARITY,
                bytesize=totalstation.BYTESIZE,
                stopbits=totalstation.STOPBITS,
                timeout=totalstation.TIMEOUT,
            )
            totalstation.port = port
            outcome["result"] = f"Serial port {serialport} opened."
        except:
            outcome["errors"].append(
                f"Serial port {serialport} could not be opened. Check your serial adapter and cable connections before proceeding"
            )
    for each in outcome["errors"]:
        database._record_setup_error(each)
    return {key: val for key, val in outcome.items() if val}


def _load_application() -> dict:
    """This function runs the private loader funtions (above) and clears setup errors if they run cleanly."""
    outcome = {"errors": [], "results": []}
    _check_system_date()
    if (
        not configs
    ):  # This app is being loaded fresh or reloaded, so check to see if there's current state saved in the database, and use that to set the module variables.
        try:
            saved_state = database.read_from_database("SELECT * FROM savedstate")[
                "results"
            ][0]
            prism.offsets = {
                "vertical_distance": saved_state["vertical_distance"],
                "latitude_distance": saved_state["latitude_distance"],
                "longitude_distance": saved_state["longitude_distance"],
                "radial_distance": saved_state["radial_distance"],
                "tangent_distance": saved_state["tangent_distance"],
                "wedge_distance": saved_state["wedge_distance"],
            }
            survey.pressure = saved_state["pressure"]
            survey.temperature = saved_state["temperature"]
            survey.sessionid = database.read_from_database(
                "SELECT id FROM sessions ORDER BY started DESC LIMIT 1"
            )["results"][0]["id"]
            sql = (
                "SELECT "
                "  sta.northing AS n, "
                "  sta.easting AS e, "
                "  sta.elevation AS z, "
                "  sess.instrumentheight AS ih, "
                "  max(grp.id) AS gid "
                "FROM sessions sess "
                "JOIN stations sta ON sess.stations_id_occupied = sta.id "
                "LEFT OUTER JOIN groupings grp ON sess.id = grp.sessions_id "
                "WHERE sess.id = ?"
            )
            session_info = database.read_from_database(sql, (survey.sessionid,))[
                "results"
            ][0]
            tripod.occupied_point = {
                "n": session_info["n"],
                "e": session_info["e"],
                "z": session_info["z"],
            }
            tripod.instrument_height = session_info["ih"]
            survey.groupingid = session_info["gid"]
        except:
            pass
    loaders = [_load_configs_from_file, _load_total_station_model, _load_serial_port]
    for each in loaders:
        loaderoutcome = each()
        if "result" in loaderoutcome:
            outcome["results"].append(loaderoutcome["result"])
        elif "errors" in loaderoutcome:
            outcome["errors"].extend(loaderoutcome["errors"])
    if len(outcome["errors"]) == 0:
        database._clear_setup_errors()
    return {key: val for key, val in outcome.items() if val}


def save_config_file(
    port: str = "", make: str = "", model: str = "", limit: int = 0
) -> dict:
    """
    This function creates the configs.ini and sets its values. Any parameters not passed
    when this function is called will stay what they currently are in the config.ini file.
    """
    if port:
        configs["SERIAL"]["port"] = port
    if make:
        configs["TOTAL STATION"]["make"] = make
    if model:
        configs["TOTAL STATION"]["model"] = model
    if limit:
        configs["BACKSIGHT ERROR"]["limit"] = str(limit)
    with open("configs.ini", "w") as f:
        configs.write(f)
    outcome = _load_application()
    if "errors" not in outcome:
        del outcome["results"]
        outcome["result"] = "Configurations saved and reloaded."
    return {key: val for key, val in outcome.items() if val}


# def summarize_current_state() -> dict:
#     """
#     This function returns the state of the global variables and
#     summary data from the ShootPoints database.
#     """
#     summary = {
#         "current_time": datetime.strftime(datetime.now(), "%-I:%M %p, %A %B %-d, %Y"),
#         "setup_errors": None,
#         "serial_port": None,
#         "total_station": None,
#         "atmospheric_conditions": survey.get_atmospheric_conditions(),
#         "prism_offsets": None,
#         "num_sessions_in_db": 0,
#         "current_session": None,
#         "num_points_in_current_session": None,
#         "current_grouping_id": None,
#         "num_points_in_current_grouping": None,
#     }
#     setuperrors = database.get_setup_errors()
#     if setuperrors:
#         summary["setup_errors"] = setuperrors
#     if configs["SERIAL"]["port"] == "demo":
#         summary["total_station"] = "demo"
#     elif serialport:
#         summary["serial_port"] = configs["SERIAL"]["port"]
#         if totalstation:
#             summary[
#                 "total_station"
#             ] = f"{configs['TOTAL STATION']['make']} {configs['TOTAL STATION']['model']}"
#     if prism.get_readable_prism_offsets()["offsets"]:
#         summary["prism_offsets"] = prism.get_readable_prism_offsets()["offsets"]
#     summary["num_sessions_in_db"] = database.read_from_database(
#         "SELECT count(*) FROM sessions"
#     )["results"][0]["count(*)"]
#     sql = (
#         "SELECT "
#         "  sess.id, "
#         "  sess.label, "
#         "  sess.started, "
#         "  sess.stations_id_occupied, "
#         "  sta.northing, "
#         "  sta.easting, "
#         "  sta.elevation, "
#         "  sess.instrumentheight "
#         "FROM sessions sess "
#         "JOIN stations sta ON sess.stations_id_occupied = sta.id "
#         "WHERE sess.id = ?"
#     )
#     try:
#         summary["current_session"] = database.read_from_database(
#             sql, (survey.sessionid,)
#         )["results"][0]
#         summary["num_points_in_current_session"] = database.read_from_database(
#             "SELECT count(*) FROM shots sh JOIN groupings grp ON sh.groupings_id = grp.id WHERE grp.sessions_id = ?",
#             (survey.sessionid,),
#         )["results"][0]["count(*)"]
#         summary["current_grouping_id"] = survey.groupingid
#         summary["num_points_in_current_grouping"] = database.read_from_database(
#             "SELECT count(*) FROM shots sh JOIN groupings grp ON sh.groupings_id = grp.id WHERE grp.id = ?",
#             (survey.groupingid,),
#         )["results"][0]["count(*)"]
#     except:
#         pass
#     return summary


print(_load_application())
