"""This module contains functions for reading, creating, and removing classes and subclasses of archaeological survey data."""

from typing import Optional

from . import database
from .utilities import format_outcome


def get_all_classes() -> dict:
    """This function returns all the classes in the database."""
    outcome = {"errors": [], "results": []}
    classes = database._read_from_database("SELECT * FROM classes ORDER BY name")
    if "errors" not in classes:
        outcome["classes"] = classes["results"]
    else:
        outcome["errors"] = classes["errors"]
    return format_outcome(outcome, ["results"])


def get_subclasses(classes_id: int) -> dict:
    """This function returns all the subclasses in the database for the indicated class."""
    outcome = {"errors": [], "results": []}
    subclasses = database._read_from_database(
        "SELECT id, name, description FROM subclasses WHERE classes_id = ? ORDER BY name",
        (classes_id,),
    )
    if "errors" not in subclasses:
        outcome["subclasses"] = subclasses["results"]
    else:
        outcome["errors"] = subclasses["errors"]
    return format_outcome(outcome, ["subclasses"])


def save_new_class(name: str, description: Optional[str] = None) -> dict:
    """This function saves a new class to the database."""
    outcome = {"errors": [], "results": ""}
    name = name.strip().title()
    description = description.strip() if description else None
    sql = "INSERT INTO classes (name, description) VALUES(?, ?)"
    newclass = database._save_to_database(sql, (name, description))
    if "errors" not in newclass:
        outcome["result"] = f"Class “{name}” saved."
    else:
        outcome["errors"] = newclass["errors"]
    return format_outcome(outcome)


def save_new_subclass(
    classes_id: int, name: str, description: Optional[str] = None
) -> dict:
    """This function saves a new subclass to the database."""
    outcome = {"errors": [], "results": ""}
    name = name.strip().title()
    description = description.strip() if description else None
    sql = "INSERT INTO subclasses (classes_id, name, description) VALUES(?, ?, ?)"
    newclass = database._save_to_database(sql, (classes_id, name, description))
    if "errors" not in newclass:
        outcome["result"] = f"Sublass “{name}” saved."
    else:
        outcome["errors"] = newclass["errors"]
    return format_outcome(outcome)


def delete_class(id: int) -> dict:
    """This function deletes the indicated class from the database."""
    outcome = {"errors": [], "results": ""}
    exists = database._read_from_database(
        "SELECT name FROM classes WHERE id = ?", (id,)
    )
    if "errors" not in exists:
        if exists[
            "results"
        ]:  # This is an empty list if there are no matches for the above query.
            name = exists["results"][0]["name"]
            sql = "DELETE FROM classes WHERE id = ?"
            deleted = database._delete_from_database(sql, (id,))
            if "errors" not in deleted:
                outcome["result"] = f"Class “{name}” successfully deleted."
            else:
                outcome["errors"] = deleted["errors"]
            try:
                if outcome["errors"][0] == "FOREIGN KEY constraint failed":
                    outcome["errors"][
                        0
                    ] = f"Class “{name}” could not be deleted because it has one or more subclasses."
            except IndexError:
                pass
        else:
            outcome["errors"].append(f"Class id {id} does not exist.")
    else:
        outcome["errors"] = exists["errors"]
    return format_outcome(outcome)


def delete_subclass(classes_id: int, id: int) -> dict:
    """This function deletes the indicated subclass from the database."""
    outcome = {"errors": [], "results": ""}
    if id == 1:
        outcome["errors"].append(
            "The Survey Station subclass (id 1) cannot be deleted."
        )
    else:
        exists = database._read_from_database(
            "SELECT name FROM subclasses WHERE classes_id = ? AND id = ?",
            (
                classes_id,
                id,
            ),
        )
        if "errors" not in exists:
            if exists[
                "results"
            ]:  # This is an empty list if there are no matches for the above query.
                name = exists["results"][0]["name"]
                sql = "DELETE FROM subclasses WHERE id = ?"
                deleted = database._delete_from_database(sql, (id,))
                if "errors" not in deleted:
                    outcome["result"] = f"Subclass “{name}” successfully deleted."
                else:
                    outcome["errors"] = deleted["errors"]
                try:
                    if outcome["errors"][0] == "FOREIGN KEY constraint failed":
                        outcome["errors"][
                            0
                        ] = f"Subclass “{name}” could not be deleted because it is the subclass of one or more groupings."
                except IndexError:
                    pass
            else:
                outcome["errors"].append(
                    f"Subclass id {id} does not exist or is not a subclass of class id {classes_id}."
                )
        else:
            outcome["errors"] = exists["errors"]
    return format_outcome(outcome)
