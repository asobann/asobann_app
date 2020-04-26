import os

if "MONGODB_URI" in os.environ:
    MONGO_URI = os.environ["MONGODB_URI"] + '?retryWrites=false'
else:
    MONGO_URI='mongodb://localhost:27017/ex2dev'