# Communications constants and methods for interfacing with Topcon GTS-300 Series total stations.

# Communications constants:
BAUDRATE=1200
PARITY='E'
BYTESIZE=7
STOPBITS=1
TIMEOUT=0
ETX = chr(3)
ACK = chr(6) + '006'

port = None  # This property is set by engine/__init__.py once the serial port has been initialized.

_canceled = False


def _read(timeout: float=0.2) -> bytes:
    """Reads all characters waiting in the serial port's buffer."""
    global port
    port.timeout = timeout
    buffer = port.read_until(bytes(ETX, 'ascii'))
    return buffer


def _write(command: str) -> None:
    """Blindly writes the command to the serial port."""
    global port
    command = bytes(command + ETX, 'ascii')
    port.write(command)
    _clear_buffers()


def _clear_buffers() -> None:
    """Clears the serial port buffers."""
    global port
    port.reset_input_buffer()
    port.reset_output_buffer()


def _calculate_bcc(data: str) -> str:
    """Calculates BCC values for commands that require it."""
    bcc = 0
    for each_character in data:
        q = ord(each_character)
        bcc ^= q
    return '{:03d}'.format(bcc)


def _wait_for_ack(count: int=10) -> bool:
    """Waits for the ACK returned from the total station."""
    global _canceled
    ack_received = False
    for _ in range(count):
        if _canceled:
            break
        elif _read() == bytes(ACK + ETX, 'ascii'):
            ack_received = True
            break
    return ack_received


def set_mode_hr() -> dict:
    """Sets the total station to V/H mode with Horizontal Right."""
    _write('Z12089')
    if _wait_for_ack():
        result = {
            'success': True,
            'result': 'Mode set to Horizontal Right.'
        }
    else:
        result = {
            'success': False,
            'errors': ['Failed to set mode to Horizontal Right.']
        }
    return result


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
        angle = (degrees * 10000) + (minutes * 100) + seconds
        command = f'J+{angle}d'
        bcc = _calculate_bcc(command)
        _write('J074')
        if _wait_for_ack():
            _write(command + bcc)
            if _wait_for_ack():
                result = {
                    'success': True,
                    'azimuth': f'{degrees}° {minutes}\' {seconds}"'
                }
            else:
                result = {
                    'success': False,
                    'errors': [f'Failed to set azimuth to {angle}.']
                }
    return result


def take_measurement() -> dict:
    """Tells the total station to begin measuring a point."""
    global _canceled
    data = b''
    _write('Z64088')
    if _wait_for_ack():
        _write('C067')
        if _wait_for_ack():
            data = _read(10)
            _write(ACK)
    measurement = data.decode('utf-8')
    try:
        data_format = measurement[0]
        data_unit = measurement[34]
        if data_format == '/' and data_unit == 'm':
            delta_e = round(float(measurement[12:23])/10000, 3)
            delta_n = round(float(measurement[1:12])/10000, 3)
            delta_z = round(float(measurement[23:34])/10000, 3)
            result = {
                'success': True,
                'measurement': {'delta_n': delta_n, 'delta_e': delta_e, 'delta_z': delta_z}
            }
        else:
            result = {
                'success': False,
                'errors': [f'Unexpected data format: {measurement}.']
            }
    except:
        if _canceled:
            result = None
        else:
            result = {
                'success': False,
                'errors': ['Measurement failed.']
            }
    return result


def cancel_measurement() -> dict:
    """Cancels a measurement in progress."""
    global _canceled
    _canceled = True  # Flag to short circuit _wait_for_ack() and take_measurement().
    set_mode_hr()  # Issue harmless command that interrupts the GTS.
    _canceled = False  # Reset flag.
    return {
        'success': True,
        'result': 'Measurement canceled by user.'
    }

