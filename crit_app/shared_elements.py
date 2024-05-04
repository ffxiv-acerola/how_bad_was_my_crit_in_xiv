from config import ETRO_TOKEN
from job_data.job_data import weapon_delays
import coreapi

# Top row stats
# Bottom row stats


def etro_build(gearset_id):
    etro_auth = coreapi.auth.TokenAuthentication(token=ETRO_TOKEN)

    # Initialize a client & load the schema document
    client = coreapi.Client(auth=etro_auth)
    schema = client.get("https://etro.gg/api/docs/")

    gearset_action = ["gearsets", "read"]
    gearset_params = {
        "id": gearset_id,
    }
    build_result = client.action(schema, gearset_action, params=gearset_params)
    job_abbreviated = build_result["jobAbbrev"]
    build_name = build_result["name"]

    if job_abbreviated in ("WHM", "AST", "SGE", "SCH"):
        build_role = "Healer"
        main_stat_str = "MND"
        secondary_stat_str = "STR"
        speed_stat_str = "SPS"
    elif job_abbreviated in ("WAR", "PLD", "DRK", "GNB"):
        build_role = "Tank"
        main_stat_str = "STR"
        secondary_stat_str = "TEN"
        speed_stat_str = "SKS"
    elif job_abbreviated in ("BLM", "SMN", "RDM"):
        build_role = "Magical Ranged"
        main_stat_str = "INT"
        secondary_stat_str = "STR"
        speed_stat_str = "SPS"
    elif job_abbreviated in ("MNK", "DRG", "SAM", "RPR", "NIN"):
        build_role = "Melee"
        main_stat_str = "STR" if job_abbreviated != "NIN" else "DEX"
        secondary_stat_str = None
        speed_stat_str = "SKS"
    elif job_abbreviated in ("BRD", "DNC", "MCH"):
        build_role = "Physical Ranged"
        main_stat_str = "DEX"
        secondary_stat_str = None
        speed_stat_str = "SKS"

    else:
        build_role = "Unsupported"
        return (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

    total_params = {}

    for p in build_result["totalParams"]:
        item = dict(p)
        key = item.pop("name")
        total_params[key] = item

    primary_stat = total_params[main_stat_str]["value"]
    dh = total_params["DH"]["value"]
    ch = total_params["CRT"]["value"]
    determination = total_params["DET"]["value"]
    speed = total_params[speed_stat_str]["value"]
    wd = total_params["Weapon Damage"]["value"]
    etro_party_bonus = build_result["partyBonus"]

    if build_role in ("Healer", "Magical Ranged"):
        if job_abbreviated == "SCH":
            secondary_stat = 350
        elif job_abbreviated == "WHM":
            secondary_stat = 214
        elif job_abbreviated == "SGE":
            secondary_stat = 233
        elif job_abbreviated == "AST":
            secondary_stat = 194
        elif job_abbreviated == "RDM":
            secondary_stat = 226
        elif job_abbreviated == "SMN":
            secondary_stat = 370
        else:
            secondary_stat = 194

    elif build_role == "Tank":
        secondary_stat = total_params[secondary_stat_str]["value"]

    else:
        secondary_stat = "None"

    # Weapon delay is read differently for normal weapons and relics
    # If normal weapon if the weapon key exists
    if build_result["weapon"] is not None:
        weapon_id = build_result["weapon"]
        weapon_action = ["equipment", "read"]
        weapon_params = {"id": weapon_id}
        weapon_result = client.action(schema, weapon_action, params=weapon_params)
        delay = weapon_result["delay"] / 1000

    # Relic weapon if the relic key exists
    elif build_result["relics"] is not None:
        weapon_id = build_result["relics"]["weapon"]
        weapon_action = ["relic", "read"]
        weapon_params = {"id": weapon_id}
        weapon_result = client.action(schema, weapon_action, params=weapon_params)
        delay = weapon_result["baseItem"]["delay"] / 1000

    # Fall back to hard-coded values by job if something goes wrong
    else:
        delay = weapon_delays[job_abbreviated]

    return (
        build_name,
        build_role,
        primary_stat,
        secondary_stat,
        determination,
        speed,
        ch,
        dh,
        wd,
        delay,
        etro_party_bonus,
    )
