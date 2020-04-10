# TODO: initialized will reset whenever the flask instance is restarted or the app is opened in a new browser/window--in which case you'll have to re-load prism and station from the DB
initialized = False

# Backsight takes:
#   NEZ of occupied point
#   NEZ of known point
#   Prism vertical offset
# ...and takes a measurement
# ...with which it can calculate and set:
#   Height of instrument
#   Azimuth between the occupied point and the known point

# Manual Setup takes:
#   NEZ of occupied point
#   Height of instrument
#   Azimuth to a known landmark
# ...and should warn the surveyor to set the prism height when shooting points
