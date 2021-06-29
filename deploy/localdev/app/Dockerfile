FROM ubuntu:20.04
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
RUN apt-get -y update
RUN apt-get install -y python3 python3-pip
RUN pip3 install pipenv
VOLUME ["/app"]
WORKDIR /app
ENV PYTHONPATH=/app/src:/app
CMD pipenv install -d ; cd src/asobann ; FLASK_ENV=development pipenv run python -m asobann.deploy ; FLASK_ENV=development pipenv run python -m asobann.wsgi

# CMD pipenv install -d ; FLASK_ENV=development pipenv run gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 -b '0.0.0.0:5000' asobann.wsgi:app
