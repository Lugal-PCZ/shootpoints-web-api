"""This module handles reading from and writing to the ShootPoints database."""

import sqlite3

from .utilities import format_outcome


dbconn = sqlite3.connect("ShootPoints.db", check_same_thread=False)
dbconn.row_factory = sqlite3.Row
cursor = dbconn.cursor()
try:
    cursor.execute("SELECT 1 FROM stations")
except sqlite3.OperationalError:
    # ShootPoints.db database is empty, so initialize it with the default schema.
    with open("blank_database.sql", "r") as f:
        sql = f.read().split(";")
        _ = [cursor.execute(query) for query in sql]
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
    return format_outcome(outcome, "results")


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
    return format_outcome(outcome, "results")


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
        outcome["results"] = "ShootPoints loaded without errors."
    return format_outcome(outcome)
