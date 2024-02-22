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

from typing import Optional

from . import database
from .utilities import format_outcome


offsets = {
    "vertical_distance": 0.0,
    "latitude_distance": 0.0,
    "longitude_distance": 0.0,
    "radial_distance": 0.0,
    "tangent_distance": 0.0,
    "wedge_distance": 0.0,
}

_directions = {
    "vertical": ["Up", "Down"],
    "latitude": ["North", "South"],
    "longitude": ["East", "West"],
    "radial": ["Away", "Toward"],
    "tangent": ["Right", "Left"],
    "wedge": ["Clockwise", "Counter-Clockwise"],
}


def get_offset_types_and_directions() -> list:
    """This function returns the types of prism offsets and their applicable directions."""
    offsets = []
    for key, val in _directions.items():
        offsets.append({"name": key.title(), "directions": val})
    return offsets


def get_readable_prism_offsets() -> dict:
    """This function returns the prism offsets in human-readable form."""
    readable_offsets = {"offsets": []}
    for key, val in offsets.items():
        if key == "vertical_distance":
            if val > 0:
                readable_offsets["offsets"].append(
                    f"{val}m {_directions['vertical'][0]}"
                )
            elif val < 0:
                val = abs(val)
                readable_offsets["offsets"].append(
                    f"{val}m {_directions['vertical'][1]}"
                )
        elif key == "latitude_distance":
            if val > 0:
                readable_offsets["offsets"].append(
                    f"{val}m {_directions['latitude'][0]}"
                )
            elif val < 0:
                val = abs(val)
                readable_offsets["offsets"].append(
                    f"{val}m {_directions['latitude'][1]}"
                )
        elif key == "longitude_distance":
            if val > 0:
                readable_offsets["offsets"].append(
                    f"{val}m {_directions['longitude'][0]}"
                )
            elif val < 0:
                val = abs(val)
                readable_offsets["offsets"].append(
                    f"{val}m {_directions['longitude'][1]}"
                )
        elif key == "radial_distance":
            if val > 0:
                readable_offsets["offsets"].append(f"{val}m {_directions['radial'][0]}")
            elif val < 0:
                val = abs(val)
                readable_offsets["offsets"].append(f"{val}m {_directions['radial'][1]}")
        elif key == "tangent_distance":
            if val > 0:
                readable_offsets["offsets"].append(
                    f"{val}m {_directions['tangent'][0]}"
                )
            elif val < 0:
                val = abs(val)
                readable_offsets["offsets"].append(
                    f"{val}m {_directions['tangent'][1]}"
                )
        elif key == "wedge_distance":
            if val > 0:
                readable_offsets["offsets"].append(f"{val}m {_directions['wedge'][0]}")
            elif val < 0:
                val = abs(val)
                readable_offsets["offsets"].append(f"{val}m {_directions['wedge'][1]}")
    return readable_offsets


def get_raw_prism_offsets() -> dict:
    return offsets


def set_prism_offsets(
    vertical_distance: Optional[float] = None,
    latitude_distance: Optional[float] = None,
    longitude_distance: Optional[float] = None,
    radial_distance: Optional[float] = None,
    tangent_distance: Optional[float] = None,
    wedge_distance: Optional[float] = None,
) -> dict:
    """This function sets the prism offsets and saves them to the database."""
    global offsets
    saved_args = locals()
    outcome = {"errors": [], "result": ""}
    newoffsets = {}
    for key, val in saved_args.items():
        if val != None:
            if key not in offsets.keys():
                outcome["errors"].append(f"“{key}” is not a valid offset.")
            else:
                newoffsets[f"{key} = ?"] = val
    if not outcome["errors"]:
        sql = f"UPDATE savedstate SET {', '.join(newoffsets.keys())}"
        data = tuple(newoffsets.values())
        saved = database._save_to_database(sql, data)
        if "errors" not in saved:
            for key, val in saved_args.items():
                if val != None:
                    offsets[key] = val
            readable_offsets = get_readable_prism_offsets()["offsets"]
            if len(readable_offsets):
                outcome["result"] = (
                    f'Prism offsets are now {", ".join(readable_offsets)}.'
                )
            else:
                outcome["result"] = "Prism offsets are 0 in all directions."
        else:
            outcome["errors"] = saved["errors"]
    return format_outcome(outcome)
