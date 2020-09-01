# from gevent import monkey
# monkey.patch_all()
import eventlet
eventlet.monkey_patch()


from flask_socketio import SocketIO, emit, join_room


socketio = SocketIO()


