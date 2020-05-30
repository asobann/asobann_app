import os

MONGO_URI = os.environ["MONGODB_URI"] + '?retryWrites=false'

