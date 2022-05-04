"""This module handles reading from and writing to the ShootPoints database."""

import sqlite3
import json
import csv
import os, glob
from zipfile import ZipFile, ZIP_DEFLATED


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


def save_to_database(sql: str, data: tuple) -> dict:
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
    return {key: val for key, val in outcome.items() if val}


def read_from_database(sql: str, params: tuple = ()) -> dict:
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
    return {key: val for key, val in outcome.items() if val or key == "results"}


def delete_from_database(sql: str, params: tuple) -> dict:
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
    return {key: val for key, val in outcome.items() if val or key == "results"}


def export_session_data(sessions_id: int) -> None:
    """This function creates a ZIP file of a session and its shots, for download by the browser."""
    # First, get information about the session, and save it to a JSON file.
    sql = (
        "SELECT "
        "  sess.id AS session_id, "
        "  sess.label AS session_label, "
        "  sess.started AS session_started, "
        "  sess.surveyor AS session_surveyor, "
        "  site.id AS session_site_id, "
        "  site.name AS session_site_name, "
        "  site.description AS session_site_description, "
        "  sess.azimuth AS session_azimuth, "
        "  sess.instrumentheight AS session_instrumentheight, "
        "  sess.pressure AS session_pressure, "
        "  sess.temperature AS session_temperature, "
        "  sta1.id AS occupied_station_id, "
        "  sta1.name AS occupied_station_name, "
        "  sta1.description AS occupied_station_description, "
        "  sta1.northing AS occupied_station_northing, "
        "  sta1.easting AS occupied_station_easting, "
        "  sta1.elevation AS occupied_station_elevation, "
        "  sta1.utmzone AS occupied_station_utmzone, "
        "  sta1.latitude AS occupied_station_latitude, "
        "  sta1.longitude AS occupied_station_longitude, "
        "  sta2.id AS backsight_station_id, "
        "  sta2.name AS backsight_station_name, "
        "  sta2.description AS backsight_station_description, "
        "  sta2.northing AS backsight_station_northing, "
        "  sta2.easting AS backsight_station_easting, "
        "  sta2.elevation AS backsight_station_elevation, "
        "  sta2.utmzone AS backsight_station_utmzone, "
        "  sta2.latitude AS backsight_station_latitude, "
        "  sta2.longitude AS backsight_station_longitude "
        "FROM sessions sess "
        "JOIN stations sta1 ON  sess.stations_id_occupied = sta1.id "
        "JOIN sites site ON sta1.sites_id = site.id "
        "LEFT OUTER JOIN stations sta2 ON sess.stations_id_backsight = sta2.id "
        "WHERE sess.id = ?"
    )
    sessiondata = read_from_database(sql, (sessions_id,))["results"][0]
    session = {"session": {}}
    occupied_station = {}
    backsight_station = {}
    for key, val in sessiondata.items():
        if key.startswith("session_"):
            session["session"][key[8:]] = val
        elif key.startswith("occupied_"):
            occupied_station[key[17:]] = val
        elif key.startswith("backsight_"):
            backsight_station[key[18:]] = val
    session["session"]["occupied_station"] = occupied_station
    if backsight_station["name"]:
        session["session"]["backsight_station"] = backsight_station
    with open("exports/session_info.json", "w") as f:
        f.write(json.dumps(session, ensure_ascii=False, indent=2))
    # Next, get data for all the shots in the session, and save them to a CSV file.
    sql = (
        "SELECT "
        "  grp.id AS group_id, "
        "  grp.label AS group_label, "
        "  grp.description AS group_description, "
        "  cls.name AS class, "
        "  scl.name AS subclass, "
        "  geo.name AS geometry, "
        "  sh.label, "
        "  sh.comment, "
        "  sh.timestamp, "
        "  sh.pressure, "
        "  sh.temperature, "
        "  sh.delta_n, "
        "  sh.delta_e, "
        "  sh.delta_z, "
        "  sh.prismoffset_vertical, "
        "  sh.prismoffset_latitude, "
        "  sh.prismoffset_longitude, "
        "  sh.prismoffset_radial, "
        "  sh.prismoffset_tangent, "
        "  sh.prismoffset_vertical, "
        "  sh.prismoffset_wedge, "
        "  sh.northing, "
        "  sh.easting, "
        "  sh.elevation "
        "FROM groupings grp "
        "JOIN geometry geo ON grp.geometry_id = geo.id "
        "JOIN subclasses scl ON grp.subclasses_id = scl.id "
        "JOIN classes cls ON scl.classes_id = cls.id "
        "JOIN shots sh ON sh.groupings_id = grp.id "
        "WHERE grp.sessions_id = ?"
    )
    shotsdata = read_from_database(sql, (sessions_id,))["results"]
    with open("exports/shots_data.csv", "w") as f:
        shotsfile = csv.DictWriter(f, fieldnames=shotsdata[0].keys())
        shotsfile.writeheader()
        shotsfile.writerows(shotsdata)
    # Parse the shots data and re-format it as a CSV file that QGIS can import directly.
    allshots = []
    multipointgroups = []
    linestringgroups = []
    thisgroupinfo = {}
    thisgroupgeometry = ""
    shotsinthisgroup = []

    def _assemble_group():
        if len(shotsinthisgroup) > 1:
            # Wipe out the shot label and comment, which are taken from the first shot and wouldn't make sense for the entire group.
            thisgroupinfo["label"] = None
            thisgroupinfo["comment"] = None
            if thisgroupgeometry == "Point Cloud":
                multipointgroups.append(
                    dict(
                        {"wkt": f"MULTIPOINT Z({', '.join(shotsinthisgroup)})"},
                        **thisgroupinfo,
                    )
                )
            elif thisgroupgeometry == "Open Polygon":
                linestringgroups.append(
                    dict(
                        {"wkt": f"LINESTRING Z({', '.join(shotsinthisgroup)})"},
                        **thisgroupinfo,
                    )
                )
            elif thisgroupgeometry == "Closed Polygon":
                shotsinthisgroup.append(shotsinthisgroup[0])
                linestringgroups.append(
                    dict(
                        {"wkt": f"LINESTRING Z({', '.join(shotsinthisgroup)})"},
                        **thisgroupinfo,
                    )
                )

    for eachshot in shotsdata:
        if (
            not "group_id" in thisgroupinfo
            or eachshot["group_id"] != thisgroupinfo["group_id"]
        ):
            _assemble_group()
            thisgroupgeometry = eachshot["geometry"]
            thisgroupinfo = {
                "group_id": eachshot["group_id"],
                "group_label": eachshot["group_label"],
                "group_description": eachshot["group_description"],
                "class": eachshot["class"],
                "subclass": eachshot["subclass"],
                "label": eachshot["label"],
                "comment": eachshot["comment"],
                "timestamp": eachshot["timestamp"],
            }
            shotsinthisgroup = []
        shotsinthisgroup.append(
            f"{eachshot['easting']} {eachshot['northing']} {eachshot['elevation']}"
        )
        allshots.append(
            {
                "group_id": eachshot["group_id"],
                "group_label": eachshot["group_label"],
                "group_description": eachshot["group_description"],
                "class": eachshot["class"],
                "subclass": eachshot["subclass"],
                "label": eachshot["label"],
                "comment": eachshot["comment"],
                "timestamp": eachshot["timestamp"],
                "wkt": f"POINT Z({eachshot['easting']} {eachshot['northing']} {eachshot['elevation']})",
            }
        )
    _assemble_group()  # This terminates a multi-point group that's at the end of the file
    qgisfieldnames = [
        "group_id",
        "group_label",
        "group_description",
        "class",
        "subclass",
        "label",
        "comment",
        "timestamp",
        "wkt",
    ]
    with open("exports/for_qgis_allshots.csv", "w") as f:
        qgisfile = csv.DictWriter(
            f,
            fieldnames=qgisfieldnames,
        )
        qgisfile.writeheader()
        qgisfile.writerows(allshots)
    if multipointgroups:
        with open("exports/for_qgis_multipointgroups.csv", "w") as f:
            qgisfile = csv.DictWriter(
                f,
                fieldnames=qgisfieldnames,
            )
            qgisfile.writeheader()
            qgisfile.writerows(multipointgroups)
    if linestringgroups:
        with open("exports/for_qgis_linestringgroups.csv", "w") as f:
            qgisfile = csv.DictWriter(
                f,
                fieldnames=qgisfieldnames,
            )
            qgisfile.writeheader()
            qgisfile.writerows(linestringgroups)
    # Export a file of photogrammetry GCPs.
    groundcontrolpoints = []
    for eachshot in shotsdata:
        if eachshot["subclass"] == "GCP":
            groundcontrolpoints.append(
                f"{eachshot['group_label'].replace(' ', '_')}\t{eachshot['easting']}\t{eachshot['northing']}\t{eachshot['elevation']}"
            )
    if groundcontrolpoints:
        with open("exports/photogrammetry_gcps_gcps_for_webodm.txt", "w") as f:
            f.write(f"WGS84 UTM {sessiondata['occupied_station_utmzone']}\n")
            for eachgcp in groundcontrolpoints:
                f.write(f"{eachgcp}\n")
        with open("exports/photogrammetry_gcps_gcps_for_dronedeploy.csv", "w") as f:
            headers = ["GCP Label", "Northing", "Easting", "Elevation (m)"]
            gcpfile = csv.DictWriter(
                f,
                fieldnames=headers,
            )
            gcpfile.writeheader()
            for eachgcp in groundcontrolpoints:
                coords = eachgcp.split("\t")
                gcpfile.writerow(
                    dict(zip(headers, [coords[0], coords[2], coords[1], coords[3]]))
                )
    # Finally, bundle up all the export files into a ZIP archive for download.
    filesinarchive = [
        "session_info.json",
        "shots_data.csv",
        "for_qgis/allshots.csv",
        "for_qgis/linestringgroups.csv",
        "for_qgis/multipointgroups.csv",
        "photogrammetry_gcps/gcps_for_webodm.txt",
        "photogrammetry_gcps/gcps_for_dronedeploy.csv",
    ]
    archivename = f"ShootPoints_Export_{sessiondata['session_started'][:10]}_Session-{sessiondata['session_id']}"
    with ZipFile(f"exports/export.zip", "w", compression=ZIP_DEFLATED) as f:
        for eachfile in filesinarchive:
            try:
                f.write(
                    f"exports/{eachfile.replace('/', '_')}",
                    arcname=f"{archivename}/{eachfile}",
                )
            except FileNotFoundError:
                pass
    cleanup = glob.glob("exports/*.json")
    cleanup.extend(glob.glob("exports/*.csv"))
    cleanup.extend(glob.glob("exports/*.txt"))
    for eachfile in cleanup:
        os.remove(eachfile)


def get_setup_errors() -> list:
    """This function returns any setup errors logged on app load."""
    outcome = read_from_database("SELECT * FROM setuperrors")
    errors = []
    try:
        for each in outcome["results"]:
            errors.append(each["error"])
    except:
        pass
    return errors


def zip_database_file() -> None:
    """This function creates a ZIP file of the ShootPoints database file, for download by the browser."""
    with ZipFile(f"exports/database.zip", "w", compression=ZIP_DEFLATED) as f:
        f.write("ShootPoints.db")  # , arcname=f"{archivename}/session_info.json")


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
