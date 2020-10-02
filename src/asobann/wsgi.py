import asobann
import asobann.app

app = asobann.app.create_app()

import logging

if __name__ == '__main__':
    if "PORT" in app.config:
        app.socketio.run(app, host="0.0.0.0", port=app.config["PORT"], log_output=False)
    else:
        app.socketio.run(app, host="0.0.0.0", log_output=False)
