FROM python:2.7-slim

WORKDIR /data
ADD . /data

RUN pip install -r requirements.txt

USER nobody
CMD ["/data/run.sh"]
