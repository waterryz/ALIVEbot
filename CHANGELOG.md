# Changelog

## Current deployment
- Replaced the `psycopg2-binary` dependency with `psycopg[binary]==3.1.18` to support Python 3.13 on Render.
- Updated `users_db.py` to use the psycopg 3 client, adopting context managers and the `dict_row` row factory when querying for stored credentials.
