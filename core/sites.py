"""This module handles the names and descriptions of sites in the ShootPoints database."""

from typing import Optional

from . import database
from .utilities import format_outcome


def get_all_sites() -> dict:
    """ "This function returns the names and descriptions of all the sites in the database."""
    outcome = {"errors": [], "sites": {}}
    query = database._read_from_database("SELECT * FROM sites ORDER BY name")
    if "errors" not in query:
        outcome["sites"] = query["results"]
    return format_outcome(outcome, ["sites"])


def save_site(name: str, description: Optional[str] = None) -> dict:
    """This function creates a new site record in the database with the given name and description."""
    outcome = {"errors": [], "result": ""}
    name = name.strip()
    description = description.strip() if description else None
    if database._read_from_database(
        "SELECT count(*) FROM sites WHERE upper(name) = ?", (name.upper(),)
    )["results"][0]["count(*)"]:
        outcome["errors"].append(f"The site name “{name}” is already taken.")
    if not outcome["errors"]:
        sql = "INSERT INTO sites (name, description) VALUES (?, ?)"
        saved = database._save_to_database(
            sql,
            (
                name,
                description,
            ),
        )
        if "errors" not in saved:
            outcome["result"] = f"Site “{name}” saved."
        else:
            outcome["errors"].append(f"Site “{name}” could not be saved.")
    return format_outcome(outcome)


def delete_site(id: int) -> dict:
    """This function deletes the indicated site from the database."""
    outcome = {"errors": [], "results": ""}
    exists = database._read_from_database("SELECT name FROM sites WHERE id = ?", (id,))
    if "errors" not in exists:
        if exists[
            "results"
        ]:  # This is an empty list if there are no matches for the above query.
            name = exists["results"][0]["name"]
            sql = "DELETE FROM sites WHERE id = ?"
            deleted = database._delete_from_database(sql, (id,))
            if "errors" not in deleted:
                outcome["result"] = f"Site “{name}” successfully deleted."
            else:
                outcome["errors"] = deleted["errors"]
            try:
                if outcome["errors"][0] == "FOREIGN KEY constraint failed":
                    outcome["errors"][0] = (
                        f"Site “{name}” could not be deleted because it contains one or more stations."
                    )
            except IndexError:
                pass
        else:
            outcome["errors"].append(f"Site id {id} does not exist.")
    else:
        outcome["errors"] = exists["errors"]
    return format_outcome(outcome)
