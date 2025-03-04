"""Create database and tables for saving analyzed rotations so they do not need to be recomputed again."""

import sqlite3

from crit_app.config import BLOB_URI, DB_URI

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
CREATE TABLE if not exists
    encounter (
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
        excluded_enemy_ids TEXT,
        job TEXT NOT NULL,
        role TEXT NOT NULL,
        PRIMARY KEY (report_id, fight_id, player_id)
    ) STRICT;
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
    job_build_id TEXT,
    job_build_provider TEXT,
    redo_dps_pdf_flag INTEGER NOT NULL,
    redo_rotation_flag INTEGER NOT NULL,
    primary key (analysis_id)
)
strict
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
strict
"""

create_player_analysis_creation_table = """
CREATE TABLE if not exists creation_player_analysis (
    analysis_id	TEXT NOT NULL,
    creation_ts TEXT,
    PRIMARY KEY("analysis_id")
);
"""

create_access_table = """
create table if not exists access(
    analysis_id TEXT NOT NULL,
    access_datetime TEXT NOT NULL
)
strict
"""

create_player_error_table = """
create table
    if not exists error_player_analysis (
        error_id TEXT NOT NULL,
        report_id TEXT NOT NULL,
        fight_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        encounter_id INTEGER NOT NULL,
        encounter_name TEXT NOT NULL,
        phase_id INTEGER NOT NULL,
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
        error_message TEXT NOT NULL,
        traceback TEXT NOT NULL,
        error_ts TEXT NOT NULL,
        error_active INTEGER NOT NULL,
        primary key (error_id)
    ) strict
"""

create_party_error_table = """
create table if not exists error_party_analysis(
    error_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    fight_id INTEGER NOT NULL,
    fight_phase INTEGER NOT NULL,
    encounter_id INTEGER NOT NULL,
    job TEXT NOT NULL,
    player_name TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    main_stat_no_buff INTEGER NOT NULL,
    secondary_stat_no_buff INTEGER,
    determination INTEGER NOT NULL,
    speed INTEGER NOT NULL,
    critical_hit INTEGER NOT NULL,
    direct_hit INTEGER NOT NULL,
    weapon_damage INTEGER NOT NULL,
    party_bonus REAL NOT NULL,
    medication_amount INTEGER NOT NULL,
    etro_url TEXT,
    error_message TEXT NOT NULL,
    traceback TEXT NOT NULL,
    error_ts TEXT NOT NULL,
    error_active INTEGER NOT NULL,
    primary key (error_id)
) strict;
"""

if __name__ == "__main__":
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(create_encounter_table)
    cur.execute(create_report_table)
    cur.execute(create_party_report_table)
    cur.execute(create_player_analysis_creation_table)
    cur.execute(create_access_table)
    cur.execute(create_player_error_table)
    cur.execute(create_party_error_table)
    cur.close()
    con.close()
