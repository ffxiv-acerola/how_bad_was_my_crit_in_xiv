"""
Functions for processing results of API queries and computing damage distributions.
"""

import json
from functools import reduce

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
    "Surging Tempest": "ST",
    "Inner Release": "IR",
}

ranged_cards = ["The Bole", "The Spire", "The Ewer"]
melee_cards = ["The Balance", "The Spear", "The Arrow"]

guaranteed_hit_via_buff = {1001177: {"affected_actions": [3549, 3550], "hit_type": 3}}

guaranteed_hit_via_action = {
    16465: {"hit_type": 3},
    25753: {
        "hit_type": 3,
    },
}


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


def ground_effect_multiplier():
    pass


def guaranteed_hit_type_buff(
    ability_id,
    buff_ids,
    multiplier,
    ch_stat,
    dh_stat,
    ch_buff=0,
    dh_buff=0,
    determination=None,
):
    """
    
    """
    hit_type = 0
    r = Rate(ch_stat, dh_stat)
    # Check if a guaranteed-hit type giving buff is present
    valid_buffs = [x for x in buff_ids if x in guaranteed_hit_via_buff.keys()]
    # And if it is affecting a relevant action
    if len(valid_buffs) > 0:
        valid_action = (
            ability_id in guaranteed_hit_via_buff[valid_buffs[0]]["affected_actions"]
        )
        hit_type = guaranteed_hit_via_buff[valid_buffs[0]]["hit_type"]
    else:
        valid_action = False

    # Now check if the ability has a guaranteed hit type regardless of buff
    if ability_id in guaranteed_hit_via_action.keys():
        valid_action = True
        hit_type = guaranteed_hit_via_action[ability_id]["hit_type"]

    # Multiplier for guaranteed hit type
    if valid_action:
        multiplier *= r.get_hit_type_damage_buff(
            hit_type,
            buff_crit_rate=ch_buff,
            buff_dh_rate=dh_buff,
            determination=determination,
        )

    return multiplier, hit_type


def when_was_darkside_not_up(action_df, player_id):
    """
    Find time intervals when Darkside is not up. 
    """
    # A bit of preprocessing, filter to Darkside buff giving actions, keep ability name and time.
    darkside_df = action_df[
        action_df["ability_name"].isin(["Edge of Shadow", "Flood of Shadow"])
        & (action_df["sourceID"] == player_id)
    ][["ability_name", "elapsed_time"]].reset_index(drop=True)
    # Lag by 1 to get last darkside ability usage
    darkside_df["prior_edge_time"] = darkside_df["elapsed_time"].shift(periods=1)

    # Set up initial values of darkside timer value for when we loop through the DF
    darkside_df["darkside_cd_prior"] = 0  # darkside timer value before DS extended
    darkside_df[
        "darkside_cd_prior_falloff"
    ] = 0  # darkside timer value is before DS was extended and if the value could be negative
    darkside_df["darkside_cd_post"] = 30  # darkside timer value after DS extended

    # Why are we looping through?
    # Current row results depend on derived values from current and prior row.
    # This makes vectorized approaches trickier without a bunch of lag/lead columns
    # Lambda functions are just for loops anyways.
    # A fight will have maybe a 100 EoS usages at most, so performance doesn't matter.
    for idx, row in darkside_df.iterrows():
        if idx > 0:
            darkside_cd_prior = (
                darkside_df["darkside_cd_post"].iloc[idx - 1]
                + darkside_df["prior_edge_time"].iloc[idx]
                - darkside_df["elapsed_time"].iloc[idx]
            )
            darkside_df.at[idx, "darkside_cd_prior"] = max(0, darkside_cd_prior)
            darkside_df.at[idx, "darkside_cd_prior_falloff"] = darkside_cd_prior
            darkside_df.at[idx, "darkside_cd_post"] = min(
                60, max(0, darkside_cd_prior) + 30
            )
        else:
            darkside_df.at[idx, "darkside_cd_prior_falloff"] = (
                0 - darkside_df["elapsed_time"].iloc[idx]
            )

    # The columns we really want, time intervals when DS is not up
    darkside_df["darkside_not_up_start"] = None
    darkside_df["darkside_not_up_end"] = None
    darkside_df.loc[
        darkside_df["darkside_cd_prior_falloff"] < 0, "darkside_not_up_start"
    ] = darkside_df["elapsed_time"] + darkside_df["darkside_cd_prior_falloff"]
    darkside_df.loc[
        darkside_df["darkside_cd_prior_falloff"] < 0, "darkside_not_up_end"
    ] = darkside_df["elapsed_time"]

    # Turn into an array
    betweens = (
        darkside_df[~darkside_df["darkside_not_up_start"].isnull()][
            ["darkside_not_up_start", "darkside_not_up_end"]
        ]
        .to_numpy()
        .astype(float)
    )

    return betweens


def apply_darkside_buff(action_df, no_darkside_times, player_id, pet_id):
    """
    Apply Darkside buff to all actions. There are some gotchas, which is why it needs it's own function
        - Salted earth snapshots Darkside
        - Living shadow does not get Darkside

    """
    from buffs import damage_buffs

    def disjunction(*conditions):
        return reduce(np.logical_or, conditions)

    no_darkside_conditions = (
        action_df["elapsed_time"].between(b[0], b[1]) for b in no_darkside_times
    )
    action_df["darkside_buff"] = 1
    # Add 10% Darkside buff except
    # For living shadow
    # For salted earth (this gets snapshotted)
    action_df.loc[
        ~disjunction(*no_darkside_conditions)
        & (action_df["sourceID"] != pet_id)
        & (action_df["ability_name"] != "Salted Earth (tick)"),
        "darkside_buff",
    ] *= 1.1

    salted_earth = action_df[action_df["ability_name"] == "Salted Earth (tick)"].copy()
    salted_earth["multiplier"] = 1
    # Time since last SE eick
    salted_earth["last_tick_time"] = salted_earth["elapsed_time"] - salted_earth[
        "elapsed_time"
    ].shift(1)
    salted_earth.loc[:, "salted_earth_application"] = 0
    # If tick > 10s, then its an application, use for snapshotting DS
    salted_earth.loc[
        (salted_earth["last_tick_time"] > 10) | (salted_earth["last_tick_time"].isna()),
        "salted_earth_application",
    ] = 1
    # Group with cumsum
    salted_earth["salted_earth_group"] = salted_earth[
        "salted_earth_application"
    ].cumsum()

    # Check if salted earth snapshotted Darkside
    no_darkside_conditions_se = (
        salted_earth["elapsed_time"].between(b[0], b[1]) for b in no_darkside_times
    )
    salted_earth.loc[
        ~disjunction(*no_darkside_conditions_se)
        & (salted_earth["salted_earth_application"] == 1),
        "darkside_buff",
    ] = 1.1

    # Propagate darkside buff by groupby max
    salted_earth["darkside_buff"] = salted_earth.groupby("salted_earth_group")[
        "darkside_buff"
    ].transform("max")

    salted_earth["multiplier"] = salted_earth["buff_names"].apply(
        lambda x: np.product([damage_buffs[k] for k in x if k in damage_buffs.keys()])
    )

    action_df.loc[
        action_df["ability_name"] == "Salted Earth (tick)",
        ["darkside_buff", "multiplier"],
    ] = salted_earth[["darkside_buff", "multiplier"]]

    action_df["multiplier"] *= action_df["darkside_buff"]
    return action_df.drop(columns=["darkside_buff"])


def apply_drk_things(action_df, player_id, pet_id):
    no_darkside_times = when_was_darkside_not_up(action_df, player_id)

    action_df = apply_darkside_buff(action_df, no_darkside_times, player_id, pet_id)

    return action_df


def create_action_df(
    actions,
    crit_stat,
    dh_stat,
    determination,
    job,
    player_id,
    pet_ids=None,
    medication_amt=262,
    medicated_buff_offset=0.05,
):
    """
    Turn the actions response from FFLogs API into a dataframe of actions.
    This serves as the precursor to the rotation dataframe, which is grouped by unique action and counted.
    """
    action_df_columns = [
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

    source_id_filters = [player_id]
    if pet_ids is not None:
        source_id_filters += pet_ids

    actions_df = pd.DataFrame(actions)
    if "unpaired" in actions_df.columns:
        action_df_columns += ["unpaired"]
    # Only include player ID and any of their associated pet IDs
    actions_df = actions_df[actions_df["sourceID"].isin(source_id_filters)]

    if "tick" in actions_df.columns:
        dots_present = True
        damage_condition = (actions_df["type"] == "calculateddamage") | (
            (actions_df["type"] == "damage") & (actions_df["tick"] == True)
        )
    else:
        action_df_columns.remove("tick")
        dots_present = False
        damage_condition = actions_df["type"] == "calculateddamage"

    # Only keep the "prepares action" or dot ticks
    actions_df = actions_df[damage_condition]

    # Buffs column won't show up if nothing is present, so make one with nans
    if "buffs" not in pd.DataFrame(actions).columns:
        actions_df["buffs"] = np.NaN
        actions_df["buffs"] = actions_df["buffs"].astype("object")

    actions_df["ability_name"] = actions_df["abilityGameID"].replace(abilities)
    actions_df["elapsed_time"] = (
        actions_df["timestamp"] - actions_df["timestamp"].iloc[0]
    ) / 1000

    # Filter/rename columns
    actions_df = actions_df[action_df_columns]
    actions_df.loc[:, "buff_names"] = actions_df["buffs"]

    # Add (tick) to a dot tick so the base ability name for
    # application and ticks are distinct - e.g., Dia and Dia (tick)
    if dots_present:
        actions_df.loc[actions_df["tick"] == True, "ability_name"] = (
            actions_df["ability_name"] + " (tick)"
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
        # Check if hit type buff acts upon guaranteed hit type
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

        row = actions_df.iloc[idx]
        multiplier[idx], hit_type = guaranteed_hit_type_buff(
            row["abilityGameID"],
            b,
            multiplier[idx],
            crit_stat,
            dh_stat,
            crit_hit_rate_mod[idx],
            direct_hit_rate_mod[idx],
            determination,
        )
        # TODO: handle pets

        # Create a unique action name based on the action + all buffs present
        if None not in b:
            short_b = list(map(abbreviations.get, b))
            name[idx] = name[idx] + "-" + "_".join(sorted(short_b))

        # FFlogs is nice enough to give us the overall damage multiplier
        multiplier[idx] = multiplier[idx]
        # Hit type overrides hit type buff additions
        p[idx] = r.get_p(
            round(crit_hit_rate_mod[idx], 2),
            round(direct_hit_rate_mod[idx], 2),
            guaranteed_hit_type=hit_type,
        )

    # Assemble the action dataframe
    # Later we can groupby/count to create a rotation dataframe
    actions_df["buff_names"] = buffs
    actions_df["multiplier"] = multiplier
    actions_df["action_name"] = name
    actions_df[["p_n", "p_c", "p_d", "p_cd"]] = np.array(p)
    actions_df["main_stat_add"] = main_stat_adjust
    actions_df["l_c"] = r.crit_dmg_multiplier()

    # Job specific things
    if job == "DarkKnight":
        actions_df = apply_drk_things(actions_df, player_id, pet_ids[0])

    # Unpaired didn't have damage go off, filter these out.
    # This column wont exist if there aren't any unpaired actions though.
    # FIXME: need to include these for Darkside tracking...
    if "unpaired" in actions_df.columns:
        actions_df = actions_df[~actions_df["unpaired"]]

    actions_df.drop(columns=["unpaired"], inplace=True)
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
