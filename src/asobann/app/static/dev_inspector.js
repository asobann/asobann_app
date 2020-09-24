function baseUrl() {
    return location.protocol + "//" + location.hostname + (location.port ? ":" + location.port : "") + "/";
}

function noop() {
}

const dev_inspector = {
    // initialize with NOOP functions
    startTrace: noop,
};


function setPerformanceRecordingDebugger() {
    const context = {};
    const traces = [];
    dev_inspector.startTrace = function (name, processTraceInfo) {
        context.currentTracing = {
            name: name,
            points: []
        };
        traces.push(context.currentTracing);
        context.trace_id = Math.floor(Math.random() * 1000000000);

        if(processTraceInfo) {
            processTraceInfo(context.trace_id);
        }
    }
    dev_inspector.tracePoint = function (label) {
        if(!context.currentTracing) {
            return;
        }
        context.currentTracing.points.push({
            trace_id: context.trace_id,
            label: label,
            timestamp: Date.now()
        });
    }

    const button = document.createElement('button');
    button.setAttribute('id', 'show_performance_recording');
    button.innerText = 'Show Performance Recording';
    button.addEventListener('click', () => {
        alert(JSON.stringify(traces));
    });
    document.getElementsByTagName('body')[0]. appendChild(button)
}

(function () {
    (async () => {
        const url = baseUrl() + "debug_setting";
        const response = await fetch(url);
        const data = response.json();
        const setting = await data;

        if (setting.performanceRecording) {
            setPerformanceRecordingDebugger();
        }
    })();
})();


export {dev_inspector};
