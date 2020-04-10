# Faked data responses for an imaginary total station, when ShootPoints is run as a demo.

from time import sleep
from random import randint

canceled = False


def set_mode_hr() -> dict:
    """Sets the total station to V/H mode with Horizontal Right."""
    sleep(1)
    return {'success': True, 'result': 'Mode set to Horizontal Right.'}


def set_azimuth(degrees: int=0, minutes: int=0, seconds: int=0) -> dict:
    """Sets the azimuth reading on the total station."""
    errors = []
    try:
        degrees = int(degrees)
    except ValueError:
        errors.append(f'A non-integer value ({degrees}) was entered for degrees.')
    try:
        minutes = int(minutes)
    except ValueError:
        errors.append(f'A non-integer value ({minutes}) was entered for minutes.')
    try:
        seconds = int(seconds)
    except ValueError:
        errors.append(f'A non-integer value ({seconds}) was entered for seconds.')
    if not 0 <= degrees <= 359:
        errors.append(f'Degrees entered ({degrees}) is out of range (0 to 359).')
    elif not 0 <= minutes <= 59:
        errors.append(f'Minutes entered ({minutes}) is out of range (0 to 59).')
    elif not 0 <= seconds <= 59:
        errors.append(f'Seconds entered ({seconds}) is out of range (0 to 59).')
    if errors:
        result = {'success': False, 'errors': errors}
    else:
        sleep(1)
        result = {'success': True, 'azimuth': f'{degrees}° {minutes}\' {seconds}"'}
    return result


def take_measurement() -> dict:
    """Tells the total station to begin measuring a point."""
    global canceled
    delay = 5
    for _ in range(delay - 1):
        sleep(_)
        if canceled:
            canceled = False
            return
    delta_n = (496337 + randint(-50000, 50000))/10000
    delta_e = (311930 + randint(-50000, 50000))/10000
    delta_z = (95802 + randint(-10000, 10000))/10000
    return {
        'success': True,
        'measurement': {'delta_n': delta_n, 'delta_e': delta_e, 'delta_z': delta_z}
    }


def cancel_measurement() -> dict:
    """Cancels a measurement in progress."""
    global canceled
    canceled = True
    return {
        'success': True,
        'result': 'Measurement canceled.'
    }
