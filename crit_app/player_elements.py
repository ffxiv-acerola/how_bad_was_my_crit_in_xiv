"""Helper functions for player analysis."""

from typing import Any

from dash import html

from crit_app.job_data.encounter_data import patch_times
from crit_app.job_data.roles import abbreviated_job_map


def rotation_percentile_text_map(rotation_percentile: float) -> str:
    """
    Fun text to display depending on the percentile.

    Parameters:
    rotation_percentile (float): The percentile value to map to a text description.

    Returns:
    str: A text description corresponding to the given percentile.
    """
    if rotation_percentile <= 0.2:
        return "On second thought, let's pretend this run never happened..."
    elif (rotation_percentile > 0.2) and (rotation_percentile <= 0.4):
        return "BADBADNOTGOOD."
    elif (rotation_percentile > 0.4) and (rotation_percentile <= 0.65):
        return "Mid."
    elif (rotation_percentile > 0.65) and (rotation_percentile <= 0.85):
        return "Actually pretty good."
    elif (rotation_percentile > 0.85) and (rotation_percentile <= 0.95):
        return "Really good."
    elif (rotation_percentile > 0.95) and (rotation_percentile <= 0.99):
        return "Incredibly good."
    elif rotation_percentile > 0.99:
        return "Personally blessed by Yoshi-P himself."


def ad_hoc_job_invalid(job: str, log_time: int) -> bool:
    """Collection of various conditions to make certain jobs un-analyzable.

    For example, 7.0 - 7.01 Monk's job gauge is not modeled, so it cannot be analyzed.

    These *should* be fairly rare.

    Args:
        job (str): Job name, FFLogs case style
        time (int): Start time of the log, to determine patch number.
    """

    if (
        (job == "Monk")
        & (log_time > patch_times[7.0]["start"])
        & (log_time < patch_times[7.0]["end"])
    ):
        return True
    else:
        return False


def show_job_options(
    job_information: list[dict[str, Any]], role: str, start_time: int
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """
    Show which jobs are available to analyze with radio buttons.

    Parameters:
    job_information (List[Dict[str, Any]]): List of job information dictionaries. Must contain keys: `player_name`, `job`, `player_id`, `role`.
    role (str): Role of the job.
    start_time (int): Start time of the log.

    Returns:
    Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    A tuple containing lists of radio items for each job role.
    """
    tank_radio_items = []
    healer_radio_items = []
    melee_radio_items = []
    physical_ranged_radio_items = []
    magical_ranged_radio_items = []

    for d in job_information:
        invalid = ad_hoc_job_invalid(d["job"], start_time)
        label_text = html.P(
            [
                html.Span(
                    [abbreviated_job_map[d["job"]]],
                    style={
                        "font-family": "job-icons",
                        "font-size": "1.4em",
                        "position": "relative",
                        "top": "4px",
                    },
                ),
                f" {d['player_name']}",
                " [Unsupported]" if invalid else "",
            ],
            style={"position": "relative", "bottom": "9px"},
        )
        if d["role"] == "Tank":
            tank_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": ("Tank" != role) or invalid,
                }
            )
        elif d["role"] == "Healer":
            healer_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": ("Healer" != role) or invalid,
                }
            )
        elif d["role"] == "Melee":
            melee_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": ("Melee" != role) or invalid,
                }
            )
        elif d["role"] == "Physical Ranged":
            physical_ranged_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": ("Physical Ranged" != role) or invalid,
                }
            )
        elif d["role"] == "Magical Ranged":
            magical_ranged_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": ("Magical Ranged" != role) or invalid,
                }
            )

    return (
        tank_radio_items,
        healer_radio_items,
        melee_radio_items,
        physical_ranged_radio_items,
        magical_ranged_radio_items,
    )
