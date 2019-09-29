FROM jfloff/alpine-python:3.7
WORKDIR /code
COPY . .
RUN apk add libxslt-dev && cd /code && pip install --upgrade pip && pip install -r requirements.txt
