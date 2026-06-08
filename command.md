docker-compose down
docker-compose up -d --build
docker exec -it django_docker_db python manage.py shell
docker exec -ti postgres_db psql -U bugbytes -d dev_database

python manage.py makemigrations
python manage.py migrate