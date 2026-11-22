# List available recipes.
default:
    just --list

# Create the database tables and blob directories if they are missing.
db-setup:
    uv run python -m crit_app_v2.db.setup

# Delete the database and all cached blob data.
db-delete:
    uv run python -m crit_app_v2.db.setup --delete
