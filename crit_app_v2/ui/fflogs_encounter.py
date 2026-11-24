"""Dash Mantine components for FFLogs encounter selection."""

from typing import Any

import dash_mantine_components as dmc
from dash import dcc
from dash_iconify import DashIconify

from crit_app_v2.fflogs_encounters.models import Encounter, EncounterPersonnel
from crit_app_v2.game_data import JOB_SPECS, Role
from crit_app_v2.game_data.encounters import get_phase_options

_HIDDEN = {"display": "none"}
_VISIBLE = {"display": "block"}


def format_kill_time(kill_time: float) -> str:
    """Format a fight duration in seconds as ``mm:ss.mmm``.

    Raises
    ------
    ValueError
        If the duration is negative.
    """
    if kill_time < 0:
        raise ValueError("Kill time cannot be negative")
    total_ms = round(kill_time * 1000)
    minutes, remainder = divmod(total_ms, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def encounter_title(encounter: Encounter) -> str:
    """Return the encounter name with its formatted duration."""
    return f"{encounter.encounter_name} ({format_kill_time(encounter.kill_time)})"


def unsupported_encounter_message(encounter: Encounter) -> str:
    """Return feedback for an encounter that cannot be analyzed."""
    return f"Sorry, {encounter.encounter_name} is not a supported encounter."


def encounter_to_store(encounter: Encounter) -> dict[str, Any]:
    """Serialize an encounter for a ``dcc.Store``, omitting computed URL fields."""
    return encounter.model_dump(
        mode="json",
        exclude={"encounter_url": {"report_id", "fight_id"}},
    )


def phase_select_state(
    encounter: Encounter,
) -> tuple[list[dict[str, str]], str, dict[str, str]]:
    """Return phase select data, its reset value, and its visibility style."""
    options = get_phase_options(encounter.encounter_id, encounter.last_phase_index)
    data = [{"value": str(option.value), "label": option.label} for option in options]
    return data, "0", _VISIBLE if len(options) > 1 else _HIDDEN


def _player_radio(player: EncounterPersonnel, selected_role: Role) -> dmc.Radio:
    """Create a radio for a player, disabled outside the selected role."""
    glyph = JOB_SPECS[player.job].icon_glyph
    label = dmc.Group(
        [
            dmc.Text(
                glyph,
                span=True,
                size="xl",
                style={"fontFamily": "job-icons", "lineHeight": 1},
            ),
            dmc.Text(player.player_name, span=True),
        ],
        gap="xs",
    )
    return dmc.Radio(
        label=label,
        value=str(player.player_id),
        disabled=player.role is not selected_role,
        # Mantine top-aligns the radio with its label, so the tall icon glyph
        # would otherwise sit below the radio.
        styles={"body": {"alignItems": "center"}},
    )


def job_selection(
    encounter: Encounter | None,
    selected_role: Role,
    selected_player_id: str | None = None,
) -> dmc.RadioGroup:
    """Create the player selector, grouped by role.

    Only players in ``selected_role`` can be chosen. A selection outside that
    role is cleared.
    """
    sections: list[Any] = []
    value = None
    if encounter is not None:
        for role, players in encounter.players_by_role().items():
            if not players:
                continue
            sections.append(
                dmc.Stack(
                    [
                        dmc.Text(f"{role.value}s", fw=600, size="sm"),
                        *[_player_radio(player, selected_role) for player in players],
                    ],
                    gap="xs",
                )
            )
            if any(
                str(player.player_id) == selected_player_id and role is selected_role
                for player in players
            ):
                value = selected_player_id

    return dmc.RadioGroup(
        dmc.Stack(sections, gap="md"),
        id="player-select",
        value=value,
    )


def fflogs_encounter_card() -> dmc.Paper:
    """Create the FFLogs URL, phase, and job-selection card."""
    return dmc.Paper(
        [
            dcc.Store(id="loaded-encounter"),
            dmc.Stack(
                [
                    dmc.Title("Enter log to analyze"),
                    dmc.Grid(
                        [
                            dmc.GridCol(
                                dmc.TextInput(
                                    id="fflogs-url",
                                    label="Log URL",
                                    value="",
                                    placeholder="https://www.fflogs.com/reports/...",
                                ),
                                span={"base": 12, "md": 9},
                            ),
                            dmc.GridCol(
                                dmc.Button(
                                    "Submit",
                                    id="fflogs-url-button",
                                    fullWidth=True,
                                    disabled=True,
                                ),
                                span={"base": 12, "md": 3},
                                style={"display": "flex", "alignItems": "flex-end"},
                            ),
                        ],
                        gap="md",
                    ),
                    dmc.Title("", id="encounter-name-time", order=3),
                    dmc.Select(
                        id="phase-select",
                        label="Phase",
                        data=[{"value": "0", "label": "Entire Fight"}],
                        allowDeselect=False,
                        value="0",
                        w={"base": "100%", "md": "50%"},
                        style=_HIDDEN,
                    ),
                    dmc.Group(
                        [
                            dmc.Title("Select a job", order=4),
                            dmc.Tooltip(
                                dmc.ActionIcon(
                                    children=DashIconify(
                                        icon="tabler:info-circle", width=16
                                    ),
                                    id="job-select-info",
                                    buttonProps={
                                        "aria-label": "Job selection guidance"
                                    },
                                    variant="subtle",
                                    color="gray",
                                    size="sm",
                                ),
                                label="Use the role selector to analyze jobs in another role.",
                                withArrow=True,
                                multiline=True,
                                w=280,
                            ),
                        ],
                        align="center",
                        gap="xs",
                    ),
                    dmc.Box(
                        job_selection(None, Role.HEALER),
                        id="job-selection",
                    ),
                    dmc.Group(
                        [
                            dmc.Button("Analyze rotation", id="player-analyze-button"),
                            dmc.Text(id="player-analysis-feedback", c="red"),
                        ],
                        align="center",
                    ),
                ]
            ),
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        p="xl",
    )
