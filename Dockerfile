FROM python:2.7

WORKDIR /data
COPY requirements.txt /data/requirements.txt
RUN apt-get update && apt-get install -y vim && pip install bpython
RUN pip install -r requirements.txt
