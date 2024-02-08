import pandas as pd
from api_queries import get_encounter_job_info, damage_events
from dmg_distribution import create_action_df, create_rotation_df

encounter_id, start_time, healer_jobs, fight_time, fight_name, r = get_encounter_job_info("cq3taLJ2KBQYMV6k", 12)
actions, fight_time, fight_name = damage_events("cq3taLJ2KBQYMV6k", 39, "Astrologian")

actions_df = create_action_df(actions, 2500, 1000, "Astrologian")
rotation_df = create_rotation_df(actions_df)