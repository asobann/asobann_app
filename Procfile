# web: cd src && gunicorn --log-level debug --worker-class eventlet asobann.wsgi:app
web: cd src && gunicorn --log-level debug -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker asobann.wsgi:app
release: cd src && python -m asobann.deploy
