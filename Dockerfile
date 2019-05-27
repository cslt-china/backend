FROM python:3.7-slim

WORKDIR /app

ADD . /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt

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

# CSLT API service
EXPOSE 80

# Prometheus metrics
EXPOSE 8000

CMD ["gunicorn", "-b", ":80", "cslt.wsgi"]

