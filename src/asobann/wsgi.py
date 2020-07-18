from gevent import monkey
monkey.patch_all()

import asobann

app = asobann.create_app()

if __name__ == '__main__':
    if "PORT" in app.config:
        app.socketio.run(app, host="0.0.0.0", port=app.config["PORT"])
    else:
        app.socketio.run(app, host="0.0.0.0")
