import time
from typing import List
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, make_response
)

trace_db = None


def get_trace_db():
    global trace_db
    if not trace_db:
        trace_db = current_app.mongo.db.traces
    return trace_db


def timestamp():
    return int(time.time() * 1000)


class NoOpPerformanceRecordingTrace:
    def trace_point(self, label):
        pass

    def end(self):
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

    def end(self):
        data = {
            'traces': [{
                'traceId': self.trace_id,
                'name': None,
                'points': self.points
            }],
            'originator': self.locus,
        }
        get_trace_db().insert_one({'traces': data, 'created_at': timestamp()})


def resume_trace(envelope):
    current_app.logger.debug('resume trace')
    if not current_app.config.get('DEBUG_PERFORMANCE_RECORDING', False):
        current_app.logger.debug('DEBUG_PERFORMANCE_RECORDING not set')
        return NoOpPerformanceRecordingTrace()

    if 'inspectionTraceId' in envelope:
        trace_id = envelope['inspectionTraceId']
        current_app.logger.debug('tracing activated with trace_id: ' + trace_id)
        return PerformanceRecordingTrace(trace_id)

    current_app.logger.debug('no inspectionTraceId found')
    return NoOpPerformanceRecordingTrace()
