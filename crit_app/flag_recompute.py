"""Set the `recompute_flag` in the report table so the analysis is recomputed.
This is necessary when the ffxiv stats module updates.
"""

import sqlite3
from config import DB_URI
import argparse

def flag_report_recompute(job_list):
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    cur.execute(f"""
    update report set redo_dps_pdf_flag = 1 where job in ({", ".join([f'"{x}"' for x in job_list])})
    """)
    con.commit()
    cur.close()
    con.close()
    pass

def flag_rotation_recompute(job_list):
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    cur.execute(f"""
    update report set redo_rotation_flag = 1 where job in ({", ".join([f'"{x}"' for x in job_list])})
    """)
    con.commit()
    cur.close()
    con.close()
    pass

parser = argparse.ArgumentParser()
parser.add_argument("--update", "-u")
parser.add_argument("--jobs", "-j", nargs="+")

args = parser.parse_args()
update = args.update
job_list = args.jobs

if update in ("rotation", "pdf"):
    if (job_list is not None) and (len(job_list) > 0):
        if update == "rotation":
            print(f"Setting the following jobs to reanalyze rotations: {', '.join(job_list)}")
            flag_rotation_recompute(job_list)

        print(f"Setting the following jobs to recompute DPS distributions: {', '.join(job_list)}")
        flag_report_recompute(job_list)
        print(f"Successfully reflagged the following jobs to recompute DPS distributions for: {', '.join(job_list)}")
    else:
        print("allowed values are 'rotation', 'pdf'")

else:
    print("No jobs specified, exiting.")