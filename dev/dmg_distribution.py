"""
Functions for processing results of API queries and computing damage distributions.
"""

from functools import reduce

import pandas as pd
import numpy as np
from ffxiv_stats import Rate

### Data ###

action_potencies = pd.read_csv("dps_potencies.csv")

base_path = "/home/craig/ffxiv_repos/how_bad_was_my_crit_in_xiv/dev/job_data/"
damage_buff_df = pd.read_csv(base_path + "damage_buffs.csv")
ch_buff_table = pd.read_csv(
    base_path + "critical_hit_rate_buffs.csv", dtype={"buff_id": str}
)
dh_buff_table = pd.read_csv(
    base_path + "direct_hit_rate_buffs.csv", dtype={"buff_id": str}
)
action_potencies = pd.read_csv(base_path + "potencies.csv")

ranged_cards = damage_buff_df[
    damage_buff_df["buff_name"].isin(["The Bole", "The Spire", "The Ewer"])
]["buff_id"].tolist()
melee_cards = damage_buff_df[
    damage_buff_df["buff_name"].isin(["The Arrow", "The Balance", "The Spear"])
]["buff_id"].tolist()

guaranteed_hit_via_buff = {
    "1001177": {"affected_actions": [3549, 3550], "hit_type": 3}
}

guaranteed_hit_via_action = {
    16465: {"hit_type": 3},
    25753: {
        "hit_type": 3,
    },
}


def ast_card_buff(job, card_id):
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

    if (job in ranged_jobs and card_id in ranged_cards) or (
        job in melee_jobs and card_id in melee_cards
    ):
        card_strength = 6
    else:
        card_strength = 3
    return f"card{card_strength}", 1 + card_strength / 100


def estimate_radiant_finale_strength(elapsed_time):
    """
    Very hacky way of estimating Radiant Finale strength.
    Values under 100s assume it's the first usage and there's only a 2% buff.
    Values over 100s assume 3 songs have been played and it's the full 6% buff.
    """
    if elapsed_time < 100:
        return "RadiantFinale1"
    else:
        return "RadiantFinale3"


def estimate_ground_effect_multiplier(actions_df, ground_effect_id):
    """
    Estimate the multiplier for ground effects, as FFLogs does not seem to supply this.

    This currently does not account for multipliers which are fight-specific (de)buffs, like Damage Down.
    """
    # Check if the multiplier already exists for other actions
    # Unhashable string column of buffs, which allow duplicates to be dropped
    # Buffs are always ordered the same way
    actions_df["str_buffs"] = actions_df["buffs"].astype(str)

    # Sort of buff fact table, grouped by buff and associated multiplier
    test = actions_df.drop_duplicates(subset=["str_buffs", "multiplier"]).sort_values(
        ["str_buffs", "multiplier"]
    )[["str_buffs", "buffs", "multiplier"]]

    # Ground effects have a null multiplier, but can be imputed if
    # there exists the same set of buffs for a non ground effect
    test["multiplier"] = test.groupby("str_buffs")["multiplier"].ffill()
    test = test.drop_duplicates(subset=["str_buffs"])

    buff_stregnths = (
        damage_buff_df.drop_duplicates(subset=["buff_id", "buff_strength"])
        .set_index("buff_id")["buff_strength"]
        .to_dict()
    )

    # TODO: Could probably improve this by looking for the closest set of buffs with a multiplier
    # and then just make a small change to that
    remainder = test[test["multiplier"].isna()]
    remainder.loc[:, "multiplier"] = (
        remainder["buffs"]
        .apply(lambda x: list(map(buff_stregnths.get, x)))
        .apply(lambda x: np.prod([y for y in x if y is not None]))
    )
    multiplier_table = pd.concat([test[~test["multiplier"].isna()], remainder])

    # Apply multiplier to ground effect ticks
    ground_ticks_actions = actions_df[actions_df["abilityGameID"] == ground_effect_id]
    ground_ticks_actions = ground_ticks_actions.merge(
        multiplier_table[["str_buffs", "multiplier"]], on="str_buffs"
    )
    # If for whatever reason a multiplier already existed,
    # use that first instead of the derived one
    # combine_first is basically coalesce
    ground_ticks_actions["multiplier"] = ground_ticks_actions[
        "multiplier_x"
    ].combine_first(ground_ticks_actions["multiplier_y"])
    ground_ticks_actions.drop(columns=["multiplier_y", "multiplier_x"], inplace=True)

    # Recombine,
    # drop temporary scratch columns,
    # Re sort values
    actions_df = (
        pd.concat(
            [
                actions_df[actions_df["abilityGameID"] != ground_effect_id],
                ground_ticks_actions,
            ]
        )
        .drop(columns=["str_buffs"])
        .sort_values("elapsed_time")
    )

    return actions_df


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
    Check if an action is guaranteed critical and/or direct damage.
    If so, and hit-type buffs are present, also compute its damage buff.
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
    darkside_df["darkside_cd_prior_falloff"] = (
        0  # darkside timer value is before DS was extended and if the value could be negative
    )
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

    # This is a fun little function which allows an arbitrary
    # number of between conditions to be applied.
    # This gets used to apply the Darkside buff,
    # where the number of "between" conditions where DS is not up
    # might be variable.
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

    ### Salted earth snapshotting ###
    # The general strategy is group salted earth ticks by usage every 90s
    # If the first tick of a group (application) has Darkside,
    # all subsequent ticks snapshot Darkside too.
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

    ### End salted earth snapshotting ###
    # Now multiply out the darkside buff to the multiplier field,
    # Remove darkside buff column
    action_df.loc[
        action_df["ability_name"] == "Salted Earth (tick)",
        ["darkside_buff", "multiplier"],
    ] = salted_earth[["darkside_buff", "multiplier"]]

    action_df["multiplier"] *= action_df["darkside_buff"]
    return action_df.drop(columns=["darkside_buff"])


def apply_drk_things(actions_df, player_id, pet_id, salted_earth_id=1000749):
    """
    Apply DRK-specific transformations to the actions dataframe including:
    * Estimate damage multiplier for Salted Earth.
    * Figure out when Darkside is up.
    * Apply Darkside to actions affected by Darkside.
    """
    # Get multiplier for Salted Earth, before Darkside is applied
    actions_df = estimate_ground_effect_multiplier(actions_df, salted_earth_id)

    # Find when Darkside is not up
    no_darkside_times = when_was_darkside_not_up(actions_df, player_id)

    # Apply darkside buff, which will correctly:
    #   - Snapshot to Salted Earth
    #   - Not apply to Living Shadow
    actions_df = apply_darkside_buff(actions_df, no_darkside_times, player_id, pet_id)
    return actions_df


def create_action_df(
    actions,
    ability_name_mapping,
    unix_start_time,
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

    # These columns are almost always here, there can be some additional columns
    # which are checked for, depending if certain actions are used
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
        "bonusPercent",
    ]

    # Whether to include damage from pets by their source ID
    source_id_filters = [player_id]
    if pet_ids is not None:
        source_id_filters += pet_ids

    # Unpaired actions have a cast begin but the damage does not go out
    # These will be filtered out later, but are included because unpaired
    # actions can still grant job gauge like Darkside
    actions_df = pd.DataFrame(actions)
    actions_df = actions_df[actions_df["sourceID"].isin(source_id_filters)]

    if "unpaired" in actions_df.columns:
        action_df_columns.append("unpaired")
    # Only include player ID and any of their associated pet IDs

    if "bonusPercent" not in actions_df.columns:
        actions_df["bonusPercent"] = pd.NA
        actions_df["bonusPercent"] = actions_df["bonusPercent"].astype("Int64")

    # Damage over time/ground effect ticks
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

    # Buffs column won't show up if no buffs are present, so make one with nans
    # Only really happens in a striking dummy scenario
    if "buffs" not in pd.DataFrame(actions).columns:
        actions_df["buffs"] = pd.NA
        actions_df["buffs"] = actions_df["buffs"].astype("object")

    actions_df["ability_name"] = actions_df["abilityGameID"].map(ability_name_mapping)
    # Time in seconds relative to the first second
    actions_df["elapsed_time"] = (
        actions_df["timestamp"] - actions_df["timestamp"].iloc[0]
    ) / 1000
    # Create proper
    actions_df["timestamp"] = actions_df["timestamp"] + unix_start_time

    # Filter/rename columns
    actions_df = actions_df[action_df_columns]
    # # TODO: remove? I don't think buff names are needed anymore
    # actions_df.loc[:, "buff_names"] = actions_df["buffs"]

    # Add (tick) to a dot tick so the base ability name for
    # application and ticks are distinct - e.g., Dia and Dia (tick)
    if dots_present:
        actions_df.loc[actions_df["tick"] == True, "ability_name"] = (
            actions_df["ability_name"] + " (tick)"
        )

    actions_df["buffs"] = actions_df["buffs"].apply(
        lambda x: x[:-1].split(".") if not pd.isna(x) else ""
    )
    actions_df = actions_df.reset_index(drop=True)

    # Start to handle hit type buffs + medication
    r = Rate(crit_stat, dh_stat)

    multiplier = actions_df["multiplier"].tolist()
    name = actions_df["ability_name"].tolist()

    buff_id = actions_df["buffs"].tolist()

    main_stat_adjust = [0] * len(actions_df)
    crit_hit_rate_mod = [0] * len(actions_df)
    direct_hit_rate_mod = [0] * len(actions_df)
    p = [0] * len(actions_df)

    medication = damage_buff_df[damage_buff_df["buff_name"] == "Medicated"]
    medication_id = medication["buff_id"].iloc[0]
    medication_multiplier = medication["buff_strength"].iloc[0]

    radiant_finale_id = damage_buff_df[damage_buff_df["buff_name"] == "Radiant Finale"][
        "buff_id"
    ].iloc[0]

    # TODO: Eventually start filtering by timestamp
    critical_hit_buff_ids = ch_buff_table.set_index("buff_id")["rate_buff"].to_dict()
    direct_hit_buff_ids = dh_buff_table.set_index("buff_id")["rate_buff"].to_dict()

    # Loop actions to create adjustments to hit type rates rates/main stat
    # There are enough conditionals/looping over array columns that vectorization isn't feasible.
    for idx, row in actions_df.iterrows():
        b = row["buffs"]

        # Loop through buffs and do various things depending on the buff
        for b_idx, s in enumerate(b):
            # Adjust critical/direct hit rate according to hit-type buffs
            if s in critical_hit_buff_ids.keys():
                crit_hit_rate_mod[idx] += critical_hit_buff_ids[s]
            if s in direct_hit_buff_ids.keys():
                direct_hit_rate_mod[idx] += direct_hit_buff_ids[s]

            # Medication is treated as a 5% damage bonus.
            # ffxiv_stats directly alters the main stat, so it must be divided out
            # Ground effects have multipliers of nan, and are unaffected either way.
            if s == medication_id:
                main_stat_adjust[idx] += medication_amt
                multiplier[idx] /= medication_multiplier

            # Radiant Finale has the same ID regardless of strength
            # A new ID is created for each buff strength.
            # Different Radiant Finale strengths will lead to different
            # 1-hit damage distributions.
            if s == radiant_finale_id:
                buff_id[idx][b_idx] = estimate_radiant_finale_strength(
                    actions_df.iloc[idx]["elapsed_time"]
                )

            # All AST cards are lumped as either 6% buff or 3% buff.
            if s in ranged_cards + melee_cards:
                buff_id[idx][b_idx] = ast_card_buff(job, s)[0]

        # Check if action has a guaranteed hit type, potentially under a hit type buff.
        # Get the hit type and new damage multiplier if hit type buffs were present.
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
        # Create a unique action name based on the action + all buffs present
        if b != "":
            name[idx] = name[idx] + "-" + "_".join(sorted(buff_id[idx]))

        # Probability of each hit type, accounting for hit type buffs or
        # guaranteed hit types.
        # Hit type ignores hit type buff additions if they are present
        p[idx] = r.get_p(
            round(crit_hit_rate_mod[idx], 2),
            round(direct_hit_rate_mod[idx], 2),
            guaranteed_hit_type=hit_type,
        )

    # Assemble the action dataframe with updated values
    # Later we can groupby/count to create a rotation dataframe
    actions_df["multiplier"] = multiplier
    actions_df["action_name"] = name
    actions_df[["p_n", "p_c", "p_d", "p_cd"]] = pd.DataFrame(np.array(p))
    actions_df["main_stat_add"] = main_stat_adjust
    actions_df["l_c"] = r.crit_dmg_multiplier()

    # Job specific transformations
    if job == "DarkKnight":
        actions_df = apply_drk_things(actions_df, player_id, pet_ids[0])

    # Unpaired didn't have damage go off, filter these out.
    # This column wont exist if there aren't any unpaired actions though.
    if "unpaired" in actions_df.columns:
        actions_df = actions_df[actions_df["unpaired"] != True]

    actions_df.drop(columns=["unpaired"], inplace=True)
    return actions_df.reset_index(drop=True)


def create_rotation_df(actions_df, action_potencies=action_potencies):
    # Count how many times each action is performed
    value_counts = (
        pd.DataFrame(actions_df[["action_name"]].value_counts())
        .reset_index()
        .rename(columns={"count": "n", 0: "n"})
    )  # looks like different pandas version give different column names for the counts.

    # Get potencies and rename columns
    rotation_df = (
        actions_df.drop(columns=["buffs"])
        .merge(value_counts, on="action_name")
        .merge(action_potencies, left_on="abilityGameID", right_on="ability_id")
        .drop_duplicates(subset=["action_name", "n"])
        .sort_values("n", ascending=False)
        .rename(columns={"multiplier": "buffs", "ability_name_x": "base_action"})
        .reset_index(drop=True)
    )
    # FIXME: Filter so it's on relevant patch
    # Probably something like:
    # Have a potency record for each patch
    # filter, where timestamp between valid_start and valid_end

    # Assign potency based on whether combo, positional, or combo + positional was satisfied
    rotation_df["potency"] = rotation_df["base_potency"]
    # Combo bonus
    rotation_df.loc[
        rotation_df["bonusPercent"] == rotation_df["combo_bonus"], "potency"
    ] = rotation_df["combo_potency"]
    # Positional bonus
    rotation_df.loc[
        rotation_df["bonusPercent"] == rotation_df["positional_bonus"], "potency"
    ] = rotation_df["positional_potency"]
    # Combo bonus and positional bonus
    rotation_df.loc[
        rotation_df["bonusPercent"] == rotation_df["combo_positional_bonus"], "potency"
    ] = rotation_df["combo_positional_potency"]

    rotation_df = rotation_df[
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
    return rotation_df.sort_values(
        ["base_action", "damage_type", "n"], ascending=[True, True, False]
    )


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
