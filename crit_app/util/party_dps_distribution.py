from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike
from scipy.signal import fftconvolve

from crit_app.util.player_dps_distribution import JobAnalysis
from ffxiv_stats.moments import _coarsened_boundaries


## Data classes for party rotation ###
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


### Party rotation analysis ###
def rotation_dps_pdf(rotation_pdf_list, lb_dps=0, dmg_step=20):
    """Combine job-level damage distributions into a party-level damage distribution.

    Args:
        rotation_pdf_list (array): list of job analysis objects for the party.
        lb_dps (int, optional): Total damage dealt by Limit Break, if used. Defaults to 0.
        dmg_step (int, optional): Amount to discretize the party's damage distribution by, in damage. Defaults to 20.

    Returns:
        tuple: tuple of the party's damage distribution and damage support.
    """
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
    rotation_pdf,
    clipped_pdf,
    rotation_support,
    clipped_support,
    clipped_mean,
    rotation_mean,
    limit_break_damage=0,
    dmg_step=20,
    new_step=250,
):
    """Yield a truncated damage pdf by unconvolving a rotation clipping from the full rotation.

    Args:
        rotation_pdf (NumPy array): Numpy array of the full rotation
        clipped_pdf (array): Numpy array of the rotation clipping.
        rotation_support (array): Numpy array of the full rotation support.
        clipped_support (array): Numpy array of the rotation clipping support
        clipped_mean (float): Mean of the clipped rotation.
        rotation_mean (float): Mean of the full, untruncated rotation.
        limit_break_damage(int): Amount of limit break damage to add to the rotation_mean. Defaults to 0
        dmg_step (int, optional): Discretization step size of the support. Defaults to 20.

    Returns:
        [array]: Tuple of numpy arrays, the truncated damage PDF and truncated damage support.
    """
    # Subtracting pdfs, smallest support value is sum of
    # smallest positive support and largest negative support values
    lower = rotation_support[0] - clipped_support[-1]
    upper = rotation_support[-1] - clipped_support[0]
    lower, upper = _coarsened_boundaries(lower, upper, dmg_step)
    support = np.arange(lower, upper + dmg_step, dmg_step)

    pdf = fftconvolve(rotation_pdf, clipped_pdf)
    pdf = pdf / np.trapz(pdf, support)

    # Getting hacky here:

    # After much testing, the new support of the truncated rotation
    # isn't coming out correct, as the unconvolved pdf doesn't
    # seem to overlap the exact damage distribution obtained when the
    # rotation is truncated and the entire damage distribution is recomputed.
    # i.e., with step sizes of 1 and MGFs computed
    # My best guess is it has to do with some accumulation of discretization error.

    # However, statistical identities for means of independent variables can help us here.
    # The mean of the full rotation and clipped rotation are both known to high accuracy,
    # So the mean of the unconvolved truncated damage distribution can be known to high accuracy.
    # Let the approximate truncated mean be the mean by integrating over the unconvolved
    # damage PDF.
    # Let the exact truncated mean be the difference in means from the full rotation
    # and clipped means.
    # The difference in these means gives us how much damage the unconvolved damage PDF
    # support is off by and lets us correct the support.
    # I don't like it, but I also don't know how else to fix it.
    approximate_truncated_mean = np.trapz(pdf * support, support)
    exact_truncated_mean = rotation_mean + limit_break_damage - clipped_mean
    mean_correction = int(exact_truncated_mean - approximate_truncated_mean)

    support += mean_correction

    return pdf / np.trapz(pdf, support), support


def lb_damage_after_clipping(
    lb_damage_events_df: pd.DataFrame, filter_time: float
) -> float:
    """Filter and sum Limit Break damage events up to a specified time.

    Args:
        lb_damage_events_df (pd.DataFrame): DataFrame containing Limit Break damage events
            with columns 'timestamp' and 'amount'
        filter_time (float): Time threshold in seconds to filter events

    Returns:
        float: Sum of damage amounts for filtered events, or 0 if no events
            found before filter_time
    """
    # Filter LB damage events that happen within truncated rotation
    clipped_lb_damage = lb_damage_events_df[
        lb_damage_events_df["timestamp"] <= (filter_time)
    ]

    # Set to 0 if none exist, otherwise sum amounts.
    if len(clipped_lb_damage) == 0:
        return 0.0
    else:
        return float(clipped_lb_damage["amount"].sum())


def kill_time_analysis(
    job_rotation_analyses_list: list,
    job_rotation_pdf_list: list,
    lb_damage_events_df: pd.DataFrame,
    job_rotation_clipping_analyses: Dict[float, list],
    job_rotation_clipping_pdf_list: Dict[float, list],
    rotation_pdf: np.ndarray,
    rotation_supp: np.ndarray,
    t_clips: List[float],
    rotation_dmg_step: float,
) -> Tuple[Dict[float, Dict[str, np.ndarray]], Dict[float, Dict[str, np.ndarray]]]:
    """Calculate party DPS distributions for different kill times.

    Args:
        job_rotation_analyses_list: List of job rotation analyses
        job_rotation_pdf_list: List of job rotation PDFs
        lb_damage_events_df: DataFrame of limit break damage events
        job_rotation_clipping_analyses: Dict mapping clip times to clipped rotation analyses
        job_rotation_clipping_pdf_list: Dict mapping clip times to clipped rotation PDFs
        rotation_pdf: Full party rotation PDF
        rotation_supp: Support for full party rotation PDF
        t_clips: List of time points to analyze
        rotation_dmg_step: Step size for damage discretization

    Returns:
        Tuple containing:
            - Dict mapping clip times to truncated party distributions (shortened kill time)
            - Dict mapping clip times to party distribution clippings (part trimmed off)
    """
    party_distribution_clipping = {t: {} for t in t_clips}
    truncated_party_distribution = {t: {} for t in t_clips}

    # Create truncated damage distributions for kill time analysis
    rotation_mean = sum([j.rotation_mean for j in job_rotation_pdf_list])
    fight_end_timestamp = job_rotation_analyses_list[0].fight_end_time
    for t in t_clips:
        # Convolve rotation clippings together
        (
            party_distribution_clipping[t]["pdf"],
            party_distribution_clipping[t]["support"],
        ) = rotation_dps_pdf(job_rotation_clipping_pdf_list[t])

        # Subtract out the party rotation clipping
        # More efficient than recomputing the entire rotation,
        # which only very slightly changes.
        party_rotation_clipping_mean = sum(
            [j.rotation_mean for j in job_rotation_clipping_analyses[t]]
        )

        # Filter LB damage events that happen within truncated rotation
        clipped_lb_damage = lb_damage_after_clipping(
            lb_damage_events_df, fight_end_timestamp - 1000 * t
        )

        (
            truncated_party_distribution[t]["pdf"],
            truncated_party_distribution[t]["support"],
        ) = unconvovle_clipped_pdf(
            rotation_pdf,
            party_distribution_clipping[t]["pdf"],
            rotation_supp,
            party_distribution_clipping[t]["support"],
            party_rotation_clipping_mean,
            rotation_mean,
            limit_break_damage=clipped_lb_damage,
            dmg_step=rotation_dmg_step,
        )

    return truncated_party_distribution, party_distribution_clipping
