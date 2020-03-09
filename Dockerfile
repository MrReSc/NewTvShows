#FROM python:alpine
FROM python:3.8-slim-buster

LABEL Name=new_tv_shows Version=0.0.1

EXPOSE 5000

WORKDIR /
COPY requirements.txt .

# pip Ausführen
RUN python3 -m pip install -r requirements.txt

COPY check.py /
COPY serien.xml /
ADD static/ /static/
ADD templates/ /templates/
RUN mkdir out

# Python Shell starten
ENTRYPOINT [ "python" ]

# check.py starten
CMD [ "-u", "check.py" ]

