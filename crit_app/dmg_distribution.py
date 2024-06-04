"""
Functions for processing results of API queries and computing damage distributions.
"""

from dataclasses import dataclass
from typing import List

import numpy as np
from numpy.typing import ArrayLike
from scipy.signal import fftconvolve

from ffxiv_stats.moments import _coarsened_boundaries


### Data classes for party rotation ###
def damage_percentile(damage, damage_pdf, damage_support):
    """
    Compute the CDF from a PDF and support, then find the corresponding percentile a value has

    inputs:
    dps - float, DPS value to find a percentile
    dmg_distribution - NumPy array of the DPS distribution
    dmg_distribution_support - NumPy array of the support ("x values") corresponding to the DPS distribution

    returns
    percentile (as a percent)
    """
    dx = damage_support[1] - damage_support[0]
    F = np.cumsum(damage_pdf) * dx
    return F[(np.abs(damage_support - damage)).argmin()]


@dataclass
class KillTime:
    def _compute_kill_time_percentile(self, boss_hp, damage_pdf, damage_support):
        """
        Compute the CDF from a PDF and support, then find the corresponding percentile a value has

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
class PartyRotationClipping(KillTime):
    seconds_shortened: float
    boss_hp: int
    shortened_damage_distribution: ArrayLike
    shortened_damage_support: ArrayLike
    damage_distribution_clipping: ArrayLike
    damage_distribution_clipping_support: ArrayLike
    percentile: float = 0

    def __post_init__(self):
        self.percentile = self._compute_kill_time_percentile(
            self.boss_hp,
            self.shortened_damage_distribution,
            self.shortened_damage_support,
        )


@dataclass
class PartyRotation(KillTime):
    party_id: str
    boss_hp: int
    party_damage_distribution: ArrayLike
    party_damage_support: ArrayLike
    shortened_rotations: List[PartyRotationClipping]
    percentile: float = 0

    def __post_init__(self):
        self.percentile = self._compute_kill_time_percentile(
            self.boss_hp,
            self.party_damage_distribution,
            self.party_damage_support,
        )


@dataclass
class JobRotationClippings:
    clipping_duration: List[int]
    rotation_clipping: List
    analysis_clipping: List


def get_dps_dmg_percentile(dps, dmg_distribution, dmg_distribution_support):
    """
    Compute the CDF from a PDF and support, then find the corresponding percentile a value has

    inputs:
    dps - float, DPS value to find a percentile
    dmg_distribution - NumPy array of the DPS distribution
    dmg_distribution_support - NumPy array of the support ("x values") corresponding to the DPS distribution

    returns
    percentile (as a percent)
    """
    dx = dmg_distribution_support[1] - dmg_distribution_support[0]
    F = np.cumsum(dmg_distribution) * dx
    return F[(np.abs(dmg_distribution_support - dps)).argmin()] * 100


def get_dmg_percentile(percentile, dmg_distribution, dmg_distribution_support):
    dx = dmg_distribution_support[1] - dmg_distribution_support[0]
    F = np.cumsum(dmg_distribution) * dx
    return dmg_distribution_support[np.abs(F - percentile).argmin()]


def summarize_actions(actions_df, unique_actions, t):
    """
    List the expected DPS, actual DPS dealt, and corresponding percentile.

    Inputs:
    actions_df - pandas df, dataframe of actions from `create_action_df` in `rla.py`
    unique_actions - unique_actions_distribution attribute from Job object in `ffxiv_stats`
    t - float, time elapsed. Set t=1 for damage dealt instead of dps.
    """
    action_dps = (
        actions_df[["ability_name", "amount"]].groupby("ability_name").sum() / t
    )

    action_dps = action_dps.reset_index()
    action_dps["percentile"] = action_dps.apply(
        lambda x: get_dps_dmg_percentile(
            x["amount"],
            unique_actions[x["ability_name"]]["dps_distribution"],
            unique_actions[x["ability_name"]]["support"],
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


### Party rotation analysis ###
def rotation_dps_pdf(rotation_pdf_list, lb_dps=0, dmg_step=250):
    party_dps_distribution = fftconvolve(
        rotation_pdf_list[0].rotation_dps_distribution,
        rotation_pdf_list[1].rotation_dps_distribution,
    )

    for a in range(2, len(rotation_pdf_list)):
        party_dps_distribution = fftconvolve(
            party_dps_distribution, rotation_pdf_list[a].rotation_dps_distribution
        )

    support_min = sum([a.rotation_dps_support[0] for a in rotation_pdf_list])
    support_max = sum([a.rotation_dps_support[-1] for a in rotation_pdf_list])

    support_min, support_max = _coarsened_boundaries(support_min, support_max, dmg_step)

    supp = np.arange(support_min, support_max + dmg_step, step=dmg_step) + lb_dps

    party_dps_distribution /= np.trapz(party_dps_distribution, supp)
    return party_dps_distribution, supp


def unconvovle_clipped_pdf(
    rotation_pdf, clipped_pdf, rotation_support, clipped_support, dmg_step=250
):
    # Subtracting pdfs, smallest support value is sum of
    # smallest positive support and largest negative support values
    lower = rotation_support[0] - clipped_support[-1]
    upper = rotation_support[-1] - clipped_support[0]
    lower, upper = _coarsened_boundaries(lower, upper, dmg_step)
    new_support = np.arange(lower, upper + dmg_step, dmg_step)
    pdf = fftconvolve(rotation_pdf, clipped_pdf)
    return pdf / np.trapz(pdf, new_support), new_support
