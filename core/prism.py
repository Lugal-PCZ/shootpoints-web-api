"""
This module handles the vertical and horizontal prism offsets.

Offset direction is always FROM the point TO the prism, as viewed
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
"""

from . import database as _database


def get_prism_offsets(human_reabable: bool=False) -> dict:
    """This function returns the prism offsets, in raw or human-readable form."""
    offsets = _database.read_from_database('SELECT * FROM prism LIMIT 1')['results'][0]
    if human_reabable:
        readable_offsets = {}
        for key, val in offsets.items():
            if offsets[key]:
                if key == 'vertical_distance':
                    if val > 0:
                        readable_offsets['vertical_direction'] = 'Up'
                    else:
                        readable_offsets['vertical_direction'] = 'Down'
                        val = abs(val)
                elif key == 'latitude_distance':
                    if val > 0:
                        readable_offsets['latitude_direction'] = 'North'
                    else:
                        readable_offsets['latitude_direction'] = 'South'
                        val = abs(val)
                elif key == 'longitude_distance':
                    if val > 0:
                        readable_offsets['longitude_direction'] = 'East'
                    else:
                        readable_offsets['longitude_direction'] = 'West'
                        val = abs(val)
                elif key == 'radial_distance':
                    if val > 0:
                        readable_offsets['radial_direction'] = 'Away'
                    else:
                        readable_offsets['radial_direction'] = 'Toward'
                        val = abs(val)
                elif key == 'tangent_distance':
                    if val > 0:
                        readable_offsets['tangent_direction'] = 'Right'
                    else:
                        readable_offsets['tangent_direction'] = 'Left'
                        val = abs(val)
                readable_offsets[key] = val
            outcome = readable_offsets
    else:
        outcome = offsets
    return outcome


def set_prism_offsets(**kwargs) -> dict:
    """This function sets the prism offsets and saves them to the database."""
    outcome = {'errors': [], 'results': []}
    offsets = get_prism_offsets()
    for key, val in kwargs.items():
        if key == 'vertical_distance':
            try:
                val = float(val)
                try:
                    if kwargs['vertical_direction'].upper() == 'UP':
                        offsets['vertical_distance'] = abs(val)
                    elif kwargs['vertical_direction'].upper() == 'DOWN':
                        offsets['vertical_distance'] = -abs(val)
                    else:
                        outcome['errors'].append(f'The Vertical Offset direction entered ({kwargs["vertical_direction"]}) was invalid. It must be Up or Down.')
                except KeyError:
                    outcome['errors'].append('No direction was given for the Vertical Offset.')
            except ValueError:
                outcome['errors'].append(f'The Vertical Offset distance entered ({val}) is not numerical.')
        elif key == 'latitude_distance':
            try:
                val = float(val)
                try:
                    if kwargs['latitude_direction'].upper() == 'NORTH':
                        offsets['latitude_distance'] = abs(val)
                    elif kwargs['latitude_direction'].upper() == 'SOUTH':
                        offsets['latitude_distance'] = -abs(val)
                    else:
                        outcome['errors'].append(f'The Latitude Offset direction entered ({kwargs["latitude_direction"]}) was invalid. It must be North or South.')
                except KeyError:
                    outcome['errors'].append('No direction was given for the Latitude Offset.')
            except ValueError:
                outcome['errors'].append(f'The Latitude Offset distance entered ({val}) is not numerical.')
        elif key == 'longitude_distance':
            try:
                val = float(val)
                try:
                    if kwargs['longitude_direction'].upper() == 'EAST':
                        offsets['longitude_distance'] = abs(val)
                    elif kwargs['longitude_direction'].upper() == 'WEST':
                        offsets['longitude_distance'] = -abs(val)
                    else:
                        outcome['errors'].append(f'The Longitude Offset direction entered ({kwargs["longitude_direction"]}) was invalid. It must be East or West.')
                except KeyError:
                    outcome['errors'].append('No direction was given for the Longitude Offset.')
            except ValueError:
                outcome['errors'].append(f'The Longitude Offset distance entered ({val}) is not numerical.')
        elif key == 'radial_distance':
            try:
                val = float(val)
                try:
                    if kwargs['radial_direction'].upper() == 'AWAY':
                        offsets['radial_distance'] = abs(val)
                    elif kwargs['radial_direction'].upper() == 'TOWARD':
                        offsets['radial_distance'] = -abs(val)
                    else:
                        outcome['errors'].append(f'The Radial Offset direction entered ({kwargs["radial_direction"]}) was invalid. It must be Away or Toward.')
                except KeyError:
                    outcome['errors'].append('No direction was given for the Radial Offset.')
            except ValueError:
                outcome['errors'].append(f'The Radial Offset distance entered ({val}) is not numerical.')
        elif key == 'tangent_distance':
            try:
                val = float(val)
                try:
                    if kwargs['tangent_direction'].upper() == 'RIGHT':
                        offsets['tangent_distance'] = abs(val)
                    elif kwargs['tangent_direction'].upper() == 'LEFT':
                        offsets['tangent_distance'] = -abs(val)
                    else:
                        outcome['errors'].append(f'The Tangent Offset direction entered ({kwargs["tangent_direction"]}) was invalid. It must be Right or Left.')
                except KeyError:
                    outcome['errors'].append('No direction was given for the Tangent Offset.')
            except ValueError:
                outcome['errors'].append(f'The Tangent Offset distance entered ({val}) is not numerical.')
    if not outcome['errors']:
        data = (
            offsets['vertical_distance'],
            offsets['latitude_distance'],
            offsets['longitude_distance'],
            offsets['radial_distance'],
            offsets['tangent_distance'],
        )
        sql = (
            'UPDATE prism '
            'SET '
                'vertical_distance = ?, '
                'latitude_distance = ?, '
                'longitude_distance = ?, '
                'radial_distance = ?, '
                'tangent_distance = ?'
        )
        _database.save_to_database(sql, data)
        outcome['results'].append(f'Prism offsets are now {str(offsets)}.')
    outcome['success'] = not outcome['errors']
    return {key: val for key, val in outcome.items() if type(val) != list or val}
