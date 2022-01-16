PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE `classes` (
  `id` integer NOT NULL PRIMARY KEY AUTOINCREMENT
,  `name` varchar(30) NOT NULL
,  `description` varchar(200) DEFAULT NULL
,  UNIQUE (`name`)
);
INSERT INTO classes VALUES(1,'Operation','Excavation units, controls, grids, and measurements.');
INSERT INTO classes VALUES(2,'Architecture','Human-built structures.');
INSERT INTO classes VALUES(3,'Artifact','Objects made, modified, or used by people.');
INSERT INTO classes VALUES(4,'Feature','Natural formations or immovable, non-architectural, human creations.');
CREATE TABLE `geometry` (
  `id` integer NOT NULL PRIMARY KEY AUTOINCREMENT
,  `name` varchar(30) NOT NULL
,  `sequential` integer NOT NULL DEFAULT '0'
,  `description` varchar(200) NOT NULL
,  UNIQUE (`name`)
);
INSERT INTO geometry VALUES(1,'Isolated Point',0,'Individual point that encapsulates granular information such as a point elevation or the location of a small artifact.');
INSERT INTO geometry VALUES(2,'Point Cloud',0,'Multiple non-sequential point samples that do not carry information individually but as elements of a group that in toto describes an entity such as topography.');
INSERT INTO geometry VALUES(3,'Open Polygon',1,'Multiple sequential points that trace an outline wherein the start and end points do not connect.');
INSERT INTO geometry VALUES(4,'Closed Polygon',1,'Multiple sequential points that trace an outline wherein the start point is connected to the end point.');
CREATE TABLE `groupings` (
  `id` integer NOT NULL PRIMARY KEY AUTOINCREMENT
,  `sessions_id` integer NOT NULL
,  `geometry_id` integer NOT NULL
,  `subclasses_id` integer NOT NULL
,  `label` varchar(30) NOT NULL
,  `description` varchar(200) DEFAULT NULL
,  CONSTRAINT `groupings_ibfk_1` FOREIGN KEY (`sessions_id`) REFERENCES `sessions` (`id`)
,  CONSTRAINT `groupings_ibfk_2` FOREIGN KEY (`geometry_id`) REFERENCES `geometry` (`id`)
,  CONSTRAINT `groupings_ibfk_3` FOREIGN KEY (`subclasses_id`) REFERENCES `subclasses` (`id`)
);
CREATE TABLE `savedstate` (
  `vertical_distance` float NOT NULL DEFAULT '0'
,  `latitude_distance` float NOT NULL DEFAULT '0'
,  `longitude_distance` float NOT NULL DEFAULT '0'
,  `radial_distance` float NOT NULL DEFAULT '0'
,  `tangent_distance` float NOT NULL DEFAULT '0'
,  `wedge_distance` float NOT NULL DEFAULT '0'
,  `pressure` integer NOT NULL DEFAULT 760
,  `temperature` integer NOT NULL DEFAULT 15
);
INSERT INTO savedstate VALUES(0.0,0.0,0.0,0.0,0.0,0.0,760,15);
CREATE TABLE `sessions` (
  `id` integer NOT NULL PRIMARY KEY AUTOINCREMENT
,  `label` varchar(30) NOT NULL
,  `started` timestamp NULL DEFAULT current_timestamp
,  `surveyor` varchar(100) NOT NULL
,  `sites_id` integer NOT NULL
,  `stations_id_occupied` integer NOT NULL
,  `stations_id_backsight` integer  DEFAULT NULL
,  `azimuth` varchar(12) NOT NULL DEFAULT '0°0''0"'
,  `instrumentheight` float NOT NULL
,  CONSTRAINT `sessions_ibfk_1` FOREIGN KEY (`sites_id`) REFERENCES `sites` (`id`)
,  CONSTRAINT `sessions_ibfk_2` FOREIGN KEY (`stations_id_occupied`) REFERENCES `stations` (`id`)
,  CONSTRAINT `sessions_ibfk_3` FOREIGN KEY (`stations_id_backsight`) REFERENCES `stations` (`id`)
);
CREATE TABLE `setuperrors` (
  `error` varchar(200) NOT NULL
,  PRIMARY KEY (`error`)
);
CREATE TABLE `shots` (
  `id` integer NOT NULL PRIMARY KEY AUTOINCREMENT
,  `groupings_id` integer NOT NULL
,  `label` varchar(30) DEFAULT NULL
,  `comment` text COLLATE BINARY DEFAULT NULL
,  `timestamp` timestamp NOT NULL DEFAULT current_timestamp
,  `delta_n` float NOT NULL
,  `delta_e` float NOT NULL
,  `delta_z` float NOT NULL
,  `northing` float NOT NULL
,  `easting` float NOT NULL
,  `elevation` float NOT NULL
,  `prismoffset_vertical` float NOT NULL DEFAULT '0'
,  `prismoffset_latitude` float NOT NULL DEFAULT '0'
,  `prismoffset_longitude` float NOT NULL DEFAULT '0'
,  `prismoffset_radial` float NOT NULL DEFAULT '0'
,  `prismoffset_tangent` float NOT NULL DEFAULT '0'
,  `prismoffset_wedge` float NOT NULL DEFAULT '0'
,  CONSTRAINT `shots_ibfk_1` FOREIGN KEY (`groupings_id`) REFERENCES `groupings` (`id`)
);
CREATE TABLE `sites` (
  `id` integer NOT NULL PRIMARY KEY AUTOINCREMENT
,  `name` varchar(30) NOT NULL
,  `description` varchar(200) DEFAULT NULL
,  UNIQUE (`name`)
);
CREATE TABLE `stations` (
  `id` integer NOT NULL PRIMARY KEY AUTOINCREMENT
,  `sites_id` integer NOT NULL
,  `name` varchar(30) NOT NULL
,  `northing` float NOT NULL
,  `easting` float NOT NULL
,  `elevation` float NOT NULL
,  `utmzone` varchar(3) DEFAULT ''
,  `latitude` float DEFAULT NULL
,  `longitude` float DEFAULT NULL
,  `description` varchar(200) DEFAULT NULL
,  UNIQUE (`name`,`sites_id`)
,  UNIQUE (`northing`,`easting`,`sites_id`)
,  CONSTRAINT `shots_ibfk_1` FOREIGN KEY (`sites_id`) REFERENCES `sites` (`id`)
);
CREATE TABLE `subclasses` (
  `id` integer NOT NULL PRIMARY KEY AUTOINCREMENT
,  `classes_id` integer NOT NULL
,  `name` varchar(30) NOT NULL
,  `description` varchar(200) DEFAULT NULL
,  UNIQUE (`classes_id`,`name`)
,  CONSTRAINT `subclasses_ibfk_1` FOREIGN KEY (`classes_id`) REFERENCES `classes` (`id`)
);
INSERT INTO subclasses VALUES(1,1,'Survey Station','Discrete surveying control points.');
INSERT INTO subclasses VALUES(2,1,'Trench','Excavation units.');
INSERT INTO subclasses VALUES(3,2,'Wall','Vertical, human-made, constructions, enclosing, dividing, or delimiting space.');
INSERT INTO subclasses VALUES(4,2,'Floor','Prepared surfaces upon which human activities took place.');
INSERT INTO subclasses VALUES(5,4,'Topography','Ground surface.');
DELETE FROM sqlite_sequence;
INSERT INTO sqlite_sequence VALUES('classes',4);
INSERT INTO sqlite_sequence VALUES('geometry',4);
INSERT INTO sqlite_sequence VALUES('subclasses',5);
CREATE INDEX "idx_sessions_stations_id_occupied" ON "sessions" (`stations_id_occupied`);
CREATE INDEX "idx_sessions_stations_id_backsight" ON "sessions" (`stations_id_backsight`);
CREATE INDEX "idx_groupings_sessions_id" ON "groupings" (`sessions_id`);
CREATE INDEX "idx_groupings_geometry_id" ON "groupings" (`geometry_id`);
CREATE INDEX "idx_groupings_subclasses_id" ON "groupings" (`subclasses_id`);
COMMIT;
PRAGMA foreign_keys=ON;
