"""This module handles importing ShootPoints data."""

import json

from . import database
from . import utilities

_verbs = [
    "they were",
    "it was",
]


def import_classes(f) -> dict:
    """This function reads a JSON file of exported classes and subclasses, and loads them into the database."""
    outcome = {
        "errors": [],
        "result": "",
    }
    wrongfiletype = "This is not a ShootPoints classes/subclasses export file."
    contents = json.load(f)
    if "_comment" not in contents:
        outcome["errors"].append(wrongfiletype)
    elif not contents["_comment"].startswith("ShootPoints classes and subclasses"):
        outcome["errors"].append(wrongfiletype)
    else:
        classesimported = 0
        classesskipped = 0
        subclassesimported = 0
        subclassesskipped = 0
        for (
            eachclass,
            details,
        ) in contents.items():
            if eachclass != "_comment":
                sql = "INSERT INTO classes (name, description) VALUES (?, ?)"
                if "result" in database._save_to_database(
                    sql,
                    (
                        eachclass,
                        contents[eachclass]["description"],
                    ),
                ):
                    classesimported += 1
                else:
                    classesskipped += 1
                sql = "SELECT id FROM classes WHERE name = ?"
                classes_id = database._read_from_database(
                    sql,
                    (eachclass,),
                )["results"][0]["id"]
                for (
                    eachsubclass,
                    eachsubclassdetails,
                ) in details["subclasses"].items():
                    sql = "INSERT INTO subclasses (classes_id, name, description) VALUES (?, ?, ?)"
                    if "result" in database._save_to_database(
                        sql,
                        (
                            classes_id,
                            eachsubclass,
                            eachsubclassdetails["description"],
                        ),
                    ):
                        subclassesimported += 1
                    else:
                        subclassesskipped += 1
        outcome["result"] = (
            f"{classesimported} class{'es'[: 2 * classesimported ^ 2]} imported, and {classesskipped} skipped because {_verbs[1] if classesskipped == 1 else _verbs[0]} already in the database. {subclassesimported} subclass{'es'[: 2 * subclassesimported ^ 2]} imported, and {subclassesskipped} skipped because {_verbs[1] if subclassesskipped == 1 else _verbs[0]} already in the database."
        )
    return utilities.format_outcome(outcome)


def import_stations(
    f,
) -> dict:
    """This function reads a JSON file of exported stations, and loads them into the database."""
    outcome = {
        "errors": [],
        "result": "",
    }
    wrongfiletype = "This is not a ShootPoints stations export file."
    contents = json.load(f)
    if "_comment" not in contents:
        outcome["errors"].append(wrongfiletype)
    elif not contents["_comment"].startswith("ShootPoints stations for"):
        outcome["errors"].append(wrongfiletype)
    else:
        sql = "INSERT INTO sites (name, description) VALUES (?, ?)"
        database._save_to_database(
            sql,
            (
                contents["site"],
                contents["description"],
            ),
        )
        sql = "SELECT id FROM sites WHERE name = ?"
        sites_id = database._read_from_database(
            sql,
            (contents["site"],),
        )["results"][0]["id"]
        stationsimported = 0
        stationsskipped = 0
        for (
            stationname,
            stationdetails,
        ) in contents["stations"].items():
            sql = "INSERT INTO stations (sites_id, name, description, northing, easting, elevation, utmzone, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            if "result" in database._save_to_database(
                sql,
                (
                    sites_id,
                    stationname,
                    stationdetails["description"],
                    stationdetails["northing"],
                    stationdetails["easting"],
                    stationdetails["elevation"],
                    stationdetails["utmzone"],
                    stationdetails["latitude"],
                    stationdetails["longitude"],
                ),
            ):
                stationsimported += 1
            else:
                stationsskipped += 1
        outcome["result"] = (
            f"{stationsimported} station{'s'[: stationsimported ^ 1]} imported, and {stationsskipped} skipped because {_verbs[1] if stationsskipped == 1 else _verbs[0]} already in the database."
        )
    return utilities.format_outcome(outcome)
