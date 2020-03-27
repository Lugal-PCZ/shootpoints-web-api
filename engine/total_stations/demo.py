# Faked data responses for an imaginary total station, when ShootPoints is run as a demo.

from time import sleep
from random import randint


def set_mode_hr() -> dict:
    """Sets the total station to V/H mode with Horizontal Right."""
    sleep(1)
    return {'success': True}


def set_azimuth(degrees: int=0, minutes: int=0, seconds: int=0) -> bool:
    """Sets the azimuth reading on the total station."""
    sleep(1)
    return {'success': True}


def take_measurement() -> str:
    """Tells the total station to begin measuring a point"""
    sleep(3)
    delta_n = (496337 + randint(-50000, 50000))/10000
    delta_e = (311930 + randint(-50000, 50000))/10000
    delta_z = (95802 + randint(-10000, 10000))/10000
    return {
        'success': True,
        'measurement': {'delta_n': delta_n, 'delta_e': delta_e, 'delta_z': delta_z}
    }
