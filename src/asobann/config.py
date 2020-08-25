import os

if 'REDIS_URI' in os.environ:
    REDIS_URI = os.environ['REDIS_URI']
else:
    REDIS_URI = None

MONGO_URI = os.environ["MONGODB_URI"] + ('&' if '?' in os.environ["MONGODB_URI"] else '?') + 'retryWrites=false'

BASE_URL = os.environ["BASE_URL"]
