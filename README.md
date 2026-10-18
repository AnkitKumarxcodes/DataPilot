# DataAgent

`feed_db.py` seeds the sample CSV data into PostgreSQL or MySQL. Set
`DB_DIALECT` to `postgresql` or `mysql` and provide the matching connection
settings in `.env`. Create the target database first; the script creates its
tables and loads the CSV rows. It does not clear existing rows before loading.
