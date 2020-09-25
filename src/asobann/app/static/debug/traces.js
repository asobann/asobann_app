import {el, mount, unmount, setStyle, setAttr} from "../redom.es.js";

const traces = {};
let nextGetTrace = 0;  // Date.now();
async function getTraces() {
    const response = await fetch('/debug/get_traces?since=' + nextGetTrace);
    const data = await (await response).json();
    for (const e of data.data) {
        const traces = e.traces;
        appendTraces(traces);
        if (nextGetTrace < e.created_at) {
            nextGetTrace = e.created_at;
        }
    }
}

function appendTraces(newTraces) {
    const originator = newTraces.originator;
    for (const fragment of newTraces.traces) {
        const traceId = fragment.traceId;
        const name = fragment.name;
        const points = fragment.points;

        if (name) {
            setTraceName(name, singleTrace(traceId));
        }

        for (const point of points) {
            addPoint(originator, point, singleTrace(traceId));
        }
    }
}

function singleTrace(traceId) {
    if (!traces.hasOwnProperty(traceId)) {
        traces[traceId] = {
            name: '',
            loci: {},
            startedAt: Date.now(),  // MAX
        };
    }
    return traces[traceId];
}

function setTraceName(name, singleTrace) {
    singleTrace.name = name;
}

function addPoint(locus, point, singleTrace) {
    if (!singleTrace.loci.hasOwnProperty(locus)) {
        singleTrace.loci[locus] = [];
    }
    singleTrace.loci[locus].push(point);
    singleTrace.loci[locus].sort((a, b) => a.timestamp - b.timestamp);

    if (singleTrace.startedAt > point.timestamp) {
        singleTrace.startedAt = point.timestamp;
    }
}

async function refresh() {
    await getTraces();

    const containerEl = document.getElementById('traces');
    if (containerEl.childElementCount > 0) {
        containerEl.removeChild(containerEl.children[0]);
    }
    const tracesEl = el('ul');

    for (const traceId of sortedTraceIds()) {
        const startedAt = singleTrace(traceId).startedAt;
        const name = singleTrace(traceId).name;
        const singleTraceEl = el('div.single_trace', {}, name + " " + new Date(startedAt).toLocaleString() + " traceId: " + traceId);
        mount(tracesEl, singleTraceEl);

        const lociEl = el('div.loci');
        for (const locusKey of sortedLociKeys(singleTrace(traceId).loci)) {
            const points = singleTrace(traceId).loci[locusKey];
            const locusEl = el('div.locus', [el('div.locus_label', locusKey)]);
            const pointsEl = el('div.points');
            const pointsText = titleTextForPoints(points, locusKey, startedAt);
            for (const point of points) {
                const ts = point.timestamp - startedAt;
                const text = ts + "ms " + point.label;
                const pointEl = el('div.point', { title: pointsText }, text);
                setStyle(pointEl, { backgroundColor: colorForText(point.label), left: ts + 'px' });
                mount(pointsEl, pointEl);
            }
            mount(locusEl, pointsEl);
            mount(lociEl, locusEl);
        }
        mount(singleTraceEl, lociEl);
    }
    mount(containerEl, tracesEl);

    function titleTextForPoints(points, locusKey, startedAt) {
        let text = 'on ' + locusKey + ':\n';
        for(const point of points) {
            text += (point.timestamp - startedAt) + "ms " + point.label + '\n'
        }
        return text;
    }
}

function sortedTraceIds() {
    const traceIds = [];
    for (const i in traces) {
        traceIds.push(i);
    }
    traceIds.sort((a, b) => traces[a].startedAt - traces[b].startedAt);
    return traceIds;
}

function sortedLociKeys(loci) {
    const keys = [];
    for (const k in loci) {
        keys.push(k);
    }
    keys.sort((a, b) => loci[a][0].timestamp - loci[b][0].timestamp);
    return keys;

}

function colorForText(text) {
    const colors = [
        'blue', 'chocolate', 'blueviolet', 'darkgreen', 'darkred',
        'mediumblue', 'lightslategray', 'maroon', 'seagreen', 'darkblue',
        'teal', 'lightsalmon', 'indigo', 'dimgray', 'darkviolet'
    ];

    let val = 0;
    for (let i = 0; i < text.length; i++) {
        val = val ^ (text.charCodeAt(i) + i);
    }
    return colors[val % colors.length];
}

function clear() {
    for (const key in traces) {
        delete traces[key];
    }
    refresh();
}

const containerEl = document.getElementById('container');
const refreshButton = el('button', { onclick: refresh }, 'Refresh');
mount(document.body, refreshButton, containerEl);

const clearButton = el('button', { onclick: clear }, 'Clear');
mount(document.body, clearButton, containerEl);
