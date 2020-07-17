FROM ubuntu:18.04
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PYTHONPATH=/runner
RUN apt-get -y update
RUN apt-get install -y python3 python3-pip
RUN pip3 install pipenv
VOLUME ["/app"]
WORKDIR /app
CMD pipenv install -d ; FLASK_ENV=development pipenv run python -m asobann.wsgi