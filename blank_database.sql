PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE `classes` (
  `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT
,  `name` TEXT COLLATE NOCASE NOT NULL
,  `description` TEXT DEFAULT NULL
,  UNIQUE (`name`)
);
INSERT INTO classes VALUES(1,'Operation','Excavation units, controls, grids, and measurements.');
INSERT INTO classes VALUES(2,'Architecture','Human-built structures.');
INSERT INTO classes VALUES(3,'Artifact','Objects made, modified, or used by people.');
INSERT INTO classes VALUES(4,'Feature','Natural formations or immovable, non-architectural, human creations.');
CREATE TABLE `geometries` (
  `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT
,  `name` TEXT COLLATE NOCASE NOT NULL
,  `sequential` INTEGER NOT NULL DEFAULT 0
,  `description` TEXT NOT NULL
,  UNIQUE (`name`)
);
INSERT INTO geometries VALUES(1,'Isolated Point',0,'A discrete point that encapsulates granular information such as a point elevation or the location of a small artifact.');
INSERT INTO geometries VALUES(2,'Point Cloud',0,'Multiple non-sequential point samples that do not carry information individually but as elements of a group that together describe an entity (such as topography).');
INSERT INTO geometries VALUES(3,'Open Polygon',1,'Multiple sequential points that trace an outline wherein the start and end points do not connect (such as in a shapefile linestring).');
INSERT INTO geometries VALUES(4,'Closed Polygon',1,'Multiple sequential points that trace an outline wherein the start point is connected to the end point (such as in a shapefile polygon).');
CREATE TABLE `groupings` (
  `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT
,  `sessions_id` INTEGER NOT NULL
,  `geometries_id` INTEGER NOT NULL
,  `subclasses_id` INTEGER NOT NULL
,  `label` TEXT NOT NULL
,  `description` TEXT DEFAULT NULL
,  CONSTRAINT `groupings_ibfk_1` FOREIGN KEY (`sessions_id`) REFERENCES `sessions` (`id`)
,  CONSTRAINT `groupings_ibfk_2` FOREIGN KEY (`geometries_id`) REFERENCES `geometries` (`id`)
,  CONSTRAINT `groupings_ibfk_3` FOREIGN KEY (`subclasses_id`) REFERENCES `subclasses` (`id`)
);
CREATE TABLE `savedstate` (
  `vertical_distance` REAL NOT NULL DEFAULT 0
,  `latitude_distance` REAL NOT NULL DEFAULT 0
,  `longitude_distance` REAL NOT NULL DEFAULT 0
,  `radial_distance` REAL NOT NULL DEFAULT 0
,  `tangent_distance` REAL NOT NULL DEFAULT 0
,  `wedge_distance` REAL NOT NULL DEFAULT 0
,  `pressure` INTEGER NOT NULL DEFAULT 760
,  `temperature` INTEGER NOT NULL DEFAULT 15
,  `currentsession` INTEGER NOT NULL DEFAULT 0
,  `currentgrouping` INTEGER NOT NULL DEFAULT 0
);
INSERT INTO savedstate VALUES(0.0,0.0,0.0,0.0,0.0,0.0,760,15,0,0);
CREATE TABLE `sessions` (
  `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT
,  `label` TEXT NOT NULL
,  `started` TEXT NULL DEFAULT current_timestamp
,  `surveyor` TEXT NOT NULL
,  `stations_id_occupied` INTEGER NOT NULL
,  `stations_id_backsight` INTEGER  DEFAULT NULL
,  `stations_id_resection_left` INTEGER  DEFAULT NULL
,  `stations_id_resection_right` INTEGER  DEFAULT NULL
,  `azimuth` TEXT NOT NULL DEFAULT '0° 0'' 0"'
,  `instrumentheight` REAL NOT NULL
,  `pressure` INTEGER NOT NULL DEFAULT 760
,  `temperature` INTEGER NOT NULL DEFAULT 15
,  CONSTRAINT `sessions_ibfk_1` FOREIGN KEY (`stations_id_occupied`) REFERENCES `stations` (`id`)
,  CONSTRAINT `sessions_ibfk_2` FOREIGN KEY (`stations_id_backsight`) REFERENCES `stations` (`id`)
,  CONSTRAINT `sessions_ibfk_3` FOREIGN KEY (`stations_id_resection_left`) REFERENCES `stations` (`id`)
,  CONSTRAINT `sessions_ibfk_4` FOREIGN KEY (`stations_id_resection_right`) REFERENCES `stations` (`id`)
);
CREATE TABLE `setuperrors` (
  `error` TEXT NOT NULL
,  PRIMARY KEY (`error`)
);
CREATE TABLE `shots` (
  `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT
,  `groupings_id` INTEGER NOT NULL
,  `comment` TEXT DEFAULT NULL
,  `timestamp` TEXT NOT NULL DEFAULT current_timestamp
,  `pressure` INTEGER NOT NULL DEFAULT 760
,  `temperature` INTEGER NOT NULL DEFAULT 15
,  `delta_n` REAL NOT NULL
,  `delta_e` REAL NOT NULL
,  `delta_z` REAL NOT NULL
,  `prismoffset_vertical` REAL NOT NULL DEFAULT 0
,  `prismoffset_latitude` REAL NOT NULL DEFAULT 0
,  `prismoffset_longitude` REAL NOT NULL DEFAULT 0
,  `prismoffset_radial` REAL NOT NULL DEFAULT 0
,  `prismoffset_tangent` REAL NOT NULL DEFAULT 0
,  `prismoffset_wedge` REAL NOT NULL DEFAULT 0
,  `northing` REAL NOT NULL
,  `easting` REAL NOT NULL
,  `elevation` REAL NOT NULL
,  CONSTRAINT `shots_ibfk_1` FOREIGN KEY (`groupings_id`) REFERENCES `groupings` (`id`)
);
CREATE TABLE `sites` (
  `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT
,  `name` TEXT COLLATE NOCASE NOT NULL
,  `description` TEXT DEFAULT NULL
,  UNIQUE (`name`)
);
CREATE TABLE `stations` (
  `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT
,  `sites_id` INTEGER NOT NULL
,  `name` TEXT COLLATE NOCASE NOT NULL
,  `description` TEXT DEFAULT NULL
,  `northing` REAL NOT NULL
,  `easting` REAL NOT NULL
,  `elevation` REAL NOT NULL
,  `utmzone` TEXT DEFAULT ''
,  `latitude` REAL DEFAULT NULL
,  `longitude` REAL DEFAULT NULL
,  UNIQUE (`name`,`sites_id`)
,  UNIQUE (`northing`,`easting`,`sites_id`)
,  CONSTRAINT `shots_ibfk_1` FOREIGN KEY (`sites_id`) REFERENCES `sites` (`id`)
);
CREATE TABLE `subclasses` (
  `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT
,  `classes_id` INTEGER NOT NULL
,  `name` TEXT COLLATE NOCASE NOT NULL
,  `description` TEXT DEFAULT NULL
,  UNIQUE (`classes_id`,`name`)
,  CONSTRAINT `subclasses_ibfk_1` FOREIGN KEY (`classes_id`) REFERENCES `classes` (`id`)
);
INSERT INTO subclasses VALUES(1,1,'Survey Station','Benchmarks for survey station setup or backsights.');
INSERT INTO subclasses VALUES(2,1,'Grid','Site or survey grid.');
INSERT INTO subclasses VALUES(3,1,'Trench','Excavation units.');
INSERT INTO subclasses VALUES(4,1,'Elevation Control Point','Control point for taking local elevations, as with a string and bubble level.');
INSERT INTO subclasses VALUES(5,1,'GCP','Photogrammetry ground control points.');
INSERT INTO subclasses VALUES(6,2,'Wall','Vertical, human-made, constructions that enclose, divide, or delimit space.');
INSERT INTO subclasses VALUES(7,2,'Floor','Level surfaces upon which human activities took place.');
INSERT INTO subclasses VALUES(8,4,'Topography','Ground surface.');
INSERT INTO subclasses VALUES(9,4,'Pit','Hole or depression that cuts through lower stratigraphic layers.');
DELETE FROM sqlite_sequence;
INSERT INTO sqlite_sequence VALUES('classes',4);
INSERT INTO sqlite_sequence VALUES('geometries',4);
INSERT INTO sqlite_sequence VALUES('subclasses',5);
CREATE INDEX "idx_sessions_stations_id_occupied" ON "sessions" (`stations_id_occupied`);
CREATE INDEX "idx_sessions_stations_id_backsight" ON "sessions" (`stations_id_backsight`);
CREATE INDEX "idx_groupings_sessions_id" ON "groupings" (`sessions_id`);
CREATE INDEX "idx_groupings_geometries_id" ON "groupings" (`geometries_id`);
CREATE INDEX "idx_groupings_subclasses_id" ON "groupings" (`subclasses_id`);
COMMIT;
PRAGMA foreign_keys=ON;
