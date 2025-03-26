"""This package controls all aspects of ShootPoints’ communications with the total station and processing and saving data."""

import configparser
import glob
import importlib
import re
import serial
import serial.tools.list_ports
from pathlib import Path

from . import calculations
from . import classifications
from . import database
from . import exporters
from . import prism
from . import sites
from . import survey
from . import tripod
from .utilities import format_outcome


__version__ = {}
configs = configparser.ConfigParser(comment_prefixes="|", allow_no_value=True)
configs.optionxform = str
totalstation = None
serialport = None


def _load_configs() -> dict:
    """
    This function loads the configurations from the configs.ini file,
    and if necessary creates that file, missing sections, and/or missing options.
    """
    outcome = {"errors": [], "result": ""}
    global configs
    if not Path("configs.ini").is_file():
        with open("configs.ini", "w") as f:
            pass
    configs.read("configs.ini")
    # Serial Port configs
    if not configs.has_section("SERIAL"):
        configs.add_section("SERIAL")
    if not configs.has_option("SERIAL", "port"):
        configs.set(
            "SERIAL", "; Set port to “demo” or the path (e.g., “/dev/ttyUSB0”)."
        )
        configs.set("SERIAL", "port", "demo")
    if not configs.has_option("SERIAL", "uart"):
        configs.set(
            "SERIAL",
            "; Change the following to “true” if a UART adapter has been connected to the Raspberry Pi’s GPIO.",
        )
        configs.set("SERIAL", "uart", "false")
    # Total Station configs
    if not configs.has_section("TOTAL STATION"):
        configs.add_section("TOTAL STATION")
    if not configs.has_option("TOTAL STATION", "make"):
        configs.set("TOTAL STATION", "make", "Topcon")
    if not configs.has_option("TOTAL STATION", "model"):
        configs.set("TOTAL STATION", "model", "GTS-300 Series")
    # Backsight Error configs
    if not configs.has_section("BACKSIGHT ERROR"):
        configs.add_section("BACKSIGHT ERROR")
    if not configs.has_option("BACKSIGHT ERROR", "limit"):
        configs.set(
            "BACKSIGHT ERROR",
            "; Acceptable error range for backsight shots (expected horizontal distance vs. measured distance), in cm.",
        )
        configs.set("BACKSIGHT ERROR", "limit", "3.0")
    with open("configs.ini", "w") as f:
        configs.write(f)
    outcome["result"] = "Configurations loaded successfully."
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
            error = f"There is no module for the {make} {model} total station. Specify the correct total station make and model in configs.ini before proceeding."
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
    global __version__
    with open("../VERSION", "r") as f:
        __version__ = {
            "app": f.readline().strip().split("=")[1],
            "database": f.readline().strip().split("=")[1],
        }
        print(
            f"ShootPoints-Web v{__version__['app']}\nDatabase v{__version__['database']}"
        )
    database.latestversion = int(__version__["database"])
    saved_state = database._read_from_database("SELECT * FROM savedstate")["results"][0]
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
    loaders = [
        _load_configs,
        _load_total_station_model,
        _load_serial_port,
        database._upgrade_database,
    ]
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
            if not eachoption[0][0] == ";":
                currentconfigs[eachoption[0]] = eachoption[1]
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
        if configs["SERIAL"]["uart"] == "true" and re.fullmatch(
            "/dev/ttyAMA\\d+", port[0]
        ):
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
