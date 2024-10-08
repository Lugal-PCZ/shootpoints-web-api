"""This module contains constants and methods for communicating with Topcon GTS-300 Series total stations."""

from ... import calculations
from ...survey import pressure, temperature
from ...utilities import format_outcome

# Communications constants:
BAUDRATE = 1200
PARITY = "E"
BYTESIZE = 7
STOPBITS = 1
TIMEOUT = 0
ETX = chr(3)
ACK = chr(6) + "006"

# This property is set by core/__init__.py once the serial port has been initialized.
# To suppress Pylance warnings, “# type: ignore” is used below everywhere that it’s referenced.
port = None

_canceled = False


def _read(timeout: float) -> bytes:
    """This function reads all characters waiting in the serial port's buffer."""
    port.timeout = timeout  # type: ignore
    buffer = port.read_until(bytes(ETX, "ascii"))  # type: ignore
    return buffer


def _write(command: str) -> None:
    """This function blindly writes the command to the serial port."""
    port.write(bytes(command + ETX, "ascii"))  # type: ignore
    _clear_buffers()


def _clear_buffers() -> None:
    """This function clears the serial port buffers."""
    port.reset_input_buffer()  # type: ignore
    port.reset_output_buffer()  # type: ignore


def _calculate_bcc(data: str) -> str:
    """This function calculates BCC values for commands that require it."""
    bcc = 0
    for each_character in data:
        bcc ^= ord(each_character)
    return "{:03d}".format(bcc)


def _wait_for_ack(count: int = 10) -> bool:
    """This function listens for the ACK returned from the total station."""
    ack_received = False
    for _ in range(count):
        if _canceled:
            break
        elif _read(0.5) == bytes(ACK + ETX, "ascii"):
            ack_received = True
            break
    return ack_received


def set_mode_hr() -> dict:
    """This function sets the total station to V/H mode with Horizontal Right."""
    outcome = {"errors": [], "result": ""}
    _write("Z12089")
    if not _wait_for_ack():
        outcome["errors"].append("A communication error occurred.")
    else:
        outcome["result"] = "Mode set to Horizontal Right."
    return format_outcome(outcome)


def set_azimuth(degrees: int = 0, minutes: int = 0, seconds: int = 0) -> dict:
    """This function sets the azimuth reading on the total station."""
    outcome = {"errors": [], "result": ""}
    global _canceled
    _canceled = False
    try:
        degrees = int(degrees)
        if not 0 <= degrees <= 359:
            outcome["errors"].append(
                f"Degrees entered ({degrees}) is out of range (0 to 359)."
            )
    except ValueError:
        outcome["errors"].append(
            f"A non-integer value ({degrees}) was entered for degrees."
        )
    try:
        minutes = int(minutes)
        if not 0 <= minutes <= 59:
            outcome["errors"].append(
                f"Minutes entered ({minutes}) is out of range (0 to 59)."
            )
    except ValueError:
        outcome["errors"].append(
            f"A non-integer value ({minutes}) was entered for minutes."
        )
    try:
        seconds = int(seconds)
        if not 0 <= seconds <= 59:
            outcome["errors"].append(
                f"Seconds entered ({seconds}) is out of range (0 to 59)."
            )
    except ValueError:
        outcome["errors"].append(
            f"A non-integer value ({seconds}) was entered for seconds."
        )
    if not outcome["errors"]:
        setmodehr = set_mode_hr()
        if "errors" not in setmodehr:
            azimuth = (degrees * 10000) + (minutes * 100) + seconds
            command = f"J+{azimuth}d"
            bcc = _calculate_bcc(command)
            _write("J074")
            if _wait_for_ack():
                _write(command + bcc)
                if not _wait_for_ack():
                    outcome["errors"].append("A communication error occurred.")
                else:
                    outcome["result"] = (
                        f"Azimuth set to {degrees}° {minutes}' {seconds}\"."
                    )
            else:
                outcome["errors"].append("A communication error occurred.")
        else:
            outcome["errors"].extend(setmodehr["errors"])
    return format_outcome(outcome)


def take_measurement() -> dict:
    """This function tells the total station to begin measuring a point."""
    outcome = {"errors": [], "measurement": {}, "notification": ""}
    global _canceled
    _canceled = False
    measurement = b""
    _write("Z64088")
    if _wait_for_ack():
        _write("C067")
        if _wait_for_ack():
            measurement = _read(30).decode("utf-8")
            _write(ACK)
        else:
            outcome["errors"].append("A communication error occurred.")
    else:
        outcome["errors"].append("A communication error occurred.")
    if not outcome["errors"]:
        try:
            data_format = measurement[0]
            data_unit = measurement[34]
            if data_format == "/" and data_unit == "m":
                delta_e = round(float(measurement[12:23]) / 10000, 3)
                delta_n = round(float(measurement[1:12]) / 10000, 3)
                delta_z = round(float(measurement[23:34]) / 10000, 3)
                outcome["measurement"] = calculations._apply_atmospheric_correction(
                    {
                        "delta_n": delta_n,
                        "delta_e": delta_e,
                        "delta_z": delta_z,
                    },
                    pressure,
                    temperature,
                )
            else:
                outcome["errors"].append(f"Unexpected data format: {measurement}.")
        except:
            if _canceled:
                _canceled = False
                return {"notification": "Shot canceled by user."}
            else:
                set_mode_hr()
                outcome["errors"].append("Measurement failed.")
    return format_outcome(outcome)


def cancel_measurement() -> None:
    """This function cancels a measurement in progress."""
    global _canceled
    _canceled = True  # Flag to short circuit _wait_for_ack() and take_measurement().
    set_mode_hr()  # Issue harmless command that interrupts the GTS.
    return
