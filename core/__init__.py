"""This package controls all aspects of ShootPoints’ communications with the total station and processing and saving data."""

import glob
import importlib
import re
import serial
import serial.tools.list_ports
from pathlib import Path

from . import calculations as calculations
from . import classifications as classifications
from . import database as database
from . import exporters as exporters
from . import prism as prism
from . import sites as sites
from . import survey as survey
from . import tripod as tripod
from .utilities import format_outcome


__version__ = {}
configs = {}
totalstation = None
serialport = None


def _load_saved_state() -> None:
    saved_state = database._read_from_database("SELECT * FROM savedstate")["results"][0]
    prism.offsets = {
        "vertical_distance": saved_state["vertical_distance"],
        "latitude_distance": saved_state["latitude_distance"],
        "longitude_distance": saved_state["longitude_distance"],
        "radial_distance": saved_state["radial_distance"],
        "tangent_distance": saved_state["tangent_distance"],
        "wedge_distance": saved_state["wedge_distance"],
    }
    survey.backsighttolerance_h = configs["backsight_tolerance_h"]
    survey.backsighttolerance_v = configs["backsight_tolerance_v"]
    survey.pressure = saved_state["pressure"]
    survey.temperature = saved_state["temperature"]
    survey.sessionid = saved_state["currentsession"]
    survey.groupingid = saved_state["currentgrouping"]
    sql = (
        "SELECT "
        "  sta.northing AS n, "
        "  sta.easting AS e, "
        "  sta.elevation AS z, "
        "  sta.utmzone AS utmzone, "
        "  sess.instrumentheight AS ih, "
        "  max(grp.id) AS gid "
        "FROM sessions sess "
        "JOIN stations sta ON sess.stations_id_occupied = sta.id "
        "LEFT OUTER JOIN groupings grp ON sess.id = grp.sessions_id "
        "WHERE sess.id = ?"
    )
    session_info = database._read_from_database(sql, (saved_state["currentsession"],))[
        "results"
    ][0]
    tripod.occupied_point = {
        "n": session_info["n"],
        "e": session_info["e"],
        "z": session_info["z"],
        "utmzone": session_info["utmzone"],
    }
    tripod.instrument_height = session_info["ih"]


def _load_total_station_model() -> dict:
    """This function loads the indicated total station."""
    outcome = {"errors": [], "result": ""}
    global totalstation
    if configs["serial_port"] == "demo":
        from .total_stations import demo as totalstation

        outcome["result"] = "Demo total station loaded."
    else:
        make = configs["totalstation_make"].replace(" ", "_").lower()
        make = make.replace("-", "_").lower()
        model = configs["totalstation_model"].replace(" ", "_").lower()
        model = model.replace("-", "_").lower()
        # All Topcon GTS-300 series total stations use the same communications protocols.
        if make == "topcon" and model[:6] == "gts_30":
            model = "gts_300_series"
        try:
            totalstation = importlib.import_module(
                f"{__name__}.total_stations.{make}.{model}", package="core"
            )
            outcome["result"] = (
                f"{configs['totalstation_make']} {configs['totalstation_model']} total station loaded."
            )
        except ModuleNotFoundError:
            error = f"There is no module for the {make} {model} total station. Specify the correct total station make and model in Setup > Set Configs before proceeding."
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
    if configs["serial_port"] != "demo" and not outcome["errors"]:
        serialport = configs["serial_port"]
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
        except serial.SerialException:
            outcome["errors"].append(
                f"Serial port {serialport} could not be opened. Check your serial cable connections, refresh this page, and re-select the proper port in Setup > Set Configs before proceeding."
            )
    for each in outcome["errors"]:
        database._record_setup_error(each)
    return format_outcome(outcome)


def _load_application() -> dict:
    """This function runs the private loader functions (above) and clears setup errors if they run cleanly."""
    outcome = {"errors": [], "results": []}
    global __version__
    global configs
    database._clear_setup_errors()
    with open("../VERSION", "r") as f:
        __version__ = {
            "app": f.readline().strip().split("=")[1],
            "database": f.readline().strip().split("=")[1],
        }
        print(
            f"ShootPoints-Web v{__version__['app']}\nDatabase v{__version__['database']}"
        )
    database.latestversion = int(__version__["database"])
    dbupgrade = database._upgrade_database()
    if "result" in dbupgrade:
        print(dbupgrade["result"])
    elif "errors" in dbupgrade:
        outcome["errors"].append(dbupgrade["errors"])
    configs = database._read_from_database("SELECT * FROM configs")["results"][0]
    loaders = [
        _load_total_station_model,
        _load_serial_port,
    ]
    for each in loaders:
        loaderoutcome = each()
        if "result" in loaderoutcome:
            outcome["results"].append(loaderoutcome["result"])
        elif "errors" in loaderoutcome:
            outcome["errors"].extend(loaderoutcome["errors"])
    if len(outcome["errors"]) == 0:
        database._clear_setup_errors()
    _load_saved_state()
    return format_outcome(outcome)


def get_configs() -> dict:
    """
    This function gets the current configs so that the application front-end
    can display them. It also finds the available ports and total station
    models for the configs, so that the application front-end can provide
    sensible choices to the user.
    """
    sql = (
        "SELECT"
        "  serial_port AS port, "
        "  serial_uart AS uart, "
        "  totalstation_make AS make, "
        "  totalstation_model AS model, "
        "  backsight_tolerance_h AS tolerance_h, "
        "  backsight_tolerance_v AS tolerance_v "
        "FROM configs"
    )
    currentconfigs = database._read_from_database(sql)["results"][0]
    ports = ["demo"]
    for port in list(serial.tools.list_ports.comports()):
        if (
            # USB to Serial adapter on Raspberry Pi
            re.fullmatch("/dev/ttyUSB\\d+", port[0])
            # USB to Serial adapter on Mac
            or re.fullmatch("/dev/cu.usbserial-\\d+", port[0])
            # USB to Serial adapter on Windows
            or re.fullmatch("COM\\d+", port[0])
        ):
            ports.append(port[0])
        # GPIO UART adapter on Raspberry Pi
        if configs["serial_uart"] and re.fullmatch("/dev/ttyAMA\\d+", port[0]):
            ports.append(port[0])
    makes = list(glob.glob(str(Path("core") / "total_stations" / "*")))
    makes.sort()
    models = {}
    for eachmake in makes:
        themodels = list(
            set(glob.glob(str(Path(eachmake) / "*.py")))
            - set(glob.glob(str(Path(eachmake) / "__init__.py")))
        )
        themodels.sort()
        models[eachmake.replace("\\", "/").split("/")[2].replace("_", " ").title()] = [
            x.replace("\\", "/")
            .split("/")[3]
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


def save_configs(
    port: str = "",
    make: str = "",
    model: str = "",
    tolerance_h: float = 0,
    tolerance_v: float = 0,
) -> dict:
    """
    This function creates saves the app configs to the database. Any parameters
    not passed when this function is called will stay at their current settings.
    """
    sqlfields = []
    configstoupate = []
    if port:
        sqlfields.append("serial_port = ?")
        configstoupate.append(port)
    if make:
        sqlfields.append("totalstation_make = ?")
        configstoupate.append(make)
    if model:
        sqlfields.append("totalstation_model = ?")
        configstoupate.append(model)
    if tolerance_h:
        sqlfields.append("backsight_tolerance_h = ?")
        configstoupate.append(tolerance_h)
    if tolerance_v:
        sqlfields.append("backsight_tolerance_v = ?")
        configstoupate.append(tolerance_v)
    sql = f"UPDATE configs SET {', '.join(sqlfields)}"
    database._save_to_database(sql, tuple(configstoupate))
    outcome = _load_application()
    if "errors" not in outcome:
        del outcome["results"]
        outcome["result"] = "Configurations saved and reloaded."
    return format_outcome(outcome)


print(_load_application())
