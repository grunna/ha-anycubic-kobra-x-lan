"""Helpers that read the printer's LAN reports out of coordinator data.

Report shapes follow AnycubicSlicerNext and the anycubic-cloud-api LAN client
used by Nino6689/hass-anycubic.
"""

from __future__ import annotations

from typing import Any

from .const import REASON_TEXT, USER_REASON_CODES

# Print report `state` values that mean a job is running.
PRINT_STATES_ACTIVE = frozenset(
    {
        "printing",
        "preheating",
        "downloading",
        "checking",
        "pausing",
        "paused",
        "resuming",
        "resumed",
        "updated",
        "auto_leveling",
    }
)
PRINT_STATES_PAUSED = frozenset({"pausing", "paused"})
PRINT_STATES_DONE = frozenset({"finished", "complete", "completed"})
PRINT_STATES_STOPPED = frozenset({"stoped", "stopped", "stopping", "canceled", "cancelled"})
PRINT_STATES_FAILED = frozenset({"failed"})

# `print_status` codes in the info report's project.
PRINT_STATUS_ACTIVE = frozenset({1, 4, 5, 6, 7, 9, 10, 11})
PRINT_STATUS_FINISHED = 2

# Used when the printer does not publish its own speed mode list.
DEFAULT_SPEED_MODES = {1: "Quiet", 2: "Standard", 3: "Sport"}


def payload(data: dict[str, Any], query_type: str) -> dict[str, Any]:
    report = data.get(query_type)

    if not isinstance(report, dict):
        return {}

    report_data = report.get("data")

    if isinstance(report_data, dict):
        return report_data

    return report


def project(data: dict[str, Any]) -> dict[str, Any]:
    info_project = payload(data, "info").get("project")

    if isinstance(info_project, dict) and info_project:
        return info_project

    print_report = data.get("print")

    if not isinstance(print_report, dict):
        return {}

    print_data = print_report.get("data")

    if not isinstance(print_data, dict):
        return {}

    return print_data


def print_report_state(data: dict[str, Any]) -> str | None:
    print_report = data.get("print")

    if not isinstance(print_report, dict):
        return None

    state = print_report.get("state")
    return state if isinstance(state, str) else None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def print_in_progress(data: dict[str, Any]) -> bool:
    state = print_report_state(data)

    if state in PRINT_STATES_ACTIVE:
        return True

    if state in PRINT_STATES_DONE | PRINT_STATES_STOPPED | PRINT_STATES_FAILED:
        return False

    return _int(project(data).get("print_status")) in PRINT_STATUS_ACTIVE


def print_paused(data: dict[str, Any]) -> bool:
    if print_report_state(data) in PRINT_STATES_PAUSED:
        return True

    return bool(_int(project(data).get("pause"))) and print_in_progress(data)


def print_complete(data: dict[str, Any]) -> bool:
    if print_report_state(data) in PRINT_STATES_DONE:
        return True

    return _int(project(data).get("print_status")) == PRINT_STATUS_FINISHED


def print_failed(data: dict[str, Any]) -> bool:
    return print_report_state(data) in PRINT_STATES_FAILED


def print_stopped(data: dict[str, Any]) -> bool:
    return print_report_state(data) in PRINT_STATES_STOPPED


def last_print_error(data: dict[str, Any]) -> str | None:
    print_report = data.get("print")

    if not isinstance(print_report, dict) or print_report.get("state") != "failed":
        return None

    message = print_report.get("msg")
    return str(message) if message else "failed"


def task_id(data: dict[str, Any]) -> str:
    current = project(data)

    for key in ("task_id", "taskid"):
        if current.get(key) is not None:
            return str(current[key])

    print_data = payload(data, "print")

    if print_data.get("taskid") is not None:
        return str(print_data["taskid"])

    return ""


def print_settings(data: dict[str, Any]) -> dict[str, Any]:
    """Live print settings: the latest print update, else the info report."""
    settings: dict[str, Any] = {}
    info = payload(data, "info")

    for key in ("print_speed_mode", "print_speed_pct"):
        if key in info:
            settings[key] = info[key]

    current = project(data)

    for key in ("print_speed_mode", "print_speed_pct"):
        if key in current:
            settings[key] = current[key]

    current_settings = current.get("settings")

    if isinstance(current_settings, dict):
        settings.update(current_settings)

    print_data = payload(data, "print")
    update_settings = print_data.get("settings")

    if isinstance(update_settings, dict):
        settings.update(update_settings)

    return settings


def speed_modes(data: dict[str, Any]) -> dict[int, str]:
    for source in (project(data), payload(data, "info")):
        reported = source.get("print_speed_model_des")

        if not isinstance(reported, list):
            continue

        modes: dict[int, str] = {}

        for item in reported:
            if not isinstance(item, dict):
                continue

            mode = _int(item.get("print_speed_mode"))

            if mode is not None:
                modes[mode] = str(item.get("title") or mode)

        if modes:
            return modes

    return dict(DEFAULT_SPEED_MODES)


def multi_color_boxes(data: dict[str, Any]) -> list[dict[str, Any]]:
    boxes = payload(data, "multiColorBox").get("multi_color_box")

    if not isinstance(boxes, list):
        return []

    return [box for box in boxes if isinstance(box, dict)]


def multi_color_box(data: dict[str, Any], box_index: int) -> dict[str, Any]:
    boxes = multi_color_boxes(data)

    if 0 <= box_index < len(boxes):
        return boxes[box_index]

    return {}


def box_id(data: dict[str, Any], box_index: int) -> int:
    box = multi_color_box(data, box_index)
    return _int(box.get("id")) if _int(box.get("id")) is not None else box_index


def drying_status(data: dict[str, Any], box_index: int) -> dict[str, Any]:
    status = multi_color_box(data, box_index).get("drying_status")
    return status if isinstance(status, dict) else {}


def is_drying(data: dict[str, Any], box_index: int) -> bool | None:
    status = drying_status(data, box_index)

    if not status:
        return None

    return _int(status.get("status")) == 1


def drying_value(data: dict[str, Any], box_index: int, key: str) -> int | None:
    if not is_drying(data, box_index):
        return 0 if drying_status(data, box_index) else None

    return _int(drying_status(data, box_index).get(key))


def auto_feed(data: dict[str, Any], box_index: int) -> bool | None:
    value = multi_color_box(data, box_index).get("auto_feed")

    if value is None:
        return None

    return bool(_int(value))


def axis_coordinates(data: dict[str, Any]) -> dict[str, Any]:
    axis = data.get("axis")

    if not isinstance(axis, dict):
        return {}

    coordinates = payload(data, "axis").get("coordinates")
    return coordinates if isinstance(coordinates, dict) else {}


def axis_move_state(data: dict[str, Any]) -> str | None:
    axis = data.get("axis")

    if not isinstance(axis, dict) or axis.get("action") != "move":
        return None

    state = axis.get("state")
    return str(state) if state is not None else None


# Job phases used for the print event entity.
PHASE_IDLE = "idle"
PHASE_PRINTING = "printing"
PHASE_PAUSED = "paused"
PHASE_FINISHED = "finished"
PHASE_STOPPED = "stopped"
PHASE_FAILED = "failed"


def job_phase(data: dict[str, Any]) -> str:
    """One word for where the job is, the order matters: a failed or stopped
    report wins over the print_status code the info report still carries."""
    if print_failed(data):
        return PHASE_FAILED

    if print_stopped(data):
        return PHASE_STOPPED

    if print_paused(data):
        return PHASE_PAUSED

    if print_in_progress(data):
        return PHASE_PRINTING

    if print_complete(data):
        return PHASE_FINISHED

    return PHASE_IDLE


# `state` values of a print report that carry a pause or stop reason code.
_REASON_STATES = PRINT_STATES_PAUSED | PRINT_STATES_STOPPED | PRINT_STATES_FAILED


def print_reason(data: dict[str, Any]) -> dict[str, Any] | None:
    """Why the printer paused or stopped the job, from the print report envelope.

    The printer puts a reason code next to the state (e.g. 10401 paused by
    user, 11518 filament stuck). Progress pushes and command replies carry 200.
    """
    report = data.get("print")

    if not isinstance(report, dict) or report.get("state") not in _REASON_STATES:
        return None

    code = report.get("code")

    if isinstance(code, bool) or not isinstance(code, int) or code == 200:
        return None

    message = report.get("msg")
    text = REASON_TEXT.get(code) or (
        str(message) if isinstance(message, str) and message else f"Code {code}"
    )
    return {
        "code": code,
        "reason": text,
        "by_user": code in USER_REASON_CODES,
        "state": report.get("state"),
    }


def slot_loaded(slot: dict[str, Any]) -> bool:
    """A slot reports status 5 while filament sits in it."""
    return _int(slot.get("status")) == 5
