import asobann

app = asobann.create_app({
    "MONGO_URI": 'mongodb://localhost:27017/ex2test',
    "TESTING": True,
})

if __name__ == '__main__':
    app.socketio.run(app, host="0.0.0.0", port=10011)
