import os

if 'REDIS_URI' in os.environ:
    REDIS_URI = os.environ['REDIS_URI']
else:
    REDIS_URI = None

MONGO_URI = 'mongodb://localhost:27017/ex2test'
PORT = 10011

