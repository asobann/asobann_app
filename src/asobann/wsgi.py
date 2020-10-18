import asobann
import asobann.app

app = asobann.app.create_app()

if __name__ == '__main__':
    if "PORT" in app.config:
        app.socketio.run(app, host="0.0.0.0", port=app.config["PORT"], log_output=app.config["ACCESS_LOG"])
    else:
        app.socketio.run(app, host="0.0.0.0", log_output=app.config["ACCESS_LOG"])
