# How Bad Was My Crit in FFXIV?
Source code for howbadwasmycritinxiv.com

## Setup Instructions

The site uses:

- poetry: Python virtual environment
- gunicorn: WSGI server
- supervisor [optional]: Process control
- Nginx [optional]: HTTP web server

### Environment Variables

First, set up the necessary environment variables.

```bash
export CRIT_APP_DIR="/path/to/your/repo" # Absolute repo directory
export GUNICORN_PATH="/path/to/gunicorn" # Path to gunicorn in venv
export CRIT_APP_WORKERS=5 # (2 * N_CPU + 1)
export CRIT_APP_ERRORS_WORKERS=1
```

### config.py

Various global parameters and secrets are stored in `crit_app/config.py`.

```py
from pathlib import Path

FFLOGS_TOKEN = ""
DB_URI = Path("data/reports.db") # Path to reports.db, usually data/reports.db
BLOB_URI = Path("data/blobs") # Path to blob files, usually data/blobs
DEBUG = True # Whether to operate dash server in debug mode
DRY_RUN = False # Not really used, set to False
BASE_PATH = Path("")
ERROR_LOGIN = {"username": "password"} # Login info to access the error tracking dashboard
DASH_AUTH_SECRET = "something_long"
```

### Running with gunicorn

Two gunicorn instances are ran, one for the public-facing site (8000) and one for the private error tracking dashboard (8001). To run locally, navigate to the repo and install all dependencies using poetry

```sh
poetry install
poetry shell
```

Start the gunicorn instance by

```sh
gunicorn -w $CRIT_APP_WORKERS -b 0.0.0.0:8000 crit_app.app:server
```

and the site is locally accessible via http://localhost:8000/analysis

The error dashboard can also be accessed by running

```sh
gunicorn -w $CRIT_APP_WORKERS -b 0.0.0.0:8001 crit_app.errors_app:error_server
```

accessible via http://localhost:8001/errors.

If desired, see the wiki for more info on creating a local server.
