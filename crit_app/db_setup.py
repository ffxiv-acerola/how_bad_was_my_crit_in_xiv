"""
Create database and tables for saving analyzed rotations so they do not need to be recomputed again.
"""

import sqlite3
from config import DB_URI, BLOB_URI

if not (DB_URI / "../").resolve().exists():
    (DB_URI / "../").resolve().mkdir(parents=True)

if not (BLOB_URI).exists():
    (BLOB_URI).mkdir(parents=True)

con = sqlite3.connect(DB_URI)
cur = con.cursor()

create_encounter_table = """
create table if not exists encounter(
    report_id TEXT NOT NULL,
    fight_id INTEGER NOT NULL,
    encounter_id INTEGER NOT NULL,
    encounter_name TEXT NOT NULL,
    kill_time REAL NOT NULL,
    player_name TEXT NOT NULL,
    player_server TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    pet_ids TEXT,
    job TEXT NOT NULL,
    job_type TEXT NOT NULL
)
"""

create_report_table = """
create table if not exists report(
    analysis_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    fight_id INTEGER NOT NULL,
    encounter_name TEXT NOT NULL,
    active_dps_time REAL NOT NULL,
    job TEXT NOT NULL,
    player_name TEXT NOT NULL,
    main_stat_pre_bonus INTEGER NOT NULL,
    main_stat INTEGER NOT NULL,
    main_stat_type TEXT NOT NULL,
    secondary_stat_pre_bonus INTEGER,
    secondary_stat INTEGER,
    secondary_stat_type TEXT,
    determination INTEGER NOT NULL,
    speed INTEGER NOT NULL,
    critical_hit INTEGER NOT NULL,
    direct_hit INTEGER NOT NULL,
    weapon_damage INTEGER NOT NULL,
    delay REAL NOT NULL,
    medication_amount INTEGER NOT NULL,
    party_bonus REAL NOT NULL,
    etro_id TEXT

)
"""

create_access_table = """
create table if not exists access(
    analysis_id TEXT NOT NULL,
    access_datetime TEXT NOT NULL
)
"""
cur.execute(create_encounter_table)
cur.execute(create_report_table)
cur.execute(create_access_table)
cur.close()
con.close()