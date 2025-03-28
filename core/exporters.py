"""This module handles exporting ShootPoints data."""

import csv
import datetime
import glob
import json
import os
import shapefile
import shutil
from pathlib import Path
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
    date = str(datetime.datetime.now()).split(" ")[0]
    with ZipFile(
        str(Path("exports") / "database.zip"), "w", compression=ZIP_DEFLATED
    ) as f:
        f.write(
            "ShootPoints.db",
            arcname=str(Path(f"ShootPoints Database {date}") / "ShootPoints.db"),
        )


def export_session_data(sessions_id: int) -> None:
    """This function creates a ZIP file of a session and its shots, for download by the browser."""
    spatialcontrol = []
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
        "  sites.id AS session_site_id, "
        "  sites.name AS session_site_name, "
        "  sites.description AS session_site_description, "
        "  sta_occ.id AS occupied_station_id, "
        "  sta_occ.name AS occupied_station_name, "
        "  sta_occ.description AS occupied_station_description, "
        "  sta_occ.northing AS occupied_station_northing, "
        "  sta_occ.easting AS occupied_station_easting, "
        "  sta_occ.elevation AS occupied_station_elevation, "
        "  sta_occ.utmzone AS occupied_station_utmzone, "
        "  sta_occ.latitude AS occupied_station_latitude, "
        "  sta_occ.longitude AS occupied_station_longitude, "
        "  CASE "
        "    WHEN sess.stations_id_backsight IS NOT NULL THEN 'Backsight' "
        "    WHEN sess.stations_id_resection_left IS NOT NULL THEN 'Resection' "
        "    ELSE 'Azimuth' "
        "  END AS session_type, "
        "  sta_bs.id AS backsight_station_id, "
        "  sta_bs.name AS backsight_station_name, "
        "  sta_bs.description AS backsight_station_description, "
        "  sta_bs.northing AS backsight_station_northing, "
        "  sta_bs.easting AS backsight_station_easting, "
        "  sta_bs.elevation AS backsight_station_elevation, "
        "  sta_bs.utmzone AS backsight_station_utmzone, "
        "  sta_bs.latitude AS backsight_station_latitude, "
        "  sta_bs.longitude AS backsight_station_longitude, "
        "  sta_rsl.id AS resection_station_left_id, "
        "  sta_rsl.name AS resection_station_left_name, "
        "  sta_rsl.description AS resection_station_left_description, "
        "  sta_rsl.northing AS resection_station_left_northing, "
        "  sta_rsl.easting AS resection_station_left_easting, "
        "  sta_rsl.elevation AS resection_station_left_elevation, "
        "  sta_rsl.utmzone AS resection_station_left_utmzone, "
        "  sta_rsl.latitude AS resection_station_left_latitude, "
        "  sta_rsl.longitude AS resection_station_left_longitude, "
        "  sta_rsr.id AS resection_station_right_id, "
        "  sta_rsr.name AS resection_station_right_name, "
        "  sta_rsr.description AS resection_station_right_description, "
        "  sta_rsr.northing AS resection_station_right_northing, "
        "  sta_rsr.easting AS resection_station_right_easting, "
        "  sta_rsr.elevation AS resection_station_right_elevation, "
        "  sta_rsr.utmzone AS resection_station_right_utmzone, "
        "  sta_rsr.latitude AS resection_station_right_latitude, "
        "  sta_rsr.longitude AS resection_station_right_longitude, "
        "  sess.azimuth AS session_azimuth, "
        "  sess.instrumentheight AS session_instrumentheight, "
        "  sess.pressure AS session_pressure, "
        "  sess.temperature AS session_temperature, "
        "  count(DISTINCT grp.id) AS data_number_of_groupings, "
        "  count(shots.id) AS data_number_of_shots "
        "FROM sessions sess "
        "JOIN stations sta_occ ON sess.stations_id_occupied = sta_occ.id "
        "JOIN sites ON sta_occ.sites_id = sites.id "
        "LEFT OUTER JOIN stations sta_bs ON sess.stations_id_backsight = sta_bs.id "
        "LEFT OUTER JOIN stations sta_rsl ON sess.stations_id_resection_left = sta_rsl.id "
        "LEFT OUTER JOIN stations sta_rsr ON sess.stations_id_resection_right = sta_rsr.id "
        "LEFT OUTER JOIN groupings grp ON grp.sessions_id = sess.id "
        "LEFT OUTER JOIN shots ON shots.groupings_id = grp.id "
        "WHERE sess.id = ?"
    )
    sessiondata = database._read_from_database(sql, (sessions_id,))["results"][0]
    session = {"session": {}}
    occupied_station = {}
    backsight_station = {}
    resection_station_left = {}
    resection_station_right = {}
    for key, val in sessiondata.items():
        if key.startswith("session_"):
            session["session"][key[8:]] = val
        elif key.startswith("occupied_station_"):
            occupied_station[key[17:]] = val
        elif key.startswith("backsight_station_"):
            backsight_station[key[18:]] = val
        elif key.startswith("resection_station_left_"):
            resection_station_left[key[23:]] = val
        elif key.startswith("resection_station_right_"):
            resection_station_right[key[24:]] = val
        elif key.startswith("data_"):
            session["session"][key[5:]] = val
    session["session"]["occupied_station"] = occupied_station
    spatialcontrol.append(
        {
            "id": occupied_station["id"],
            "name": occupied_station["name"],
            "descr": occupied_station["description"],
            "type": "Occupied Station",
            "N": occupied_station["northing"],
            "E": occupied_station["easting"],
            "Z": occupied_station["elevation"],
        }
    )
    if sessiondata["session_type"] == "Backsight":
        session["session"]["backsight_station"] = backsight_station
        spatialcontrol.append(
            {
                "id": backsight_station["id"],
                "name": backsight_station["name"],
                "descr": backsight_station["description"],
                "type": "Backsight Station",
                "N": backsight_station["northing"],
                "E": backsight_station["easting"],
                "Z": backsight_station["elevation"],
            }
        )
    elif sessiondata["session_type"] == "Resection":
        session["session"]["resection_station_left"] = resection_station_left
        spatialcontrol.append(
            {
                "id": resection_station_left["id"],
                "name": resection_station_left["name"],
                "descr": resection_station_left["description"],
                "type": "Left Resection Reference Station",
                "N": resection_station_left["northing"],
                "E": resection_station_left["easting"],
                "Z": resection_station_left["elevation"],
            }
        )
        session["session"]["resection_station_right"] = resection_station_right
        spatialcontrol.append(
            {
                "id": resection_station_right["id"],
                "name": resection_station_right["name"],
                "descr": resection_station_right["description"],
                "type": "Right Resection Reference Station",
                "N": resection_station_right["northing"],
                "E": resection_station_right["easting"],
                "Z": resection_station_right["elevation"],
            }
        )
    with open(str(Path("exports") / "session_info.json"), "w", encoding="utf8") as f:
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
        shotsdata = database._read_from_database(sql, (sessions_id,))["results"]
        # Save all shots to a flat CSV file.
        with open(
            str(Path("exports") / "shots_data.csv"), "w", encoding="utf8", newline=""
        ) as f:
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
    prjfile = (
        str(
            Path("core")
            / "prj_templates"
            / f"{sessiondata['occupied_station_utmzone']}.txt"
        )
        if sessiondata["occupied_station_utmzone"]
        else ""
    )
    with shapefile.Writer(
        str(Path("exports") / "gis_shapefiles_spatialcontrol"),
        shapeType=shapefile.POINTZ,
    ) as w:
        w.field("id", "N")
        w.field("name", "C")
        w.field("descr", "C")
        w.field("type", "C")
        w.field("N", "N", decimal=3)
        w.field("E", "N", decimal=3)
        w.field("Z", "N", decimal=3)
        for eachstation in spatialcontrol:
            w.record(*tuple(eachstation.values()))
            w.pointz(eachstation["E"], eachstation["N"], eachstation["Z"])
        if prjfile:
            shutil.copy2(
                prjfile,
                str(Path("exports") / "gis_shapefiles_spatialcontrol.prj"),
            )
    if allshots:
        with shapefile.Writer(
            str(Path("exports") / "gis_shapefiles_allshots"), shapeType=shapefile.POINTZ
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
            if prjfile:
                shutil.copy2(
                    prjfile,
                    str(Path("exports") / "gis_shapefiles_allshots.prj"),
                )
    if closedpolygons:
        with shapefile.Writer(
            str(Path("exports") / "gis_shapefiles_closedpolygons"),
            shapeType=shapefile.POLYGONZ,
        ) as w:
            w.field("group_id", "N")
            w.field("label", "C")
            w.field("descr", "C")
            w.field("class", "C")
            w.field("subclass", "C")
            for eachgroup in closedpolygons:
                w.record(*tuple(eachgroup[0].values()))
                w.polyz([eachgroup[1]])
            if prjfile:
                shutil.copy2(
                    prjfile,
                    str(Path("exports") / "gis_shapefiles_closedpolygons.prj"),
                )
    if openpolygons:
        with shapefile.Writer(
            str(Path("exports") / "gis_shapefiles_openpolygons"),
            shapeType=shapefile.POLYLINEZ,
        ) as w:
            w.field("group_id", "N")
            w.field("label", "C")
            w.field("descr", "C")
            w.field("class", "C")
            w.field("subclass", "C")
            for eachgroup in openpolygons:
                w.record(*tuple(eachgroup[0].values()))
                w.linez([eachgroup[1]])
            if prjfile:
                shutil.copy2(
                    prjfile,
                    str(Path("exports") / "gis_shapefiles_openpolygons.prj"),
                )
    if pointclouds:
        with shapefile.Writer(
            str(Path("exports") / "gis_shapefiles_pointclouds"),
            shapeType=shapefile.MULTIPOINTZ,
        ) as w:
            w.field("group_id", "N")
            w.field("label", "C")
            w.field("descr", "C")
            w.field("class", "C")
            w.field("subclass", "C")
            for eachgroup in pointclouds:
                w.record(*tuple(eachgroup[0].values()))
                w.multipointz(eachgroup[1])
            if prjfile:
                shutil.copy2(
                    prjfile,
                    str(Path("exports") / "gis_shapefiles_pointclouds.prj"),
                )
    if gcps:
        for eachfile in gcpfiles:
            _write_gcps_to_file(eachfile, sessiondata, gcps)

    # Finally, bundle up all the export files into a ZIP archive for download.
    filesinarchive = [
        "session_info.json",
        "shots_data.csv",
    ]
    for eachfile in [
        "spatialcontrol",
        "allshots",
        "closedpolygons",
        "openpolygons",
        "pointclouds",
    ]:
        for eachext in ["dbf", "shp", "shx", "prj"]:
            filesinarchive.append(str(Path("gis_shapefiles") / f"{eachfile}.{eachext}"))
    for eachfile in gcpfiles:
        filesinarchive.append(
            str(
                Path("photogrammetry_gcps")
                / f"gcps_for_{eachfile['name']}.{eachfile['type']}"
            )
        )
    archivename = f"ShootPoints Data ({sessiondata['session_label'].replace('/', '_').replace(':', '_').replace(chr(92), '_')})"
    with ZipFile(
        str(Path("exports") / "export.zip"), "w", compression=ZIP_DEFLATED
    ) as f:
        for eachfile in filesinarchive:
            try:
                f.write(
                    str(
                        Path("exports")
                        / f"{eachfile.replace('/', '_').replace(chr(92), '_')}"
                    ),
                    arcname=str(Path(archivename) / eachfile),
                )
            except FileNotFoundError:
                pass
    cleanup = []
    for eachfiletype in ["csv", "dbf", "json", "prj", "shp", "shx", "txt"]:
        cleanup.extend(glob.glob(str(Path("exports") / f"*.{eachfiletype}")))
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
        str(
            Path("exports")
            / f"photogrammetry_gcps_gcps_for_{fileinfo['name']}.{fileinfo['type']}"
        ),
        "w",
        encoding="utf8",
        newline="",
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
