# Set the default prism offset values.
# Direction is FROM the point TO the prism, as viewed from the occupied station.


_offsets = {
    # Vertical Offset:
    # > 0 = Up
    # < 0 = Down
    'vertical_distance': 0.0,
    #
    # Absolute Offsets:
    # > 0 = North
    # < 0 = South
    'latitude_distance': 0.0,
    # > 0 = East
    # < 0 = West
    'longitude_distance': 0.0,
    #
    # Relative Offsets:
    # > 0 = Away
    # < 0 = Toward
    'radial_distance': 0.0,
    # > 0 = Right
    # < 0 = Left
    'tangent_distance': 0.0,
}


def get_prism_offset(full_output: bool=False) -> dict:
    global _offsets
    results = {'success': True}
    if not full_output:  # Format the output to be more easily human-readable
        readable_offsets = {}
        for key, val in _offsets.items():
            _offsets[key]:
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
        results['prism_offset'] = readable_offsets
    else:
        results['prism_offset'] = _offsets
    return results


def set_prism_offset(**kwargs: dict) -> dict:
    # TODO: save the offsets to the DB for stability
    errors = []
    global _offsets
    # Save the current offsets
    temp_offsets = {
        'vertical_distance': _offsets['vertical_distance'],
        'latitude_distance': _offsets['latitude_distance'],
        'longitude_distance': _offsets['longitude_distance'],
        'radial_distance': _offsets['radial_distance'],
        'tangent_distance': _offsets['tangent_distance'],
    }
    for key, val in kwargs.items():
        if key == 'vertical_distance':
            try:
                val = float(val)
                try:
                    if kwargs['vertical_direction'].upper() == 'UP':
                        temp_offsets['vertical_distance'] = abs(val)
                    elif kwargs['vertical_direction'].upper() == 'DOWN':
                        temp_offsets['vertical_distance'] = -abs(val)
                    else:
                        errors.append(f'The Vertical Offset direction entered ({kwargs["vertical_direction"]}) was invalid. It must be Up or Down.')
                except KeyError:
                    errors.append('No direction was given for the Vertical Offset.')
            except ValueError:
                errors.append(f'The Vertical Offset distance entered ({val}) is not numerical.')
        elif key == 'latitude_distance':
            try:
                val = float(val)
                try:
                    if kwargs['latitude_direction'].upper() == 'NORTH':
                        temp_offsets['latitude_distance'] = abs(val)
                    elif kwargs['latitude_direction'].upper() == 'SOUTH':
                        temp_offsets['latitude_distance'] = -abs(val)
                    else:
                        errors.append(f'The Latitude Offset direction entered ({kwargs["latitude_direction"]}) was invalid. It must be North or South.')
                except KeyError:
                    errors.append('No direction was given for the Latitude Offset.')
            except ValueError:
                errors.append(f'The Latitude Offset distance entered ({val}) is not numerical.')
        elif key == 'longitude_distance':
            try:
                val = float(val)
                try:
                    if kwargs['longitude_direction'].upper() == 'EAST':
                        temp_offsets['longitude_distance'] = abs(val)
                    elif kwargs['longitude_direction'].upper() == 'WEST':
                        temp_offsets['longitude_distance'] = -abs(val)
                    else:
                        errors.append(f'The Longitude Offset direction entered ({kwargs["longitude_direction"]}) was invalid. It must be East or West.')
                except KeyError:
                    errors.append('No direction was given for the Longitude Offset.')
            except ValueError:
                errors.append(f'The Longitude Offset distance entered ({val}) is not numerical.')
        elif key == 'radial_distance':
            try:
                val = float(val)
                try:
                    if kwargs['radial_direction'].upper() == 'AWAY':
                        temp_offsets['radial_distance'] = abs(val)
                    elif kwargs['radial_direction'].upper() == 'TOWARD':
                        temp_offsets['radial_distance'] = -abs(val)
                    else:
                        errors.append(f'The Radial Offset direction entered ({kwargs["radial_direction"]}) was invalid. It must be Away or Toward.')
                except KeyError:
                    errors.append('No direction was given for the Radial Offset.')
            except ValueError:
                errors.append(f'The Radial Offset distance entered ({val}) is not numerical.')
        elif key == 'tangent_distance':
            try:
                val = float(val)
                try:
                    if kwargs['tangent_direction'].upper() == 'RIGHT':
                        temp_offsets['tangent_distance'] = abs(val)
                    elif kwargs['tangent_direction'].upper() == 'LEFT':
                        temp_offsets['tangent_distance'] = -abs(val)
                    else:
                        errors.append(f'The Tangent Offset direction entered ({kwargs["tangent_direction"]}) was invalid. It must be Right or Left.')
                except KeyError:
                    errors.append('No direction was given for the Tangent Offset.')
            except ValueError:
                errors.append(f'The Tangent Offset distance entered ({val}) is not numerical.')

    if errors:
        result = {'success': False, 'errors': errors}
    else:
        _offsets = temp_offsets
        result = get_prism_offset()
    return result
