docker-compose down
docker-compose up -d --build
docker exec -it truck_backend sh
python manage.py makemigrations
python manage.py migrate

docker exec -ti postgres_db psql -U bugbytes -d dev_database

-- list all tables
\dt

-- see all databases
\l

-- switch to a different database
\c dev_database

-- see columns of a specific table
\d truck

-- now your SQL queries
SELECT * FROM truck;
SELECT * FROM vendor;
SELECT * FROM repair;

-- exit
\q

python manage.py makemigrations
python manage.py migrate


# Backup
docker exec postgres_db pg_dump -U bugbytes dev_database > backup.sql

# Restore
docker exec -i postgres_db psql -U bugbytes dev_database < backup.sql