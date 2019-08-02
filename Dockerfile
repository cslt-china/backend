FROM python:3.7-slim

WORKDIR /app

ADD . /app

RUN apt-get update && apt-get install build-essential vim python3-dev default-libmysqlclient-dev -y

RUN pip install --trusted-host pypi.python.org -r requirements.txt

RUN sed -i "s|locks.lock(fd, locks.LOCK_EX)|# locks.lock(fd, locks.LOCK_EX) |g" /usr/local/lib/python3.7/site-packages/django/core/files/move.py
RUN sed -i "s|locks.unlock(fd)|# locks.unlock(fd) |g" /usr/local/lib/python3.7/site-packages/django/core/files/move.py
RUN sed -i "s|locks.lock(fd, locks.LOCK_EX)|# locks.lock(fd, locks.LOCK_EX) |g" /usr/local/lib/python3.7/site-packages/django/core/files/storage.py
RUN sed -i "s|locks.unlock(fd)|# locks.unlock(fd) |g" /usr/local/lib/python3.7/site-packages/django/core/files/storage.py


ENV CSLT_DB_HOST 127.0.0.1
ENV CSLT_DB_NAME cslt
ENV CSLT_DB_USER root
ENV CSLT_DB_PASS none
ENV CSLT_SECRET_KEY none
ENV CSLT_MEDIA_ROOT /data/media
ENV CSLT_ENV qcloud
ENV CSLT_TARGET_TRAINING_COUNT 50
ENV CSLT_PENDING_APPROVAL_LIMIT 10
ENV CSLT_MINIMUM_REVIEWS 5
ENV CSLT_ONE_GLOSS_RECORDING_LIMIT 2

# CSLT API service
EXPOSE 80

# Prometheus metrics
EXPOSE 8000

CMD ["gunicorn", "-b", ":80", "cslt.wsgi", "--reload"]

