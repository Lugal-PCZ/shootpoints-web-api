PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE `classes` (
  `id` integer  NOT NULL PRIMARY KEY AUTOINCREMENT
,  `name` varchar(30) NOT NULL DEFAULT ''
);
INSERT INTO classes VALUES(1,'Operation');
INSERT INTO classes VALUES(2,'Architecture');
INSERT INTO classes VALUES(3,'Artifact');
INSERT INTO classes VALUES(4,'Feature');
CREATE TABLE `currentstate` (
  `sessions_id` integer  NOT NULL
,  `prism_vertical_distance` float NOT NULL DEFAULT '0'
,  `prism_latitude_distance` float NOT NULL DEFAULT '0'
,  `prism_longitude_distance` float NOT NULL DEFAULT '0'
,  `prism_radial_distance` float NOT NULL DEFAULT '0'
,  `prism_tangent_distance` float NOT NULL DEFAULT '0'
,  PRIMARY KEY (`sessions_id`)
,  CONSTRAINT `currentstate_ibfk_1` FOREIGN KEY (`sessions_id`) REFERENCES `sessions` (`id`)
);
CREATE TABLE `geometry` (
  `id` integer  NOT NULL PRIMARY KEY AUTOINCREMENT
,  `name` varchar(30) NOT NULL DEFAULT ''
,  `sequential` integer  NOT NULL DEFAULT '0'
,  UNIQUE (`name`)
);
INSERT INTO geometry VALUES(1,'Isolated Point',0);
INSERT INTO geometry VALUES(2,'Open Polygon',1);
INSERT INTO geometry VALUES(3,'Closed Polygon',1);
INSERT INTO geometry VALUES(4,'Point Cloud',0);
CREATE TABLE `groupings` (
  `id` integer  NOT NULL PRIMARY KEY AUTOINCREMENT
,  `label` varchar(30) NOT NULL DEFAULT ''
,  `geometry_id` integer  NOT NULL
,  `subclasses_id` integer  NOT NULL
,  CONSTRAINT `groupings_ibfk_1` FOREIGN KEY (`geometry_id`) REFERENCES `geometry` (`id`)
,  CONSTRAINT `groupings_ibfk_2` FOREIGN KEY (`subclasses_id`) REFERENCES `subclasses` (`id`)
);
CREATE TABLE `sessions` (
  `id` integer  NOT NULL PRIMARY KEY AUTOINCREMENT
,  `label` varchar(30) NOT NULL DEFAULT ''
,  `started` timestamp NOT NULL DEFAULT current_timestamp
,  `ended` timestamp NULL DEFAULT NULL
,  `surveyor` varchar(100) NOT NULL DEFAULT ''
,  `instrumentheight` float NOT NULL
,  `stations_id_occupied` integer  NOT NULL
,  `stations_id_backsight` integer  DEFAULT NULL
,  `azimuth` float  NOT NULL
,  CONSTRAINT `sessions_ibfk_1` FOREIGN KEY (`stations_id_occupied`) REFERENCES `stations` (`id`)
,  CONSTRAINT `sessions_ibfk_2` FOREIGN KEY (`stations_id_backsight`) REFERENCES `stations` (`id`)
);
CREATE TABLE `shots` (
  `id` integer  NOT NULL PRIMARY KEY AUTOINCREMENT
,  `sessions_id` integer  NOT NULL
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
,  `groupings_id` integer  NOT NULL
,  `sequenceingroup` integer  DEFAULT NULL
,  `label` varchar(30) DEFAULT NULL
,  `comment` text COLLATE BINARY
,  UNIQUE (`groupings_id`,`sequenceingroup`)
,  CONSTRAINT `shots_ibfk_1` FOREIGN KEY (`groupings_id`) REFERENCES `groupings` (`id`)
);
CREATE TABLE `stations` (
  `id` integer  NOT NULL PRIMARY KEY AUTOINCREMENT
,  `name` varchar(30) NOT NULL DEFAULT ''
,  `northing` float NOT NULL
,  `easting` float NOT NULL
,  `elevation` float NOT NULL
,  `utmzone` varchar(3) DEFAULT ''
,  `latitude` float DEFAULT NULL
,  `longitude` float DEFAULT NULL
,  UNIQUE (`name`)
);
CREATE TABLE `subclasses` (
  `id` integer  NOT NULL PRIMARY KEY AUTOINCREMENT
,  `classes_id` integer  NOT NULL
,  `name` varchar(30) NOT NULL DEFAULT ''
,  CONSTRAINT `subclasses_ibfk_1` FOREIGN KEY (`classes_id`) REFERENCES `classes` (`id`)
);
INSERT INTO subclasses VALUES(1,2,'Wall');
INSERT INTO subclasses VALUES(2,2,'Floor');
INSERT INTO subclasses VALUES(3,1,'Trench');
INSERT INTO subclasses VALUES(4,1,'Survey Station');
INSERT INTO subclasses VALUES(5,1,'Topography');
DELETE FROM sqlite_sequence;
INSERT INTO sqlite_sequence VALUES('classes',4);
INSERT INTO sqlite_sequence VALUES('geometry',4);
INSERT INTO sqlite_sequence VALUES('subclasses',5);
CREATE INDEX "idx_sessions_stations_id_occupied" ON "sessions" (`stations_id_occupied`);
CREATE INDEX "idx_sessions_stations_id_backsight" ON "sessions" (`stations_id_backsight`);
CREATE INDEX "idx_groupings_geometry_id" ON "groupings" (`geometry_id`);
CREATE INDEX "idx_groupings_subclasses_id" ON "groupings" (`subclasses_id`);
CREATE INDEX "idx_subclasses_classes_id" ON "subclasses" (`classes_id`);
COMMIT;
