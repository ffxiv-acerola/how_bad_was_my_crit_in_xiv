from pathlib import Path

FFLOGS_TOKEN = ""
ETRO_TOKEN = ""
DB_URI = Path("db_uri.db").resolve()
BLOB_URI = Path("blob_uri").resolve()
DEBUG = True # run server in debug mode
DRY_RUN = False # whether to write items to DB_URI