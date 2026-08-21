import time
from typing import List

# socketioイベントハンドラはQuartのリクエスト/アプリコンテキスト外で実行されるため、
# current_appではなくcreate_app()から明示的に渡された状態を保持する。
_state = {
    'trace_db': None,
    'performance_recording': False,
}


def configure(mongo_db, performance_recording):
    _state['trace_db'] = mongo_db.traces
    _state['performance_recording'] = performance_recording


def timestamp():
    return int(time.time() * 1000)


class NoOpPerformanceRecordingTrace:
    def trace_point(self, label):
        pass

    async def end(self):
        pass


class PerformanceRecordingTrace:
    def __init__(self, trace_id):
        self.trace_id = trace_id
        self.locus = 'server'
        self.points: List = []

    def trace_point(self, label):
        point = {
            'label': label,
            'timestamp': timestamp()
        }
        self.points.append(point)

    async def end(self):
        data = {
            'traces': [{
                'traceId': self.trace_id,
                'name': None,
                'points': self.points
            }],
            'originator': self.locus,
        }
        await _state['trace_db'].insert_one({'traces': data, 'created_at': timestamp()})


def resume_trace(envelope):
    if not _state['performance_recording']:
        return NoOpPerformanceRecordingTrace()

    if 'inspectionTraceId' in envelope:
        trace_id = envelope['inspectionTraceId']
        return PerformanceRecordingTrace(trace_id)

    return NoOpPerformanceRecordingTrace()
