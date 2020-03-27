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

def _read(timeout: float=0.2) -> bytes:
    """Reads all characters waiting in the serial port's buffer."""
    port.timeout = timeout
    buffer = port.read_until(bytes(ETX, 'ascii'))
    return buffer


def _write(command: str) -> None:
    """Blindly writes the command to the serial port."""
    command = bytes(command + ETX, 'ascii')
    port.write(command)
    _clear_buffers()


def _clear_buffers() -> None:
    """Clears the serial port buffers."""
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
    ack_received = False
    for _ in range(count):
        if _read() == bytes(ACK + ETX, 'ascii'):
            ack_received = True
            break
    return ack_received


def set_mode_hr() -> bool:
    """Sets the total station to V/H mode with Horizontal Right."""
    success = False
    _write('Z12089')
    if _wait_for_ack():
        success = True
    return {'success': success}


def set_azimuth(degrees: int=0, minutes: int=0, seconds: int=0) -> bool:
    """Sets the azimuth reading on the total station."""
    success = False
    angle = (degrees * 10000) + (minutes * 100) + seconds
    command = 'J+{}d'.format(angle)
    bcc = _calculate_bcc(command)
    _write('J074')
    if _wait_for_ack():
        _write(command + bcc)
        if _wait_for_ack():
            success = True
    return {'success': success}



def take_measurement() -> str:
    """Tells the total station to begin measuring a point"""
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
            delta_e = float(measurement[12:23])/10000
            delta_n = float(measurement[1:12])/10000
            delta_z = float(measurement[23:34])/10000
            result = {
                'success': True,
                'measurement': {'delta_n': delta_n, 'delta_e': delta_e, 'delta_z': delta_z}
            }
        else:
            result = {
                'success': False,
                'error': f'Unexpected data format: {measurement}.'
            }
    except:
        result = {
            'success': False,
            'error': 'Measurement failed.'
        }
    return result
