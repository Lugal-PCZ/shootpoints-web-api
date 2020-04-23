from fastapi import FastAPI, Response

import engine


app = FastAPI()


@app.post('/azimuth/')
def azimuth_set(response: Response, degrees: int=0, minutes: int=0, seconds: int=0):
    """Sets the azimuth on the total station."""
    result = engine.total_station.set_azimuth(degrees, minutes, seconds)
    if result['success']:
        return result['azimuth']
    else:
        response.status_code = 422
        return result['errors']


@app.get('/instrument_height/')
def instrument_height_get():
    """"Gets the instrument height above the occupied point."""
    result = engine.station.get_instrument_height()
    return result['instrument_height']


@app.post('/instrument_height/')
def instrument_height_set(response: Response, height: float):
    """"Gets the instrument height above the occupied point."""
    result = engine.station.set_instrument_height(height)
    if result['success']:
        return result['instrument_height']
    else:
        response.status_code = 422
        return result['errors']


@app.get('/cancel/')
def measurement_cancel():
    """Stops a measurement in progress."""
    result = engine.total_station.cancel_measurement()
    return result['result']


@app.get('/measurement/')
def measurement_take(response: Response):
    """Tells the total station to start measuring a point."""
    result = engine.total_station.take_measurement()
    if result['success']:
        return engine.data.apply_offsets_to_measurement(result)['measurement']
    else:
        response.status_code = 422
        return result['errors']


@app.post('/mode_hr/')
def mode_hr_set(response: Response):
    """Sets the total station to horizontal right mode."""
    result = engine.total_station.set_mode_hr()
    if result['success']:
        return result['result']
    else:
        response.status_code = 422
        return result['errors']


@app.get('/occupied_point/')
def occupied_point_get():
    """Gets the coordinates of the occupied point."""
    result = engine.station.get_occupied_point()
    return result['coordinates']


@app.post('/occupied_point/')
def occupied_point_set(response: Response, northing: float, easting: float, elevation: float):
    """Sets the coordinates of the occupied point."""
    result = engine.station.set_occupied_point(northing, easting, elevation)
    if result['success']:
        return result['coordinates']
    else:
        response.status_code = 422
        return result['errors']


@app.get('/prism_offset/')
def prism_offset_get():
    """Gets the prism offsets."""
    result = engine.prism.get_prism_offset()
    return result['prism_offset']


@app.post('/prism_offset/')
def prism_offset_set(response: Response, offsets: dict):
    """Sets the prism offsets."""
    result = engine.prism.set_prism_offset(**offsets)
    if result['success']:
        return result['prism_offset']
    else:
        response.status_code = 422
        return result['errors']
