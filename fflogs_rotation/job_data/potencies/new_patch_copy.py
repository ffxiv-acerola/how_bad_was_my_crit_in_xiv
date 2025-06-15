"""
Create a new potency CSV for a job to accommodate a new patch.

new_patch - {major}_{minor} patch string to create files for.
reference_patch - {major}_{minor} patch string that should be copied, usually previous patch.
overwrite - if the new patch file exists, overwrite it?
"""

import shutil
from pathlib import Path

if __name__ == "__main__":
    job_csv_path = Path("fflogs_rotation/job_data/potencies")
    potency_path = Path("fflogs_rotation/job_data")

    new_patch = "7_25"
    reference_patch = "7_2"
    overwrite = False

    potency_df_list = []
    for p in job_csv_path.glob(f"**/{reference_patch}*.csv"):
        print(p)

        job = p.stem.split("-")[1]
        new_patch_file_name = p.parent / f"{new_patch}-{job}.csv"
        new_patch_potency_exists = new_patch_file_name.exists()

        if not new_patch_potency_exists:
            shutil.copy(p, new_patch_file_name)
        elif new_patch_potency_exists & overwrite:
            shutil.copy(p, new_patch_file_name)

        pass
