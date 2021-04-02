"""
This module handles the vertical and horizontal prism offsets.

Offset direction is always FROM the prism TO the point, as viewed
from the occupied station.

  Vertical Offset:
    vertical_distance > 0 = Up
    vertical_distance < 0 = Down

  Absolute Offsets:
    latitude_distance > 0 = North
    latitude_distance < 0 = South
    longitude_distance > 0 = East
    longitude_distance < 0 = West

  Relative Offsets:
    radial_distance > 0 = Away
    radial_distance < 0 = Toward
    tangent_distance > 0 = Right
    tangent_distance < 0 = Left
    wedge_distance > 0 = Clockwise
    wedge_distance < 0 = Counter-Clockwise
"""

from . import _database


offsets = {
    'vertical_distance': 0.0,
    'latitude_distance': 0.0,
    'longitude_distance': 0.0,
    'radial_distance': 0.0,
    'tangent_distance': 0.0,
    'wedge_distance': 0.0,
}

_directions = {
    'vertical': ['Up', 'Down'],
    'latitude': ['North', 'South'],
    'longitude': ['East', 'West'],
    'radial': ['Away', 'Toward'],
    'tangent': ['Right', 'Left'],
    'wedge': ['Clockwise', 'Counter-Clockwise'],
}


def get_readable_offsets() -> dict:
    """This function returns the prism offsets in human-readable form."""
    readable_offsets = {'offsets': []}
    for key, val in offsets.items():
        if key == 'vertical_distance':
            if val > 0:
                readable_offsets['offsets'].append(f"{val}m {_directions['vertical'][0]}")
            elif val < 0:
                val = abs(val)
                readable_offsets['offsets'].append(f"{val}m {_directions['vertical'][1]}")
        elif key == 'latitude_distance':
            if val > 0:
                readable_offsets['offsets'].append(f"{val}m {_directions['latitude'][0]}")
            elif val < 0:
                val = abs(val)
                readable_offsets['offsets'].append(f"{val}m {_directions['latitude'][1]}")
        elif key == 'longitude_distance':
            if val > 0:
                readable_offsets['offsets'].append(f"{val}m {_directions['longitude'][0]}")
            elif val < 0:
                val = abs(val)
                readable_offsets['offsets'].append(f"{val}m {_directions['longitude'][1]}")
        elif key == 'radial_distance':
            if val > 0:
                readable_offsets['offsets'].append(f"{val}m {_directions['radial'][0]}")
            elif val < 0:
                val = abs(val)
                readable_offsets['offsets'].append(f"{val}m {_directions['radial'][1]}")
        elif key == 'tangent_distance':
            if val > 0:
                readable_offsets['offsets'].append(f"{val}m {_directions['tangent'][0]}")
            elif val < 0:
                val = abs(val)
                readable_offsets['offsets'].append(f"{val}m {_directions['tangent'][1]}")
        elif key == 'wedge_distance':
            if val > 0:
                readable_offsets['offsets'].append(f"{val}m {_directions['wedge'][0]}")
            elif val < 0:
                val = abs(val)
                readable_offsets['offsets'].append(f"{val}m {_directions['wedge'][1]}")
    return readable_offsets


def _validate_prism_offset(offsettype: str, distance: str, direction: str, errors: list) -> None:
    """This function verifies the sanity of the given prism offset."""
    global offsets
    try:
        distance = float(distance)
        try:
            if distance == 0:
                pass
            elif direction.upper() == _directions[offsettype][0].upper():
                distance = abs(distance)
            elif direction.upper() == _directions[offsettype][1].upper():
                distance = -abs(distance)
            else:
                errors.append(f'The {offsettype.title()} Offset direction entered ({direction}) was invalid. It must be {_directions[offsettype][0]} or {_directions[offsettype][1]}.')
            offsets[f'{offsettype}_distance'] = distance
        except KeyError:
            errors.append(f'No direction was given for the {offsettype.title()} Offset.')
    except ValueError:
        errors.append(f'The {offsettype.title()} Offset distance entered ({distance}) is not numerical.')


def set_prism_offsets(**kwargs) -> dict:
    """This function sets the prism offsets and saves them to the database."""
    outcome = {'errors': [], 'result': ''}
    for key, val in kwargs.items():
        key = key.split('_')
        offsettype = key[0]
        if key[1] == 'distance' and offsettype in _directions:
            distance = kwargs[f'{key[0]}_distance']
            try:
                direction = kwargs[f'{key[0]}_direction']
            except KeyError:
                direction = ''
            _validate_prism_offset(offsettype, distance, direction, outcome['errors'])
    if not outcome['errors']:
        data = (
            offsets['vertical_distance'],
            offsets['latitude_distance'],
            offsets['longitude_distance'],
            offsets['radial_distance'],
            offsets['tangent_distance'],
            offsets['wedge_distance'],
        )
        sql = (
            'UPDATE prism '
            'SET '
                'vertical_distance = ?, '
                'latitude_distance = ?, '
                'longitude_distance = ?, '
                'radial_distance = ?, '
                'tangent_distance = ?, '
                'wedge_distance = ?'
        )
        _database.save_to_database(sql, data)
        readable_offsets = get_readable_offsets()['offsets']
        if len(readable_offsets):
            outcome['result'] = f'Prism offsets are now {", ".join(readable_offsets)}.'
        else:
            outcome['result'] = 'Prism offsets are 0 in all directions.'
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if val or key == 'success'}
