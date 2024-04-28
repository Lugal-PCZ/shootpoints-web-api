"""This package controls all aspects of ShootPoints’ communications with the total station and processing and saving data."""

import configparser
import shutil
import glob
import importlib
import serial

from . import calculations
from . import classifications
from . import database
from . import exporters
from . import prism
from . import sites
from . import survey
from . import tripod
from .utilities import format_outcome


configs = {}
totalstation = None
serialport = None


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
    survey.backsighterrorlimit = float(configs["BACKSIGHT ERROR"]["limit"])
    return format_outcome(outcome)


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
            outcome["result"] = (
                f"{configs['TOTAL STATION']['make']} {configs['TOTAL STATION']['model']} total station loaded."
            )
        except ModuleNotFoundError:
            error = f"File total_stations/{make}/{model}.py does not exist. Specify the correct total station make and model in configs.ini before proceeding."
            outcome["errors"].append(error)
            database._record_setup_error(error)
    if not outcome["errors"]:
        survey.totalstation = totalstation
    return format_outcome(outcome)


def _load_serial_port() -> dict:
    """
    This function finds the appropriate serial port and initializes it
    with the communication parameters for the total station model.
    """
    outcome = {"errors": [], "result": ""}
    global serialport
    if configs["SERIAL"]["port"] == "demo":
        outcome["result"] = (
            "Demo total station loaded, so no physical serial port initialized."
        )
    else:
        serialport = configs["SERIAL"]["port"]
    if configs["SERIAL"]["port"] != "demo" and not outcome["errors"]:
        try:
            port = serial.Serial(
                port=serialport,
                baudrate=totalstation.BAUDRATE,  # type: ignore
                parity=totalstation.PARITY,  # type: ignore
                bytesize=totalstation.BYTESIZE,  # type: ignore
                stopbits=totalstation.STOPBITS,  # type: ignore
                timeout=totalstation.TIMEOUT,  # type: ignore
            )
            totalstation.port = port  # type: ignore
            outcome["result"] = f"Serial port {serialport} opened."
        except:
            outcome["errors"].append(
                f"Serial port {serialport} could not be opened. Check your serial adapter and cable connections before proceeding."
            )
    for each in outcome["errors"]:
        database._record_setup_error(each)
    return format_outcome(outcome)


def _load_application() -> dict:
    """This function runs the private loader functions (above) and clears setup errors if they run cleanly."""
    outcome = {"errors": [], "results": []}
    if (
        not configs
    ):  # This app is being loaded fresh or reloaded, so check to see if there's current state saved in the database, and use that to set the module variables.
        try:
            saved_state = database._read_from_database("SELECT * FROM savedstate")[
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
            survey.sessionid = saved_state["currentsession"]
            survey.groupingid = saved_state["currentgrouping"]
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
            session_info = database._read_from_database(
                sql, (saved_state["currentsession"],)
            )["results"][0]
            tripod.occupied_point = {
                "n": session_info["n"],
                "e": session_info["e"],
                "z": session_info["z"],
            }
            tripod.instrument_height = session_info["ih"]
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
    return format_outcome(outcome)


def get_configs() -> dict:
    """
    This function gets the current settings of the configs.ini file, so that the
    application front-end can display them. It also finds the available ports
    and total station models for the config file, so that the application
    front-end can provide sensible choices to the end user.
    """
    currentconfigs = {}
    for eachsection in configs.sections():  # type: ignore
        for eachoption in configs.items(eachsection):  # type: ignore
            currentconfigs[eachoption[0]] = eachoption[1]
    ports = ["demo"]
    ports.extend(glob.glob("/dev/ttyUSB*"))
    ports.extend(glob.glob("/dev/ttyAMA*"))
    ports.extend(glob.glob("/dev/cu.usbserial*"))
    makes = list(
        set(glob.glob("core/total_stations/*"))
        - set(glob.glob("core/total_stations/_*"))
        - set(["core/total_stations/demo.py"])
    )
    makes.sort()
    models = {}
    for eachmake in makes:
        themodels = list(
            set(glob.glob(f"{eachmake}/*.py")) - set(glob.glob(f"{eachmake}/_*"))
        )
        themodels.sort()
        models[eachmake.split("/")[2].replace("_", " ").title()] = [
            x.split("/")[3]
            .replace(".py", "")
            .replace("_", " ")
            .title()
            .replace("Gts ", "GTS-")
            for x in themodels
        ]
    options = {
        "ports": ports,
        "total_stations": {key: val for key, val in models.items() if len(val) > 0},
    }
    return {"current": currentconfigs, "options": options}


def save_config_file(
    port: str = "", make: str = "", model: str = "", limit: float = 0
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
        configs.write(f)  # type: ignore
    outcome = _load_application()
    if "errors" not in outcome:
        del outcome["results"]
        outcome["result"] = "Configurations saved and reloaded."
    return format_outcome(outcome)


print(_load_application())
