import os

if 'MONGODB_URI' in os.environ:
    MONGO_URI = f'{os.environ["MONGODB_URI"]}/ex2dev?authSource=admin'
else:
    MONGO_URI = 'mongodb://localhost:27017/ex2dev'


