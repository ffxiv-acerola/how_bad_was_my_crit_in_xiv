"""Create database and tables for saving analyzed rotations so they do not need to be recomputed again."""

import sqlite3

from config import BLOB_URI, DB_URI

if not (DB_URI / "../").exists():
    (DB_URI / "../").resolve().mkdir(parents=True, exist_ok=True)

if not (BLOB_URI).exists():
    (BLOB_URI).resolve().mkdir(parents=True)

if not (BLOB_URI / "job-rotation-clippings").exists():
    (BLOB_URI / "job-rotation-clippings").resolve().mkdir(parents=True)

if not (BLOB_URI / "party-analyses").exists():
    (BLOB_URI / "party-analyses").resolve().mkdir(parents=True)

if not (BLOB_URI / "error-logs").exists():
    (BLOB_URI / "error-logs").resolve().mkdir(parents=True)

create_encounter_table = """
create table if not exists encounter(
    report_id TEXT NOT NULL,
    fight_id INTEGER NOT NULL,
    encounter_id INTEGER NOT NULL,
    last_phase_index INTEGER,
    encounter_name TEXT NOT NULL,
    kill_time REAL NOT NULL,
    player_name TEXT NOT NULL,
    player_server TEXT,
    player_id INTEGER NOT NULL,
    pet_ids TEXT,
    job TEXT NOT NULL,
    role TEXT NOT NULL,
    primary key (report_id, fight_id, player_id)
)
"""

create_report_table = """
create table if not exists report(
    analysis_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    fight_id INTEGER NOT NULL,
    phase_id INTEGER NOT NULL,
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
    etro_id TEXT,
    redo_dps_pdf_flag INTEGER NOT NULL,
    redo_rotation_flag INTEGER NOT NULL,
    primary key (analysis_id)
)
"""

create_party_report_table = """
create table if not exists party_report(
    party_analysis_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    fight_id INTEGER NOT NULL,
    phase_id INTEGER NOT NULL,
    analysis_id_1 TEXT NOT NULL,
    analysis_id_2 TEXT NOT NULL,
    analysis_id_3 TEXT NOT NULL,
    analysis_id_4 TEXT NOT NULL,
    analysis_id_5 TEXT, 
    analysis_id_6 TEXT, 
    analysis_id_7 TEXT, 
    analysis_id_8 TEXT,
    redo_analysis_flag INTEGER NOT NULL,
    primary key (party_analysis_id)
)
"""

create_access_table = """
create table if not exists access(
    analysis_id TEXT NOT NULL,
    access_datetime TEXT NOT NULL
)
"""

con = sqlite3.connect(DB_URI)
cur = con.cursor()
cur.execute(create_encounter_table)
cur.execute(create_report_table)
cur.execute(create_party_report_table)
cur.execute(create_access_table)
cur.close()
con.close()
