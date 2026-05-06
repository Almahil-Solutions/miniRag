## Run Alembic Migrations


### Configuration

- Initialize the migrations:
```bash

cd src/models/db_schemes/minirag/
# Initialize the migrations in a subfolder named alembic, and link alembic.ini file to the root of the project.
alembic init alembic
```

- Copy the example alembic.ini file to alembic.ini:
```bash
cp alembic.ini.EXAMPLE alembic.ini
```
- Update the `alembic.ini` file with your database connection string in the `sqlalchemy.url` field:
```ini
sqlalchemy.url = driver://user:pass@localhost/dbname
```

### Generate a new migration script
```bash
alembic revision --autogenerate -m "New migration comment"
```

### Apply migrations or upgrade to the latest version
```bash
alembic upgrade head
```
