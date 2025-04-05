function baseUrl() {
    return location.protocol + "//" + location.hostname + (location.port ? ":" + location.port : "") + "/";
}

function noop() {
}

const dev_inspector = {
    // initialize with NOOP functions
    startTrace: noop,
    resumeTrace: noop,
    endTrace: noop,
    passTraceInfo: noop,
    tracePoint: noop,
    tracePointByTraceId: noop,
};


function setPerformanceRecordingDebugger(uid) {
    const context = {};
    const traces = [];
    const MAX_TRACES = 1000; // Limit maximum number of accumulated traces
    
    function resetTrace(name, traceId) {
        context.traceId = traceId;
        context.currentTracing = {
            traceId: context.traceId,
            name: name,
            points: []
        };
        
        // Only add if we're below the limit
        if (traces.length < MAX_TRACES) {
            traces.push(context.currentTracing);
        } else {
            // Remove oldest trace if we're at capacity
            traces.shift();
            traces.push(context.currentTracing);
        }
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
        // Limit the number of points per trace
        if (context.currentTracing.points.length < 20) {
            context.currentTracing.points.push({
                label: label,
                timestamp: Date.now()
            });
        }
    }
    dev_inspector.tracePointByTraceId = function (label, traceId) {
        // Only add if we're below the limit
        if (traces.length < MAX_TRACES) {
            traces.push(
                {
                    traceId: traceId,
                    name: '',
                    points: [{
                        label: label,
                        timestamp: Date.now(),
                    }]
                }
            );
        }
    }

    function sendTraces() {
        // Check if fetch is available in this environment
        if (typeof fetch === 'undefined') {
            // In test environments without fetch, just clear the traces
            traces.length = 0;
            return;
        }
        
        // Don't allow trace queue to grow too large
        if (traces.length > MAX_TRACES / 2) {
            const toSend = [];
            // Take half of the traces, limiting the batch size
            const batchSize = Math.min(100, Math.floor(traces.length / 2));
            for (let i = 0; i < batchSize; i++) {
                if (traces[0] === context.currentTracing) {
                    break;
                }
                toSend.push(traces.shift());
            }
            
            if (toSend.length === 0) {
                return;
            }
            
            try {
                const data = {
                    traces: toSend,
                    originator: uid,
                }
                const request = new Request('/debug/add_traces', { method: 'POST', body: JSON.stringify(data) });
                request.headers.append('Content-Type', 'application/json');
                fetch(request).catch(err => {
                    console.warn("Error sending traces", err);
                    // Don't try to resend failed traces - just drop them
                });
            } catch (err) {
                console.warn("Error preparing trace request", err);
                // Clear the traces to avoid memory buildup
                traces.length = 0;
            }
        }
    }

    setInterval(sendTraces, 1000);
}

(function () {
    // Check if we're in a browser environment where fetch is available
    const isBrowser = typeof window !== 'undefined' && typeof window.fetch !== 'undefined';
    
    if (isBrowser) {
        (async () => {
            try {
                const uid = Math.floor(Math.random() * 1000000000);
                const url = baseUrl() + "/debug/setting";
                const response = await fetch(url);
                if(!response.ok) {
                    return;
                }
                const data = response.json();
                const setting = await data;

                if (setting && setting.performanceRecording) {
                    setPerformanceRecordingDebugger(uid);
                }
            } catch (err) {
                console.warn("Error initializing debug inspector:", err);
            }
        })();
    }
})();


export {dev_inspector};
