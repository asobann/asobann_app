import os

if 'REDIS_URI' in os.environ:
    REDIS_URI = os.environ['REDIS_URI']
else:
    REDIS_URI = None

MONGO_URI = os.environ["MONGODB_URI"] + ('&' if '?' in os.environ["MONGODB_URI"] else '?') + 'retryWrites=false'

value = os.environ['PUBLIC_HOSTNAME']
if value.startswith('.'):
    value = value[1:]
BASE_URL = 'https://' + value

GOOGLE_ANALYTICS_ID = os.environ['GOOGLE_ANALYTICS_ID']
