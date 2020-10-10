import {dev_inspector} from "./dev_inspector.js";
import io from 'socket.io-client'
import {expect} from "@jest/globals";

const socket = io(
    // {
    //     transports: ['websocket']
    // }
);

const context = {
    client_connection_id: 'xxxxxxxxxxxx'.replace(/[x]/g, function (/*c*/) {
        return (Math.random() * 16 | 0).toString(16);
    }),
};

function emit(eventName, data) {
    dev_inspector.tracePoint('emitted');
    socket.emit(eventName, data);
}

function setTableContext(tablename, connector) {
    context.tablename = tablename;
    context.initializeTable = connector.initializeTable;
    context.updateSingleComponent = connector.updateSingleComponent;
    context.updateManyComponents = connector.updateManyComponents;
    context.update_whole_table = connector.update_whole_table;
    context.updatePlayer = connector.updatePlayer;
    context.showOthersMouseMovement = connector.showOthersMouseMovement;
    context.addComponent = connector.addComponent;
    context.addKit = connector.addKit;
}

socket.on("load table", (msg) => {
    context.initializeTable(msg);
});

socket.on('connect', () => {
    emit('come by table', { tablename: context.tablename });
});

socket.on("refresh table", (msg) => {
    console.log("event received: refresh table", msg);
    if (msg.tablename !== context.tablename) {
        return;
    }
    context.update_whole_table(msg.table);
});

socket.on("confirmed player name", (msg) => {
    console.log("confirmed player name: ", msg);
    context.updatePlayer({ name: msg.player.name });
});


socket.on("mouse movement", (msg) => {
    if (msg.tablename !== context.tablename) {
        return;
    }
    context.showOthersMouseMovement(msg.playerName, msg.mouseMovement);
});

// sending out component update to server is queued and actually emit()ted intermittently
const componentUpdateQueue = [];
const actualUpdateQueue = [];

class ComponentUpdateBuffer {
    constructor(table) {
        this.table = table;
        this.buffer = {};
        this.orderOfComponentId = [];
    }

    addDiff(componentId, diff) {
        Object.assign(this.updateOf(componentId), diff);
        if (this.orderOfComponentId.indexOf(componentId) < 0) {
            this.orderOfComponentId.push(componentId);
        }
    }

    updateOf(componentId) {
        if (!this.buffer.hasOwnProperty(componentId)) {
            this.buffer[componentId] = {};
        }
        return this.buffer[componentId];
    }

    buildMessageToEmit() {
        if (this.orderOfComponentId.length === 0) {
            throw 'no updates to emit';
        }

        const diffs = [];
        for(const componentId of this.orderOfComponentId) {
            const diff = {};
            diff[componentId] = this.updateOf(componentId);
            diffs.push(diff);
        }
        return {
            eventName: 'update components',
            data: {
                tablename: context.tablename,
                originator: context.client_connection_id,
                diffs: diffs,
            },
        }
    }


    /**
     * Reset the buffer and discard all buffered updates.
     */
    reset() {
        this.buffer = {};
        this.orderOfComponentId.splice(0);
    }
}

const componentUpdateBuffer = new ComponentUpdateBuffer();

function sendComponentUpdateFromQueue() {
    while (componentUpdateQueue.length > 0) {
        const update = componentUpdateQueue.shift();
        let shouldEmit = true;
        if (update.data.volatile) {
            for (const another of componentUpdateQueue) {
                if (another.data.componentId === update.data.componentId) {
                    // discard update as another is newer
                    shouldEmit = false;
                    break;
                }
            }
        }
        if (shouldEmit) {
            if (update.data.inspectionTraceId) {
                dev_inspector.tracePointByTraceId('emitted', update.data.inspectionTraceId);
            }
            socket.emit(update.eventName, update.data);
        }
    }

    while (actualUpdateQueue.length > 0) {
        const actualUpdate = actualUpdateQueue.shift();
        actualUpdate();
    }
}

setInterval(sendComponentUpdateFromQueue, 75);

function pushComponentUpdate(table, componentId, diff, volatile) {
    console.log("pushComponentUpdate", componentId, diff, volatile);
    if (!table.data.components[componentId]) {
        console.log("no such component", componentId, table.data);
    }

    const eventName = "update single component";
    diff.lastUpdated = {
        from: context.client_connection_id,
        epoch: Date.now(),
    }
    const data = {
        tablename: context.tablename,
        originator: context.client_connection_id,
        componentId: componentId,
        diff: diff,
        volatile: volatile === true,
    };
    const event = {
        eventName: eventName,
        data: data
    };
    dev_inspector.tracePoint('queued');
    dev_inspector.passTraceInfo((traceId) => data.inspectionTraceId = traceId);
    componentUpdateQueue.push(event);
    componentUpdateBuffer.addDiff(componentId, diff);
    updateTableDataWithComponentDiff(table, componentId, diff);
}

function updateTableDataWithComponentDiff(table, componentId, diff) {
    const oldData = table.data;
    Object.assign(oldData.components[componentId], diff);
    table.receiveData(oldData);
}

socket.on("update single component", (msg) => {
    if (msg.tablename !== context.tablename) {
        return;
    }
    if (msg.inspectionTraceId) {
        dev_inspector.resumeTrace(msg.inspectionTraceId);
        dev_inspector.tracePoint('receive update single component');
    }
    if (msg.originator === context.client_connection_id) {
        dev_inspector.endTrace();
        return;
    }
    context.updateSingleComponent(msg.componentId, msg.diff);
    dev_inspector.tracePoint('finished receive update single component');
    dev_inspector.endTrace();
});


socket.on('update many components', (msg) => {
    if (msg.tablename !== context.tablename) {
        return;
    }
    for (const ev of msg.events) {
        if (ev.data.inspectionTraceId) {
            dev_inspector.tracePointByTraceId('receive update many components', ev.data.inspectionTraceId);
        }
    }
    if (msg.originator === context.client_connection_id) {
        return;
    }
    context.updateManyComponents(msg.events);
});

function pushNewComponent(componentData) {
    console.log("pushNewComponent", componentData);
    emit("add component", {
        tablename: context.tablename,
        originator: context.client_connection_id,
        component: componentData,
    });
    console.log("pushNewComponent end");
}

socket.on("add component", (msg) => {
    console.log("event received: add component", msg);
    if (msg.tablename !== context.tablename) {
        return;
    }
    context.addComponent(msg.component);
});


function pushNewKit(kitData) {
    emit("add kit", {
        tablename: context.tablename,
        originator: context.client_connection_id,
        kitData: kitData,
    })
}

socket.on("add kit", (msg) => {
    console.log("event received: add kit", msg);
    if (msg.tablename !== context.tablename) {
        return;
    }
    context.addKit(msg.kit);
});

function pushRemoveKit(kitId) {
    emit("remove kit", {
        tablename: context.tablename,
        originator: context.client_connection_id,
        kitId: kitId,
    })
}

function pushRemoveComponent(componentId) {
    console.log("pushRemoveComponent", componentId);
    componentUpdateQueue.push({
        eventName: "remove component",
        data: {
            tablename: context.tablename,
            originator: context.client_connection_id,
            componentId: componentId,
        },
    });
}


function pushSyncWithMe(tableData) {
    emit("sync with me", {
        tablename: context.tablename,
        originator: context.client_connection_id,
        tableData: tableData,
    });
}

function joinTable(player, isHost) {
    emit("set player name", {
        tablename: context.tablename,
        player: {
            name: player,
            isHost: isHost,
        },
    });
}

function pushCursorMovement(playerName, mouseMovement) {
    socket.emit("mouse movement", {
        tablename: context.tablename,
        playerName: playerName,
        mouseMovement: mouseMovement,
    });
}

export {
    setTableContext,
    pushComponentUpdate,
    pushNewComponent,
    pushRemoveComponent,
    pushNewKit,
    pushRemoveKit,
    pushSyncWithMe,
    joinTable,
    pushCursorMovement,
    componentUpdateBuffer,
};