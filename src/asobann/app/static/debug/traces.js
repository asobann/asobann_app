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

const colors = [
    'blue', 'chocolate', 'blueviolet', 'darkgreen', 'darkred', 'mediumblue', 'lightslategray', 'maroon', 'seagreen'
];

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
        const singleTraceEl = el('li.single_trace', {}, name);
        mount(tracesEl, singleTraceEl);

        const lociUl = el('ul');
        let colorIndex = 0;
        for (const locus in singleTrace(traceId).loci) {
            const locusEl = el('li.locus', {}, locus);
            const pointsUl = el('ul');
            for (const point of singleTrace(traceId).loci[locus]) {
                const ts = point.timestamp - startedAt;
                const pointEl = el('li.point', {}, ts + " " + point.label);
                setStyle(pointEl, { backgroundColor: colors[colorIndex], left: ts + 'px' });
                colorIndex = (colorIndex + 1) % colors.length;
                mount(pointsUl, pointEl);
            }
            mount(locusEl, pointsUl);
            mount(lociUl, locusEl);
        }
        mount(singleTraceEl, lociUl);
    }
    mount(containerEl, tracesEl);
}

function sortedTraceIds() {
    const traceIds = [];
    for (const i in traces) {
        traceIds.push(i);
    }
    traceIds.sort((a, b) => traces[a].startedAt - traces[b].startedAt);
    return traceIds;
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
