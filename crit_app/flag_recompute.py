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
    update report set recompute_flag = 1 where job in ({", ".join([f'"{x}"' for x in job_list])})
    """)
    con.commit()
    cur.close()
    con.close()
    pass

parser = argparse.ArgumentParser()

parser.add_argument("--jobs", "-j", nargs="+")
args = parser.parse_args()
job_list = args.jobs

if (job_list is not None) and (len(job_list) > 0):
    print(f"Setting the following jobs to recompute DPS distributions: {', '.join(job_list)}")
    flag_report_recompute(job_list)
    print(f"Successfully reflagged the following jobs to recompute DPS distributions for: {', '.join(job_list)}")


else:
    print("No jobs specified, exiting.")