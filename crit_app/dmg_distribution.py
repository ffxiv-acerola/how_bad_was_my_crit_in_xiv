"""
Functions for processing results of API queries and computing damage distributions.
"""

import json

import pandas as pd
import numpy as np
from ffxiv_stats import Rate

### Data ###
# Ability IDs
with open("abilities.json", "r") as f:
    abilities = json.load(f)

action_potencies = pd.read_csv("dps_potencies.csv")
int_ids = np.asarray(list(abilities.keys()), dtype=int).tolist()
abilities = dict(zip(int_ids, abilities.values()))

# FIXME: move to file
crit_buffs = {
    "Chain Stratagem": 0.1,
    "Battle Litany": 0.1,
    "The Wanderer's Minuet": 0.02,
    "Devilment": 0.2,
}

dh_buffs = {"Battle Voice": 0.2, "Devilment": 0.2}

abbreviations = {
    "Mug": "Mug",
    "Vulnerability Up": "Mug",
    "Arcane Circle": "AC",
    "Battle Litany": "BL",
    "Brotherhood": "BH",
    "Left Eye": "LH",
    "Battle Voice": "BV",
    "Radiant Finale": "RF",
    "Radiant Finale 1": "RF1",
    "Radiant Finale 2": "RF2",
    "Radiant Finale 3": "RF3",
    "The Wanderer's Minuet": "WM",
    "Mage's Ballad": "MB",
    "Army's Paeon": "AP",
    "Technical Finish": "TF",
    "Devilment": "DV",
    "Embolden": "EM",
    "Searing Light": "SL",
    "Chain Stratagem": "CS",
    "Divination": "DIV",
    "Card3": "Card3",
    "Card6": "Card6",
    "Harmony of Mind": "HoM",
    "Medicated": "Pot",
    "No Mercy": "NM",
    "Damage Down": "DD",  # oof
    "Weakness": "WK",  # ooof
    "Brink of Death": "BD",  # oooof
}

ranged_cards = ["The Bole", "The Spire", "The Ewer"]
melee_cards = ["The Balance", "The Spear", "The Arrow"]


def ast_card_buff(job, card_name):
    """
    Get the buff strength of a card given  the job and card tuple.
    """
    ranged_jobs = [
        "WhiteMage",
        "Sage",
        "Astrologian",
        "Scholar",
        "Summoner",
        "RedMage",
        "BlackMage",
        "Dancer",
        "Bard",
        "Machinist",
    ]
    melee_jobs = [
        "Ninja",
        "Samurai",
        "Monk",
        "Reaper",
        "Dragoon",
        "DarkKnight",
        "Gunbreaker",
        "Warrior",
        "Paladin",
    ]

    ranged_cards = ["The Bole", "The Spire", "The Ewer"]
    melee_cards = ["The Balance", "The Spear", "The Arrow"]

    if (job in ranged_jobs and card_name in ranged_cards) or (
        job in melee_jobs and card_name in melee_cards
    ):
        card_strength = 6
    else:
        card_strength = 3
    return f"Card{card_strength}", 1 + card_strength / 100


def estimate_radiant_finale_strength(elapsed_time):
    """
    Very hacky way of estimating Radiant Finale strength.
    Values under 100s assume it's the first usage and there's only a 2% buff.
    Values over 100s assume 3 songs have been played and it's the full 6% buff.
    """
    if elapsed_time < 100:
        return "Radiant Finale 1"
    else:
        return "Radiant Finale 3"

def when_was_darkside_up():
    pass

def create_action_df(
    actions, crit_stat, dh_stat, job, medication_amt=262, medicated_buff_offset=0.05
):
    """
    Turn the actions response from FFLogs API into a dataframe of actions.
    This serves as the precursor to the rotation dataframe, which is grouped by unique action and counted.
    """
    actions_df = pd.DataFrame(actions)
    # Only keep the "prepares action" or dot ticks
    actions_df = actions_df[
        (actions_df["type"] == "calculateddamage")
        | (actions_df["type"] == "damage") & (actions_df["tick"])
    ]

    # Unpaired didn't have damage go off, filter these out.
    # This column wont exist if there aren't any unpaired actions though.

    if "unpaired" in actions_df.columns:
        actions_df = actions_df[actions_df["unpaired"] != True]

    # Buffs column won't show up if nothing is present, so make one with nans
    if "buffs" not in pd.DataFrame(actions).columns:
        actions_df["buffs"] = np.NaN
        actions_df["buffs"] = actions_df["buffs"].astype("object")

    actions_df["ability_name"] = actions_df["abilityGameID"].replace(abilities)
    actions_df["elapsed_time"] = (
        actions_df["timestamp"] - actions_df["timestamp"].iloc[0]
    ) / 1000
    # Filter/rename columns
    actions_df = actions_df[
        [
            "timestamp",
            "elapsed_time",
            "type",
            "sourceID",
            "targetID",
            "abilityGameID",
            "ability_name",
            "buffs",
            "amount",
            "tick",
            "multiplier",
        ]
    ].rename(columns={"buffs": "buff_names"})

    # Add (tick) to a dot tick so the base ability name for
    # application and ticks are distinct - e.g., Dia and Dia (tick)
    actions_df["ability_name"] = np.select(
        [actions_df["tick"] == True],
        [actions_df["ability_name"] + " (tick)"],
        default=actions_df["ability_name"],
    )

    # Split up buffs
    # I forgot why I replaced nan with -11, but it's probably important
    buffs = [
        str(x)[:-1].split(".") for x in actions_df["buff_names"].replace({np.NaN: -11})
    ]
    buffs = [list(map(int, x)) for x in buffs]
    buffs = [[abilities[b] for b in k] for k in buffs]

    # Start to handle hit type buffs + medication
    r = Rate(crit_stat, dh_stat)

    multiplier = actions_df["multiplier"].tolist()
    name = actions_df["ability_name"].tolist()

    main_stat_adjust = [0] * len(buffs)
    crit_hit_rate_mod = [0] * len(buffs)
    direct_hit_rate_mod = [0] * len(buffs)
    p = [0] * len(buffs)

    # Loop over buffs/pots to create adjustments to rates/main stat
    # This is probably able to be done more efficiently with broadcasting/lambda functions
    # But it's fast enough and far from the most computationally expensive step
    for idx, b in enumerate(buffs):
        for b_idx, s in enumerate(b):
            if s in crit_buffs.keys():
                crit_hit_rate_mod[idx] += crit_buffs[s]

            elif s in dh_buffs.keys():
                direct_hit_rate_mod[idx] += dh_buffs[s]

            elif s == "Medicated":
                main_stat_adjust[idx] += medication_amt
                multiplier[idx] /= 1 + medicated_buff_offset

            if s == "Radiant Finale":
                buffs[idx][b_idx] = estimate_radiant_finale_strength(
                    actions_df.iloc[idx]["elapsed_time"]
                )

            if s in ranged_cards + melee_cards:
                buffs[idx][b_idx] = ast_card_buff(job, b)[0]
            # TODO: need to handle auto CH/DH
            # TODO: handle pets

        # Create a unique action name based on the action + all buffs present
        if None not in b:
            short_b = list(map(abbreviations.get, b))
            name[idx] = name[idx] + "-" + "_".join(sorted(short_b))

        # FFlogs is nice enough to give us the overall damage multiplier
        multiplier[idx] = multiplier[idx]
        p[idx] = r.get_p(crit_hit_rate_mod[idx], direct_hit_rate_mod[idx])

    # Assemble the action dataframe
    # Later we can groupby/count to create a rotation dataframe
    actions_df["buff_names"] = buffs
    actions_df["multiplier"] = multiplier
    actions_df["action_name"] = name
    actions_df[["p_n", "p_c", "p_d", "p_cd"]] = np.array(p)
    actions_df["main_stat_add"] = main_stat_adjust
    actions_df["l_c"] = r.crit_dmg_multiplier()
    return actions_df


def create_rotation_df(actions_df, action_potencies=action_potencies):
    # Count how many times each action is performed
    value_counts = (
        pd.DataFrame(actions_df[["action_name"]].value_counts())
        .reset_index()
        .rename(columns={"count": "n", 0: "n"})
    )  # looks like different pandas version give different column names for the counts.

    # Get potencies and rename columns
    rotation_df = (
        actions_df.merge(value_counts, on="action_name")
        .merge(action_potencies, left_on="abilityGameID", right_on="ability_id")
        .drop_duplicates(subset=["action_name", "n"])
        .sort_values("n", ascending=False)
        .rename(columns={"multiplier": "buffs", "ability_name_x": "base_action"})
        .reset_index(drop=True)
    )[
        [
            "action_name",
            "base_action",
            "n",
            "p_n",
            "p_c",
            "p_d",
            "p_cd",
            "buffs",
            "l_c",
            "main_stat_add",
            "potency",
            "damage_type",
        ]
    ]
    return rotation_df.sort_values("action_name")


def get_dmg_percentile(dps, dmg_distribution, dmg_distribution_support):
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
        lambda x: get_dmg_percentile(
            x["amount"],
            unique_actions[x["ability_name"]]["dps_distribution"],
            unique_actions[x["ability_name"]]["support"],
        )
        / 100,
        axis=1,
    )

    action_dps["expected_dps"] = action_dps["ability_name"].apply(
        lambda x: np.trapz(
            unique_actions[x]["support"] * unique_actions[x]["dps_distribution"],
            unique_actions[x]["support"],
        )
    )

    return action_dps[["ability_name", "expected_dps", "amount", "percentile"]].rename(
        columns={"amount": "actual_dps_dealt"}
    )
