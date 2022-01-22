"""This module contains functions for reading, creating, and removing classes and subclasses of archaeological survey data."""

from . import database


def get_all_classes() -> dict:
    """This function returns all the classes in the database."""
    outcome = {"errors": [], "results": []}
    classes = database.read_from_database("SELECT * FROM classes ORDER BY name")
    if not "errors" in classes:
        outcome["classes"] = classes["results"]
    else:
        outcome["errors"] = classes["errors"]
    return {key: val for key, val in outcome.items() if val or key == "results"}


def get_subclasses(classes_id: int) -> dict:
    """This function returns all the subclasses in the database for the indicated class."""
    outcome = {"errors": [], "results": []}
    subclasses = database.read_from_database(
        "SELECT id, name, description FROM subclasses WHERE classes_id = ? ORDER BY name",
        (classes_id,),
    )
    if not "errors" in subclasses:
        outcome["subclasses"] = subclasses["results"]
    else:
        outcome["errors"] = classes["errors"]
    return {key: val for key, val in outcome.items() if val or key == "results"}


def save_new_class(name: str, description: str = None) -> dict:
    """This function saves a new class to the database."""
    outcome = {"errors": [], "results": ""}
    name = name.strip().title()
    description = description.strip() if description else None
    sql = "INSERT INTO classes (name, description) VALUES(?, ?)"
    newclass = database.save_to_database(sql, (name, description))
    if not "errors" in newclass:
        outcome["result"] = f"Class “{name}” saved to the database."
    else:
        outcome["errors"] = newclass["errors"]
    return {key: val for key, val in outcome.items() if val}


def save_new_subclass(classes_id: int, name: str, description: str = None) -> dict:
    """This function saves a new subclass to the database."""
    outcome = {"errors": [], "results": ""}
    name = name.strip().title()
    description = description.strip() if description else None
    sql = "INSERT INTO subclasses (classes_id, name, description) VALUES(?, ?, ?)"
    newclass = database.save_to_database(sql, (classes_id, name, description))
    if not "errors" in newclass:
        outcome["result"] = f"Sublass “{name}” saved to the database."
    else:
        outcome["errors"] = newclass["errors"]
    return {key: val for key, val in outcome.items() if val}


def delete_class(id: int) -> dict:
    """This function deletes the indicated class from the database."""
    outcome = {"errors": [], "results": ""}
    exists = database.read_from_database("SELECT name FROM classes WHERE id = ?", (id,))
    if not "errors" in exists:
        if exists[
            "results"
        ]:  # This is an empty list if there are no matches for the above query.
            name = exists["results"][0]["name"]
            sql = "DELETE FROM classes WHERE id = ?"
            deleted = database.delete_from_database(sql, (id,))
            if not "errors" in deleted:
                outcome[
                    "result"
                ] = f"Class “{name}” successfully deleted from the database."
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
    return {key: val for key, val in outcome.items() if val}


def delete_subclass(classes_id: int, id: int) -> dict:
    """This function deletes the indicated subclass from the database."""
    outcome = {"errors": [], "results": ""}
    if id == 1:
        outcome["errors"].append(
            "The Survey Station subclass (id 1) cannot be deleted."
        )
    else:
        exists = database.read_from_database(
            "SELECT name FROM subclasses WHERE classes_id = ? AND id = ?",
            (
                classes_id,
                id,
            ),
        )
        if not "errors" in exists:
            if exists[
                "results"
            ]:  # This is an empty list if there are no matches for the above query.
                name = exists["results"][0]["name"]
                sql = "DELETE FROM subclasses WHERE id = ?"
                deleted = database.delete_from_database(sql, (id,))
                if not "errors" in deleted:
                    outcome[
                        "result"
                    ] = f"Subclass “{name}” successfully deleted from the database."
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
    return {key: val for key, val in outcome.items() if val}
