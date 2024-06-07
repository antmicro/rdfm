# Alembic database migration configuration

RDFM server uses [Alembic](https://alembic.sqlalchemy.org/) for managing database migrations. The migration itself is automatically performed on server startup.
This directory contains Alembic's configuration generated with `alembic init`.

## Generating migration scripts

After making changes to the database layout, a new migration script needs to be created. To do this, run the following command in the `server/deploy` directory:

```bash
cd server/deploy
alembic revision --autogenerate -m "Description of changes" --rev-id=<next-id>
```

The `-m` flag is for providing a short description of changes to the layout.
Substitute `<next-id>` with the layout version (e.g. if the current version is 2, set it to 3).
As a result, a new script will be generated in the `server/alembic/versions` directory.
The `--autogenerate` flag will populate the script with operations on the database to move from the previous layout to the current one, but it has some limitations and the script needs to be reviewed after generation.
Adjust the script if any changes are required (like e.g. moving data between tables) and verify that it works, either by running the server or manually running the `alembic upgrade head` command.
Remember to commit the script to the repository together with changes to the model objects.

For details, consult the [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/).
