# Set the default prism offset values.
# Direction is FROM the point TO the prism.


_vertical_offset = {
    # > 0 = U
    # < 0 = D
    'vertical_distance': 0.0,
}

_absolute_offset = {
    # > 0 = N
    # < 0 = S
    'latitude_distance': 0.0,
    # > 0 = E
    # < 0 = W
    'longitude_distance': 0.0,
}

_relative_offset = {
    # > 0 = B
    # < 0 = F
    'radial_distance': 0.0,
    # > 0 = R
    # < 0 = L
    'tangent_distance': 0.0,
}


def get_prism_offset() -> dict:
    offsets = []
    global _vertical_offset
    global _absolute_offset
    global _relative_offset
    _ = {**_vertical_offset, **_absolute_offset, **_relative_offset}
    for key, val in _.items():
        if _[key]:
            if key == 'vertical_distance':
                if val > 0:
                    offsets.append({'vertical_direction': 'U'})
                else:
                    offsets.append({'vertical_direction': 'D'})
                    val = abs(val)
            elif key == 'latitude_distance':
                if val > 0:
                    offsets.append({'latitude_direction': 'N'})
                else:
                    offsets.append({'latitude_direction': 'S'})
                    val = abs(val)
            elif key == 'longitude_distance':
                if val > 0:
                    offsets.append({'longitude_direction': 'E'})
                else:
                    offsets.append({'longitude_direction': 'W'})
                    val = abs(val)
            elif key == 'radial_distance':
                if val > 0:
                    offsets.append({'radial_direction': 'B'})
                else:
                    offsets.append({'radial_direction': 'F'})
                    val = abs(val)
            elif key == 'tangent_distance':
                if val > 0:
                    offsets.append({'tangent_direction': 'R'})
                else:
                    offsets.append({'tangent_direction': 'L'})
                    val = abs(val)
            offsets.append({key: val})
    return {
        'success': True,
        'prism_offset': offsets
    }

def set_prism_offset(**kwargs) -> dict:
    # TODO: save the offsets to the DB for stability
    errors = []
    global _vertical_offset
    global _absolute_offset
    global _relative_offset
    temp_vertical_offset = {'vertical_distance': 0.0}
    temp_absolute_offset = {'latitude_distance': 0.0, 'longitude_distance': 0.0}
    temp_relative_offset = {'radial_distance': 0.0, 'tangent_distance': 0.0}
    for key, val in kwargs.items():
        if key == 'verdist':
            try:
                val = float(val)
                try:
                    if kwargs['verdir'].upper() == 'U':
                        temp_vertical_offset['vertical_distance'] = abs(val)
                    elif kwargs['verdir'].upper() == 'D':
                        temp_vertical_offset['vertical_distance'] = -abs(val)
                    else:
                        errors.append(f'The Vertical Offset direction entered ({kwargs["verdir"]}) was invalid. It must be U or D.')
                except KeyError:
                    errors.append('No direction was given for the Vertical Offset.')
            except ValueError:
                errors.append(f'The Vertical Offset distance entered ({val}) is not numerical.')
        elif key == 'latdist':
            try:
                val = float(key)
                try:
                    if kwargs['latdir'].upper() == 'N':
                        temp_absolute_offset['latitude_distance'] = abs(val)
                    elif kwargs['latdir'].upper() == 'S':
                        temp_absolute_offset['latitude_distance'] = -abs(val)
                    else:
                        errors.append(f'The Latitude Offset direction entered ({kwargs["latdir"]}) was invalid. It must be N or S.')
                except KeyError:
                    errors.append('No direction was given for the Latitude Offset.')
            except ValueError:
                errors.append(f'The Latitude Offset distance entered ({val}) is not numerical.')
        elif key == 'londist':
            try:
                val = float(key)
                try:
                    if kwargs['londir'].upper() == 'E':
                        temp_absolute_offset['longitude_distance'] = abs(val)
                    elif kwargs['londir'].upper() == 'W':
                        temp_absolute_offset['longitude_distance'] = -abs(val)
                    else:
                        errors.append(f'The Longitude Offset direction entered ({kwargs["londir"]}) was invalid. It must be E or W.')
                except KeyError:
                    errors.append('No direction was given for the Longitude Offset.')
            except ValueError:
                errors.append(f'The Longitude Offset distance entered ({val}) is not numerical.')
        elif key == 'raddist':
            try:
                val = float(key)
                try:
                    if kwargs['raddir'].upper() == 'B':
                        temp_relative_offset['radial_distance'] = abs(val)
                    elif kwargs['raddir'].upper() == 'F':
                        temp_relative_offset['radial_distance'] = -abs(val)
                    else:
                        errors.append(f'The Radial Offset direction entered ({kwargs["raddir"]}) was invalid. It must be B or F.')
                except KeyError:
                    errors.append('No direction was given for the Radial Offset.')
            except ValueError:
                errors.append(f'The Radial Offset distance entered ({val}) is not numerical.')
        elif key == 'tandist':
            try:
                val = float(key)
                try:
                    if kwargs['tandir'].upper() == 'R':
                        temp_relative_offset['tangent_distance'] = abs(val)
                    elif kwargs['tandir'].upper() == 'L':
                        temp_relative_offset['tangent_distance'] = -abs(val)
                    else:
                        errors.append(f'The Tangent Offset direction entered ({kwargs["tandir"]}) was invalid. It must be R or L.')
                except KeyError:
                    errors.append('No direction was given for the Tangent Offset.')
            except ValueError:
                errors.append(f'The Tangent Offset distance entered ({val}) is not numerical.')

    if errors:
        result = {'success': False, 'errors': errors}
    else:
        _vertical_offset = temp_vertical_offset
        _absolute_offset = temp_absolute_offset
        _relative_offset = temp_relative_offset
        result = get_prism_offset()
    return result
