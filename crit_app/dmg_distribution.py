"""
Functions for processing results of API queries and computing damage distributions.
"""

import numpy as np

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

    return action_dps[["ability_name", "dps_50th_percentile", "amount", "percentile"]].rename(
        columns={"amount": "actual_dps_dealt"}
    )
