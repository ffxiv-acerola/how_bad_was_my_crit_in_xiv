"""Functions for processing results of API queries and computing damage distributions."""

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike
from scipy.signal import fftconvolve

### Data classes for job-level analyses


@dataclass
class JobStats:
    role: str
    level: int
    lvl_main: int
    lvl_sub: int
    job_attribute: int
    atk_mod: int
    main_stat: int
    secondary_stat: int
    determination: int
    speed_stat: int
    critical_hit: int
    direct_hit: int
    weapon_damage: int
    delay: int
    attack_multiplier: int
    determination_multiplier: int
    tenacity_multiplier: int
    weapon_damage_multiplier: int
    pet_job_attribute: int
    pet_attack_power: int
    pet_attack_power_scalar: float
    pet_attack_power_offset: float
    pet_effective_attack_power: float
    pet_atk_mod: int


@dataclass
class JobAnalysis:
    active_dps_t: float
    analysis_t: float
    rotation_mean: float
    rotation_variance: float
    rotation_std: float
    rotation_skewness: float
    rotation_dps_distribution: ArrayLike
    rotation_dps_support: ArrayLike
    unique_actions_distribution: Dict

    def interpolate_distributions(self, rotation_n=5000, action_n=5000):
        """Interpolate supplied distributions so the arrays have a fewer number of elements.

        Used after all convolving is complete

        Args:
            rotation_n (int, optional): Number of data points for rotation damage distribution. Defaults to 5000.
            action_n (int, optional): Number of data points for action damage distributions. Defaults to 5000.
        """
        lower, upper = self.rotation_dps_support[0], self.rotation_dps_support[-1]
        new_support = np.linspace(lower, upper, num=rotation_n)
        new_pdf = np.interp(
            new_support, self.rotation_dps_support, self.rotation_dps_distribution
        )

        self.rotation_dps_support = new_support
        self.rotation_dps_distribution = new_pdf

        for k, v in self.unique_actions_distribution.items():
            lower, upper = v["support"][0], v["support"][-1]
            new_support = np.linspace(lower, upper, num=action_n)
            new_pdf = np.interp(new_support, v["support"], v["dps_distribution"])

            self.unique_actions_distribution[k]["support"] = new_support
            self.unique_actions_distribution[k]["dps_distribution"] = new_pdf

        pass


### Data classes for party rotation ###
@dataclass
class KillTime:
    def _compute_kill_time_percentile(self, boss_hp, damage_pdf, damage_support):
        """
        Compute the CDF from a PDF and support, then find the corresponding percentile a value has.

        inputs:
        dps - float, DPS value to find a percentile
        dmg_distribution - NumPy array of the DPS distribution
        dmg_distribution_support - NumPy array of the support ("x values") corresponding to the DPS distribution

        returns
        percentile (as a percent)
        """
        dx = damage_support[1] - damage_support[0]
        F = np.cumsum(damage_pdf) * dx
        return F[(np.abs(damage_support - boss_hp)).argmin()]


@dataclass
class SplitPartyRotation(KillTime):
    """Party rotation analysis split into a truncated segment and a clipping segment."""

    seconds_shortened: float
    boss_hp: int
    truncated_damage_distribution: ArrayLike
    truncated_damage_support: ArrayLike
    damage_distribution_clipping: ArrayLike
    damage_distribution_clipping_support: ArrayLike
    percentile: float = 0

    def __post_init__(self):
        self.percentile = self._compute_kill_time_percentile(
            self.boss_hp,
            self.truncated_damage_distribution,
            self.truncated_damage_support,
        )


@dataclass
class PartyRotation(KillTime):
    party_id: str
    boss_hp: int
    active_dps_time: float
    limit_break_events: pd.DataFrame
    party_mean: float
    party_std: float
    party_skewness: float
    party_damage_distribution: ArrayLike
    party_damage_support: ArrayLike
    shortened_rotations: List[SplitPartyRotation]
    percentile: float = 0

    def __post_init__(self):
        self.percentile = self._compute_kill_time_percentile(
            self.boss_hp,
            self.party_damage_distribution,
            self.party_damage_support,
        )

    def interpolate_distributions(self, rotation_n=5000, split_n=5000):
        """Interpolate supplied distributions so the arrays have a fewer number of elements.

        Used after all convolving is complete

        Args:
            rotation_n (int, optional): Number of data points for rotation damage distribution. Defaults to 5000.
            action_n (int, optional): Number of data points for action damage distributions. Defaults to 5000.
        """
        lower, upper = self.party_damage_support[0], self.party_damage_support[-1]
        new_support = np.linspace(lower, upper, num=rotation_n)
        new_pdf = np.interp(
            new_support, self.party_damage_support, self.party_damage_distribution
        )

        self.party_damage_support = new_support
        self.party_damage_distribution = new_pdf

        for idx, r in enumerate(self.shortened_rotations):
            # Rotation clippings
            lower, upper = (
                r.damage_distribution_clipping_support[0],
                r.damage_distribution_clipping_support[-1],
            )
            new_support = np.linspace(lower, upper, num=split_n)
            new_pdf = np.interp(
                new_support,
                r.damage_distribution_clipping_support,
                r.damage_distribution_clipping,
            )

            self.shortened_rotations[
                idx
            ].damage_distribution_clipping_support = new_support
            self.shortened_rotations[idx].damage_distribution_clipping = new_pdf

            # Truncated rotation
            lower, upper = (
                r.truncated_damage_support[0],
                r.truncated_damage_support[-1],
            )
            new_support = np.linspace(lower, upper, num=split_n)
            new_pdf = np.interp(
                new_support,
                r.truncated_damage_support,
                r.truncated_damage_distribution,
            )

            self.shortened_rotations[idx].truncated_damage_support = new_support
            self.shortened_rotations[idx].truncated_damage_distribution = new_pdf

        pass


@dataclass
class JobRotationClippings:
    clipping_duration: List[int]
    rotation_clipping: List
    analysis_clipping: List[JobAnalysis]


def job_analysis_to_data_class(job_analysis_object, active_dps_time):
    return JobAnalysis(
        active_dps_time,
        job_analysis_object.t,
        job_analysis_object.rotation_mean,
        job_analysis_object.rotation_variance,
        job_analysis_object.rotation_std,
        job_analysis_object.rotation_skewness,
        job_analysis_object.rotation_dps_distribution,
        job_analysis_object.rotation_dps_support,
        job_analysis_object.unique_actions_distribution,
    )


def get_dps_dmg_percentile(dps, dmg_distribution, dmg_distribution_support, t_div=1):
    """
    Compute the CDF from a PDF and support, then find the corresponding percentile a value has.

    inputs:
    dps - float, DPS value to find a percentile
    dmg_distribution - NumPy array of the DPS distribution
    dmg_distribution_support - NumPy array of the support ("x values") corresponding to the DPS distribution

    returns
    percentile (as a percent)
    """
    if t_div > 1:
        dmg_distribution_support /= t_div
        dmg_distribution = dmg_distribution / np.trapz(
            dmg_distribution, dmg_distribution_support
        )

    dx = dmg_distribution_support[1] - dmg_distribution_support[0]
    F = np.cumsum(dmg_distribution) * dx
    return F[(np.abs(dmg_distribution_support - dps)).argmin()] * 100


def get_dmg_percentile(percentile, dmg_distribution, dmg_distribution_support):
    dx = dmg_distribution_support[1] - dmg_distribution_support[0]
    F = np.cumsum(dmg_distribution) * dx
    return dmg_distribution_support[np.abs(F - percentile).argmin()]


def summarize_actions(actions_df, unique_actions, active_dps_time, analysis_time):
    """
    List the expected DPS, actual DPS dealt, and corresponding percentile.

    Inputs:
    actions_df - pandas df, dataframe of actions from `create_action_df` in `rla.py`
    unique_actions - unique_actions_distribution attribute from Job object in `ffxiv_stats`
    t - float, time elapsed. Set t=1 for damage dealt instead of dps.
    """

    if analysis_time == 1:
        t_div = active_dps_time
    else:
        t_div = 1

    action_dps = (
        actions_df[["ability_name", "amount"]].groupby("ability_name").sum()
        / active_dps_time
    )

    action_dps = action_dps.reset_index()
    action_dps["percentile"] = action_dps.apply(
        lambda x: get_dps_dmg_percentile(
            x["amount"],
            unique_actions[x["ability_name"]]["dps_distribution"],
            unique_actions[x["ability_name"]]["support"],
            t_div,
        )
        / 100,
        axis=1,
    )

    action_dps["dps_50th_percentile"] = action_dps["ability_name"].apply(
        lambda x: get_dmg_percentile(
            0.5,
            unique_actions[x]["dps_distribution"],
            unique_actions[x]["support"],
        )
    )

    return action_dps[
        ["ability_name", "dps_50th_percentile", "amount", "percentile"]
    ].rename(columns={"amount": "actual_dps_dealt"})
