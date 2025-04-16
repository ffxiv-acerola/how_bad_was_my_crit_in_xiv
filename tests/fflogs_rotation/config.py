from crit_app.config import FFLOGS_TOKEN

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {FFLOGS_TOKEN}",
}
