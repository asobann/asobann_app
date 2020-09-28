function baseUrl() {
    return location.protocol + "//" + location.hostname + (location.port ? ":" + location.port : "") + "/";
}

function noop() {
}

const dev_inspector = {
    // initialize with NOOP functions
    startTrace: noop,
    resumeTrace: (traceId) => {
    },
    endTrace: noop,
    passTraceInfo: noop,
    tracePoint: (label) => {
    },
    tracePointByTraceId: (label, traceId) => {
    },
};


function setPerformanceRecordingDebugger(uid) {
    const context = {};
    const traces = [];

    function resetTrace(name, traceId) {
        context.traceId = traceId;
        context.currentTracing = {
            traceId: context.traceId,
            name: name,
            points: []
        };
        traces.push(context.currentTracing);
    }

    dev_inspector.startTrace = function (name) {
        const traceId = 'xxx-xxx-xxxx'.replace(/[x]/g, function (/*c*/) {
            const s = '23456789abcdefghjkmnpqrstuvwxyz';
            return s[Math.floor(Math.random() * s.length)];
        })
        resetTrace(name, traceId);
    }
    dev_inspector.resumeTrace = function (traceId) {
        resetTrace(null, traceId);
    }
    dev_inspector.endTrace = function () {
        context.traceId = null;
        context.currentTracing = null;
    }
    dev_inspector.passTraceInfo = function (traceInfoReceiver) {
        if (!context.traceId) {
            return;
        }
        if (traceInfoReceiver) {
            traceInfoReceiver(context.traceId);
        }
    }
    dev_inspector.tracePoint = function (label) {
        if (!context.currentTracing) {
            return;
        }
        context.currentTracing.points.push({
            label: label,
            timestamp: Date.now()
        });
    }
    dev_inspector.tracePointByTraceId = function (label, traceId) {
        traces.push(
            {
                traceId: traceId,
                name: '',
                points: [{
                    label: label,
                    timestamp: Date.now(),
                }]
            }
        )
    }

    function sendTraces() {
        const toSend = [];
        while (traces.length > 0) {
            if (traces[0] === context.currentTracing) {
                break;
            }
            toSend.push(traces.shift());
        }
        if (toSend.length === 0) {
            return;
        }
        const data = {
            traces: toSend,
            originator: uid,
        }
        const request = new Request('/debug/add_traces', { method: 'POST', body: JSON.stringify(data) });
        request.headers.append('Content-Type', 'application/json');
        fetch(request);
    }

    setInterval(sendTraces, 1000);
}

(function () {
    (async () => {
        const uid = Math.floor(Math.random() * 1000000000);
        const url = baseUrl() + "/debug/setting";
        const response = await fetch(url);
        if(!response.ok) {
            return;
        }
        const data = response.json();
        const setting = await data;

        if (setting.performanceRecording) {
            setPerformanceRecordingDebugger(uid);
        }
    })();
})();


export {dev_inspector};
