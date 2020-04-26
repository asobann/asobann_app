import asobann

app = asobann.create_app()

if __name__ == '__main__':
    app.socketio.run(app, host="0.0.0.0")
