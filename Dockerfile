FROM python:2.7-slim

WORKDIR /data

COPY ./requirements.txt /data/requirements.txt
RUN pip install -r requirements.txt

ADD . /data

USER nobody
CMD ["/data/run.sh"]
