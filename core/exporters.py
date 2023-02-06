"""This module handles exporting ShootPoints data."""

import json
import csv
import shapefile
import os, glob
from zipfile import ZipFile, ZIP_DEFLATED

from . import database


# Define the file formats for exported GCPs.
gcpfiles = [
    {
        "name": "dronedeploy",
        "type": "csv",
        "coords": "NEZ",
        "headers": ["GCP Label", "Northing", "Easting", "Elevation (m)"],
    },
    {
        "name": "metashape",
        "type": "csv",
        "coords": "XYZ",
        "headers": ["Name", "X", "Y", "Z"],
    },
    {
        "name": "pix4d",
        "type": "csv",
        "coords": "ENZ",
        "headers": [],
    },
    {
        "name": "realitycapture",
        "type": "csv",
        "coords": "XYZ",
        "headers": ["Name", "X (east)", "Y (north)", "Alt"],
    },
    {
        "name": "webodm",
        "type": "txt",
        "coords": "XYZ",
        "headers": ["WGS84 UTM |UTMZONE|"],
    },
]


def export_database_file() -> None:
    """This function creates a ZIP file of the ShootPoints database file, for download by the browser."""
    with ZipFile(f"exports/database.zip", "w", compression=ZIP_DEFLATED) as f:
        f.write("ShootPoints.db")


def export_session_data(sessions_id: int) -> None:
    """This function creates a ZIP file of a session and its shots, for download by the browser."""
    allshots = []
    pointclouds = []
    openpolygons = []
    closedpolygons = []
    thisgroupinfo = {}
    thisgroupgeometry = ""
    shotsinthisgroup = []
    gcps = []

    def _assemble_group():
        if thisgroupgeometry == "Point Cloud":
            pointclouds.append([dict(**thisgroupinfo), shotsinthisgroup])
        elif thisgroupgeometry == "Open Polygon":
            openpolygons.append([dict(**thisgroupinfo), shotsinthisgroup])
        elif thisgroupgeometry == "Closed Polygon":
            closedpolygons.append([dict(**thisgroupinfo), shotsinthisgroup])

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
        "  sta2.longitude AS backsight_station_longitude, "
        "  count(DISTINCT grp.id) AS data_number_of_groupings, "
        "  count(shots.id) AS data_number_of_shots "
        "FROM sessions sess "
        "JOIN stations sta1 ON  sess.stations_id_occupied = sta1.id "
        "JOIN sites site ON sta1.sites_id = site.id "
        "LEFT OUTER JOIN stations sta2 ON sess.stations_id_backsight = sta2.id "
        "LEFT OUTER JOIN groupings grp ON grp.sessions_id = sess.id "
        "LEFT OUTER JOIN shots ON shots.groupings_id = grp.id "
        "WHERE sess.id = ?"
    )
    sessiondata = database.read_from_database(sql, (sessions_id,))["results"][0]
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
        elif key.startswith("data_"):
            session["session"][key[5:]] = val
    session["session"]["occupied_station"] = occupied_station
    if backsight_station["name"]:
        session["session"]["backsight_station"] = backsight_station
    with open("exports/session_info.json", "w") as f:
        f.write(json.dumps(session, ensure_ascii=False, indent=2))

    # Next, get all the shots in the session, and handle them accordingly.
    if sessiondata["data_number_of_shots"] > 0:
        sql = (
            "SELECT "
            "  grp.id AS group_id, "
            "  grp.label, "
            "  grp.description, "
            "  cls.name AS class, "
            "  scl.name AS subclass, "
            "  geo.name AS geometry, "
            "  sh.id AS shot_id, "
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
            "JOIN geometries geo ON grp.geometries_id = geo.id "
            "JOIN subclasses scl ON grp.subclasses_id = scl.id "
            "JOIN classes cls ON scl.classes_id = cls.id "
            "JOIN shots sh ON sh.groupings_id = grp.id "
            "WHERE grp.sessions_id = ?"
        )
        shotsdata = database.read_from_database(sql, (sessions_id,))["results"]
        # Save all shots to a flat CSV file.
        with open("exports/shots_data.csv", "w") as f:
            shotsfile = csv.DictWriter(f, fieldnames=shotsdata[0].keys())
            shotsfile.writeheader()
            shotsfile.writerows(shotsdata)
        # Parse shotsdata to build the shapefiles and GCP files.
        for eachshot in shotsdata:
            if (
                not "group_id" in thisgroupinfo
                # This is the first shot in shotsdata.
                or eachshot["group_id"] != thisgroupinfo["group_id"]
                # This is the first shot in a new grouping.
            ):
                _assemble_group()
                thisgroupgeometry = eachshot["geometry"]
                thisgroupinfo = {
                    "group_id": eachshot["group_id"],
                    "label": eachshot["label"],
                    "descr": eachshot["description"],
                    "class": eachshot["class"],
                    "subclass": eachshot["subclass"],
                }
                shotsinthisgroup = []
            shotsinthisgroup.append(
                [eachshot["easting"], eachshot["northing"], eachshot["elevation"]]
            )
            allshots.append(
                {
                    "group_id": eachshot["group_id"],
                    "shot_id": eachshot["shot_id"],
                    "label": eachshot["label"],
                    "descr": eachshot["description"],
                    "class": eachshot["class"],
                    "subclass": eachshot["subclass"],
                    "comment": eachshot["comment"],
                    "timestamp": eachshot["timestamp"],
                    "N": eachshot["northing"],
                    "E": eachshot["easting"],
                    "Z": eachshot["elevation"],
                }
            )
            # Assemble a list of all the GCPs in this session.
            if eachshot["subclass"] == "GCP":
                label = eachshot["label"].replace(" ", "_").replace(",", "_")
                gcps.append(
                    {
                        "label": label,
                        "N": eachshot["northing"],
                        "E": eachshot["easting"],
                        "X": eachshot["easting"],
                        "Y": eachshot["northing"],
                        "Z": eachshot["elevation"],
                    }
                )
        _assemble_group()  # This terminates a multi-point group that's at the end of the file

    # Then save the shapefiles and GCP files.
    if allshots:
        with shapefile.Writer(
            "exports/gis_shapefiles_allshots", shapeType=shapefile.POINTZ
        ) as w:
            w.field("group_id", "N")
            w.field("shot_id", "N")
            w.field("label", "C")
            w.field("descr", "C")
            w.field("class", "C")
            w.field("subclass", "C")
            w.field("comment", "C")
            w.field("timestamp", "C")
            w.field("N", "N", decimal=3)
            w.field("E", "N", decimal=3)
            w.field("Z", "N", decimal=3)
            for eachshot in allshots:
                w.record(*tuple(eachshot.values()))
                w.pointz(eachshot["E"], eachshot["N"], eachshot["Z"])
    if closedpolygons:
        with shapefile.Writer(
            "exports/gis_shapefiles_closedpolygons", shapeType=shapefile.POLYGONZ
        ) as w:
            w.field("group_id", "N")
            w.field("label", "C")
            w.field("descr", "C")
            w.field("class", "C")
            w.field("subclass", "C")
            for eachgroup in closedpolygons:
                w.record(*tuple(eachgroup[0].values()))
                w.polyz([eachgroup[1]])
    if openpolygons:
        with shapefile.Writer(
            "exports/gis_shapefiles_openpolygons", shapeType=shapefile.POLYLINEZ
        ) as w:
            w.field("group_id", "N")
            w.field("label", "C")
            w.field("descr", "C")
            w.field("class", "C")
            w.field("subclass", "C")
            for eachgroup in openpolygons:
                w.record(*tuple(eachgroup[0].values()))
                w.linez([eachgroup[1]])
    if pointclouds:
        with shapefile.Writer(
            "exports/gis_shapefiles_pointclouds", shapeType=shapefile.MULTIPOINTZ
        ) as w:
            w.field("group_id", "N")
            w.field("label", "C")
            w.field("descr", "C")
            w.field("class", "C")
            w.field("subclass", "C")
            for eachgroup in pointclouds:
                w.record(*tuple(eachgroup[0].values()))
                w.multipointz(eachgroup[1])
    if gcps:
        for eachfile in gcpfiles:
            _write_gcps_to_file(eachfile, sessiondata, gcps)

    # Finally, bundle up all the export files into a ZIP archive for download.
    filesinarchive = [
        "session_info.json",
        "shots_data.csv",
    ]
    for eachfile in ["allshots", "closedpolygons", "openpolygons", "pointclouds"]:
        filesinarchive.append(f"gis_shapefiles/{eachfile}.dbf")
        filesinarchive.append(f"gis_shapefiles/{eachfile}.shp")
        filesinarchive.append(f"gis_shapefiles/{eachfile}.shx")
    for eachfile in gcpfiles:
        filesinarchive.append(
            f"photogrammetry_gcps/gcps_for_{eachfile['name']}.{eachfile['type']}"
        )
    archivename = f"ShootPoints_Data_{sessiondata['session_started'].replace('-', '').replace(' ', '').replace(':', '')}"
    with ZipFile(f"exports/export.zip", "w", compression=ZIP_DEFLATED) as f:
        for eachfile in filesinarchive:
            try:
                f.write(
                    f"exports/{eachfile.replace('/', '_')}",
                    arcname=f"{archivename}/{eachfile}",
                )
            except FileNotFoundError:
                pass
    cleanup = []
    for eachfiletype in ["csv", "dbf", "json", "shp", "shx", "txt"]:
        cleanup.extend(glob.glob(f"exports/*.{eachfiletype}"))
    for eachfile in cleanup:
        os.remove(eachfile)


def _write_gcps_to_file(
    fileinfo: dict,
    session: dict,
    gcps: list,
) -> None:
    """This function writes a CSV or text file with the parameters given."""
    if not fileinfo["headers"]:
        headers = [
            "label",
            fileinfo["coords"][0],
            fileinfo["coords"][1],
            fileinfo["coords"][2],
        ]
    else:
        headers = [
            eachheader.replace("|UTMZONE|", session["occupied_station_utmzone"])
            for eachheader in fileinfo["headers"]
        ]
    with open(
        f"exports/photogrammetry_gcps_gcps_for_{fileinfo['name']}.{fileinfo['type']}",
        "w",
    ) as f:
        if fileinfo["type"] == "csv":
            gcpfile = csv.DictWriter(
                f,
                fieldnames=headers,
            )
            if fileinfo["headers"]:
                gcpfile.writeheader()
            for eachgcp in gcps:
                gcpfile.writerow(
                    dict(
                        zip(
                            headers,
                            [
                                eachgcp["label"],
                                eachgcp[fileinfo["coords"][0]],
                                eachgcp[fileinfo["coords"][1]],
                                eachgcp[fileinfo["coords"][2]],
                            ],
                        )
                    )
                )
        elif fileinfo["type"] == "txt":
            for eachline in headers:
                f.write(f"{eachline}\n")
            for eachgcp in gcps:
                f.write(
                    f"{eachgcp['label']}\t{eachgcp[fileinfo['coords'][0]]}\t{eachgcp[fileinfo['coords'][1]]}\t{eachgcp[fileinfo['coords'][2]]}\n"
                )
