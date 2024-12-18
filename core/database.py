"""This module handles reading from and writing to the ShootPoints database."""

import datetime
import os
import shutil
import sqlite3
from pathlib import Path

from .survey import end_current_session
from .utilities import format_outcome


dbconn = sqlite3.connect("ShootPoints.db", check_same_thread=False)
dbconn.row_factory = sqlite3.Row
cursor = dbconn.cursor()
try:
    cursor.execute("SELECT 1 FROM stations")
except sqlite3.OperationalError:
    # ShootPoints.db database is empty, so initialize it with the default schema.
    with open("blank_database.sql", "r") as f:
        cursor.executescript(f.read())
        dbconn.commit()
cursor.execute("PRAGMA foreign_keys = ON")


def _save_to_database(sql: str, data: tuple) -> dict:
    """This function performs an INSERT or UPDATE of the given data using the provided query string."""
    outcome = {"errors": [], "result": ""}
    if sql[:11].upper().find("INSERT INTO") == 0 or sql[:6].upper().find("UPDATE") == 0:
        try:
            cursor.execute(sql, data)
            dbconn.commit()
            outcome["result"] = "Data successfully saved to the database."
        except sqlite3.Error as err:
            outcome["errors"].append(str(err))
    else:
        outcome["errors"].append(
            "The given sql does not appear to be an INSERT or UPDATE query."
        )
    return format_outcome(outcome)


def _read_from_database(sql: str, params: tuple = ()) -> dict:
    """This function performs a SELECT query on the database, with optional parameters."""
    outcome = {"errors": [], "results": []}
    if sql[:6].upper().find("SELECT") == 0:
        try:
            cursor.execute(sql, params)
            outcome["results"].extend([dict(row) for row in cursor.fetchall()])
        except sqlite3.Error as err:
            outcome["errors"].append(str(err))
    else:
        outcome["errors"].append("The given sql does not appear to be a SELECT query.")
    return format_outcome(outcome, ["results"])


def _delete_from_database(sql: str, params: tuple) -> dict:
    """This function deletes data from the database"""
    outcome = {"errors": [], "result": ""}
    if sql[:6].upper().find("DELETE") == 0:
        try:
            cursor.execute(sql, params)
            dbconn.commit()
            affected = cursor.rowcount
            if affected == 1:
                outcome["result"] = f"1 row was deleted."
            else:
                outcome["result"] = f"{affected} rows were deleted."
        except sqlite3.Error as err:
            outcome["errors"].append(str(err))
    else:
        outcome["errors"].append("The given sql does not appear to be a DELETE query.")
    return format_outcome(outcome, ["results"])


def _record_setup_error(error: str) -> None:
    sql = "INSERT INTO setuperrors (error) VALUES (?)"
    try:
        cursor.execute(sql, (error,))
        dbconn.commit()
    except sqlite3.IntegrityError:
        pass


def _clear_setup_errors() -> None:
    try:
        cursor.execute("DELETE FROM setuperrors")
        dbconn.commit()
    except:
        pass


def get_setup_errors() -> dict:
    """This function returns any setup errors logged on app load."""
    outcome = _read_from_database("SELECT * FROM setuperrors")
    if "errors" not in outcome:
        outcome["errors"] = []
        try:
            for each in outcome["results"]:
                outcome["errors"].append(each["error"])
        except:
            pass
        outcome["results"] = "ShootPoints is ready for use."
    return format_outcome(outcome)


def reset_database(
    preservesitesandstations: bool = True, preserveclassesandsubclasses: bool = True
) -> dict:
    """This function creates a new blank database, optionally with some data saved from the current one."""
    global dbconn
    global cursor
    outcome = end_current_session()
    # Cache sites, stations, classes, and subclasses if requested
    cachedsites = []
    cachedstations = []
    cachedclasses = []
    cachedsubclasses = []
    if preservesitesandstations:
        cachedsites = _read_from_database("SELECT * FROM sites")["results"]
        cachedstations = _read_from_database("SELECT * FROM stations")["results"]
    if preserveclassesandsubclasses:
        cachedclasses = _read_from_database("SELECT * FROM classes")["results"]
        cachedsubclasses = _read_from_database("SELECT * FROM subclasses")["results"]
    # Back up the current database to the backups folder and restore a pristine copy
    dbconn.close()
    thedatetime = str(datetime.datetime.now()).split(".")[0].replace(":", "-")
    shutil.copy2(
        "ShootPoints.db", str(Path("backups") / f"ShootPoints ({thedatetime}).db")
    )
    os.remove("ShootPoints.db")
    dbconn = sqlite3.connect("ShootPoints.db", check_same_thread=False)
    dbconn.row_factory = sqlite3.Row
    cursor = dbconn.cursor()
    with open("blank_database.sql", "r") as f:
        cursor.executescript(f.read())
        dbconn.commit()
        cursor.execute("PRAGMA foreign_keys = ON")
    # Restore cached data
    sql = "INSERT INTO sites (id, name, description) VALUES (?, ?, ?)"
    cursor.executemany(sql, [tuple(each.values()) for each in cachedsites])
    sql = "INSERT INTO stations (id, sites_id, name, description, northing, easting, elevation, utmzone, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    cursor.executemany(sql, [tuple(each.values()) for each in cachedstations])
    if preserveclassesandsubclasses:
        cursor.execute("DELETE FROM subclasses")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='subclasses'")
        cursor.execute("DELETE FROM classes")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='classes'")
        sql = "INSERT INTO classes (id, name, description) VALUES (?, ?, ?)"
        cursor.executemany(sql, [tuple(each.values()) for each in cachedclasses])
        sql = "INSERT INTO subclasses (id, classes_id, name, description) VALUES (?, ?, ?, ?)"
        cursor.executemany(sql, [tuple(each.values()) for each in cachedsubclasses])
    dbconn.commit()
    # Return result message
    outcome["result"] = "Database replaced with pristine copy."
    if preservesitesandstations and preserveclassesandsubclasses:
        outcome["result"] = (
            "Database reset, preserving existing sites, stations, classes, and subclasses."
        )
    elif preservesitesandstations:
        outcome["result"] = "Database reset, preserving existing sites and stations."
    elif preserveclassesandsubclasses:
        outcome["result"] = (
            "Database reset, preserving existing classes and subclasses."
        )
    return outcome
