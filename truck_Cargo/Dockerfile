FROM python:3.12-alpine

# Set environment variables
# Prevents Python from writing .pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Ensures Python output is sent directly to the terminal without buffering
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# install system dependencies
RUN pip install --upgrade pip

# install python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# copy project
COPY . /app/

# run server (default, overridden in compose for worker)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]