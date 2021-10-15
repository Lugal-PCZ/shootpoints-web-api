"""This module handles the names and descriptions of sites in the ShootPoints database."""

from . import _database


def get_all_sites() -> dict:
    """ "This function returns the names and descriptions of all the sites in the database."""
    outcome = {"errors": [], "sites": {}}
    query = _database.read_from_database("SELECT * FROM sites")
    if query["success"]:
        outcome["sites"] = query["results"]
    outcome["success"] = not outcome["errors"]
    return {
        key: val
        for key, val in outcome.items()
        if val or key == "success" or key == "sites"
    }


def get_site(id: int) -> dict:
    """ "This function returns the name and description of the indicated site."""
    outcome = {"errors": [], "site": {}}
    query = _database.read_from_database("SELECT * FROM sites WHERE id = ?", (id,))
    if query["success"] and len(query["results"]) > 0:
        outcome["site"] = query["results"][0]
    else:
        outcome["errors"].append(f"Site id {id} was not found in the database.")
    outcome["success"] = not outcome["errors"]
    return {key: val for key, val in outcome.items() if val or key == "success"}


def save_site(name: str, description: str = None) -> dict:
    """This function creates a new site record in the database with the given name and description."""
    outcome = {"errors": [], "result": ""}
    name = name.strip()
    description = description.strip() if description else None
    if _database.read_from_database(
        "SELECT count(*) FROM sites WHERE upper(name) = ?", (name.upper(),)
    )["results"][0]["count(*)"]:
        outcome["errors"].append(f"The site name “{name}” is not unique.")
    if not outcome["errors"]:
        sql = f"INSERT INTO sites (name, description) VALUES (?, ?)"
        if _database.save_to_database(
            sql,
            (
                name,
                description,
            ),
        )["success"]:
            outcome["result"] = f"Site “{name}” saved to the database."
        else:
            outcome["errors"].append(
                f"Site “{name}” could not be saved to the database."
            )
    outcome["success"] = not outcome["errors"]
    return {key: val for key, val in outcome.items() if val or key == "success"}


def delete_site(id: int) -> dict:
    """This function deletes the indicated site from the database."""
    outcome = {"errors": [], "results": ""}
    exists = _database.read_from_database("SELECT name FROM sites WHERE id = ?", (id,))
    if exists["success"]:
        if exists[
            "results"
        ]:  # This is an empty list if there are no matches for the above query.
            name = exists["results"][0]["name"]
            sql = "DELETE FROM sites WHERE id = ?"
            deleted = _database.delete_from_database(sql, (id,))
            if deleted["success"]:
                outcome[
                    "result"
                ] = f"Site “{name}” successfully deleted from the database."
            else:
                outcome["errors"] = deleted["errors"]
            try:
                if outcome["errors"][0] == "FOREIGN KEY constraint failed":
                    outcome["errors"][
                        0
                    ] = f"Site “{name}” could not be deleted because one or more stations are at this site."
            except IndexError:
                pass
        else:
            outcome["errors"].append(f"Site id {id} does not exist.")
    else:
        outcome["errors"] = exists["errors"]
    outcome["success"] = not outcome["errors"]
    return {key: val for key, val in outcome.items() if val or key == "success"}
