```
  ____   _                    _    ____         _         _         __        __     _     
 / ___| | |__    ___    ___  | |_ |  _ \  ___  (_) _ __  | |_  ___  \ \      / /___ | |__  
 \___ \ | '_ \  / _ \  / _ \ | __|| |_) |/ _ \ | || '_ \ | __|/ __|  \ \ /\ / // _ \| '_ \ 
  ___) || | | || (_) || (_) || |_ |  __/| (_) || || | | || |_ \__ \   \ V  V /|  __/| |_) |
 |____/ |_| |_| \___/  \___/  \__||_|    \___/ |_||_| |_| \__||___/    \_/\_/  \___||_.__/ 
```


# Overview
ShootPoints Web is a set of programs for total station surveying. Based on the SiteMap surveying package originally developed at the Museum Applied Science Center for Archaeology (MASCA) at the University of Pennsylvania Museum, ShootPoints Web streamlines and simplifies total station operation and data collection on archaeological excavations.

ShootPoints Web consists of two interrelated projects: shootpoints-web-api and shootpoints-web-frontend. shootpoints-web-api can be run as a standalone program from the command line, but it is most easily operated through the web interface provided by shootpoints-web-frontend.

shootpoints-web-api communicates with the total station via a serial connection. Though it can be run from a laptop connected directly to the total station, it is intended to be installed on a dedicated Raspberry Pi mounted on the tripod of the total station, and controlled wirelessly via the web from a tablet on a local wifi network.


# Requirements
shootpoints-web-api is written for Python 3.8 and later. Python versions as early as 3.6 may work, but have not been tested.

ShootPoints Web’s processing and storage requirements are minimal, and it runs well on Raspberry Pi 2 Model B and better SBCs.

Serial communications protocols have only been created for Topcon GTS-300 series total stations, but ShootPoint Web’s modular design means that other makes and models of total station will be added in the future.

shootpoints-web-api requires the following third-party Python packages, installation instructions for which are provided below:
- fastapi
- pyserial
- python-multipart
- utm
- uvicorn

shootpoints-web-frontend requires the [Mustache](http://mustache.github.io) JavaScript library. Because ShootPoints Web is expected to be run on a local wifi network without internet access, Mustache is installed locally, as shown below.


# Installation
## Clone ShootPoints Web into your project directory:
```bash
cd <path/to/your/installation/>
git clone https://github.com/Lugal-PCZ/shootpoints-web-api.git
git clone https://github.com/Lugal-PCZ/shootpoints-web-frontend.git
```

## Install required Python packages:
```bash
pip3 install -r shootpoints-web-api/requirement.txt
```

## Install Mustache:
```bash
curl -LO https://unpkg.com/mustache@latest/mustache.min.js
mv mustache.min.js <path/to/your/installation/>shootpoints-web-frontend/lib/
```


# Quick Start
These instructions presume that you will be installing ShootPoints Web on a laptop or desktop computer for initial testing purposes. Instructions for installing ShootPoints Web on a Raspberry Pi for fieldwork are forthcoming.

By default, shootpoints-web-api will launch in “demo” mode with no serial connection and simulated shot data so you can familiarize yourself with the software without a total station. This, however, can be easily overridden for testing with an actual live connection to a supported total station.

## Data Management and Categorization
Following the model developed for SiteMap, ShootPoints Web categorizes shot data to simplify its interpretation and visualization. The two primary categorizations are groupings (collections of related points) and class/subclass (archaeological metadata about the shots). All data are saved to a local database which can be downloaded *in toto* or exported as CSV files via the web interface.

ShootPoints Web will not let you begin collecting data without the proper prerequisites (site, station coordinates, and surveying session).

### Geometries
Every measurement taken with ShootPoints Web is part of a grouping, which can be any of the following four geometries:
* **Isolated Point**: A discrete point that encapsulates granular information such as a point elevation or the location of a small artifact.
* **Point Cloud**: Multiple non-sequential point samples that do not carry information individually but as elements of a group that together describe an entity (such as topography).
* **Open Polygon**: Multiple sequential points that trace an outline wherein the start and end points do not connect.
* **Closed Polygon**: Multiple sequential points that trace an outline wherein the start point is connected to the end point.

### Classes and Subclasses
Each grouping also is assigned a class and subclass to assist in categorization and visualization of the data collected. The following classes and subclasses are populated in the ShootPoints database with a fresh install, but new ones can be added and removed under the “Setup” section, as is appropriate for your site.
* **Architecture**: Human-built structures.
  * **Wall**: Vertical, human-made, constructions that enclose, divide, or delimit space.
  * **Floor**: Prepared surfaces upon which human activities took place.
* **Artifact**: Objects made, modified, or used by people.
* **Feature**: Natural formations or immovable, non-architectural, human creations.
  * **Topography**: Ground surface.
* **Operation**: Excavation units, controls, grids, and measurements.
  * **Survey Station**: Benchmarks for survey station setup or backsights.
  * **Trench**: Excavation units.
  * **GCP**: Photogrammetry ground control points.

## ShootPoints Web Interface
ShootPoints Web’s interface has five primary components:

![ShootPoints Web interface overview](https://github.com/Lugal-PCZ/readme-images/blob/main/shootpoints-web-frontend_Overview.png?raw=true)
1. **On-The-Fly Adjustments**: Click the arrows icon in the upper left to set atmospheric corrections and prism offsets, which may vary from one shot to the next.
2. **Utilities**: Click the gears icon in the upper right to download data or delete a surveying session. Also, if ShootPoints Web is running on a Raspberry Pi, you will have options to set its system clock and safely shut it down.
3. **Output Box**: The results of your commands will be displayed here.
4. **“Setup” Section**: Expand this area to input values that should be set prior to beginning surveying, such as your site, total station benchmarks, and class/subclass.
5. **“Surveying” Section**: Expand this area to collect data with the total station.

## Start the ShootPoints Web software:
```bash
cd <path/to/your/installation/>shootpoints-web-api/
uvicorn api:app --host 0.0.0.0
```

Open a web browser on your computer and access ShootPoint Web’s interface at [http://localhost:8000/](http://localhost:8000/) or else open a web browser on a device connected to the same wifi network and navigate to [http://<your.computer's.ip.address>:8000/](http://<your.computer's.ip.address>:8000/).

## Save a new site:
1. Expand the “Setup” section.
2. Enter a name for the new site.
3. (*optional*) Enter a description for the new site.
4. Click the “Save New Site” button.  
![Save New Site form](https://github.com/Lugal-PCZ/readme-images/blob/main/shootpoints-web-frontend_SaveNewSite.png?raw=true)

## Save a new station:
1. Choose the site where this survey station is located.
2. Enter a name for the new station.
3. (*optional*) Enter a description for the new station.
4. Choose the coordinate system.
5. Enter the station coordinates.
6. Click the “Save New Station” button.  
![Save New Station form](https://github.com/Lugal-PCZ/readme-images/blob/main/shootpoints-web-frontend_SaveNewStation.png?raw=true)

Add additional stations if you’re working with an existing site with multiple benchmarks with known coordinates.

## Start a new surveying session:
(*If you’re testing with a total station, be sure that it is set up properly, turned on, and connected to your computer’s serial port. Also verify that the proper serial port is selected under the “Set Configs” form of the “Setup” section.*)
1. Minimize the “Setup” section and expand the “Surveying” section.
2. Enter a label for the new surveying session.
3. Enter your name or initials as the responsible surveyor.
4. Choose the site.
5. Choose the occupied point (the station over which the total station is set up).
6. Choose the session type (note: choose “Azimuth,” if you’re in demo mode):
   * **Azimuth**: You will aim the total station at a known landmark, enter the bearing to that landmark, and measure the instrument height by hand.
     * Enter the height (in meters) of the total station above the occupied point and azimuth (in dd.mmss format) to the known landmark.
   * **Backsight**: You will to shoot a point between two pre-set stations with known coordinates and have ShootPoints Web calculate the azimuth and instrument height.
     * Select the backsight station and enter the height (in meters) of the prism pole.
7. Click the “Start New Session” button.  
![Start New Session form](https://github.com/Lugal-PCZ/readme-images/blob/main/shootpoints-web-frontend_StartNewSession.png?raw=true)
10. When prompted to check, verify that the atmospheric conditions and time displayed in the page header are correct. If they aren’t, dismiss the dialog and click the “On-The-Fly” Adjustments (arrows) icon in the upper left and/or the “Utilities” (gears) icon in the upper right to make the necessary adjustments.
11. If the atmospheric conditions and system clock are correct, aim the total station at the landmark or the backsight prism and click “OK” to start the new surveying session.  
![“Please verify” dialog box](https://github.com/Lugal-PCZ/readme-images/blob/main/shootpoints-web-frontend_PleaseVerify.png?raw=true)

## Create a new grouping:
1. Enter a label for the grouping.
2. Select the appropriate geometry.
3. Select the class and subclass of this grouping.
4. (*optional*) Enter a description for the new grouping.
5. Click the “Start New Grouping” button.  
![Start New Grouping form](https://github.com/Lugal-PCZ/readme-images/blob/main/shootpoints-web-frontend_StartNewGrouping.png?raw=true)


## Collect data:
1. Aim the total station at the prism.
2. Click the “Take Shot” button.  
![Take Shot button](https://github.com/Lugal-PCZ/readme-images/blob/main/shootpoints-web-frontend_TakeShot.png?raw=true)
3. While the shot is being taken, you can click the “Cancel Shot” button to abort.
4. After the shot data have been returned from the total station, you will be given the option to save the shot or discard the data.
5. (*optional*) If saving the shot, you can add a comment such as “NE corner” or “broken edge” to assist your interpretation of the data later.  
![Save Last Shot form](https://github.com/Lugal-PCZ/readme-images/blob/main/shootpoints-web-frontend_SaveLastShot.png?raw=true)

Continue taking shots, each of which will be saved to the current grouping. To begin taking shots in a new grouping, simply create a new grouping as described above.

Note that any grouping shot with an “Isolated Point” geometry can logically only have one shot saved to it, so if you’re taking a series of these (such as is typical of end-of-day point elevations in a trench), you will need to create a new grouping for each shot. Though this sounds needlessly cumbersome, in practice it is a quick process and ensures that your data are marked consistently.
