const socket = io(
    {
        transports: ['websocket']
    }
);
console.log(socket);

const context = {
    client_connection_id: 'xxxxxxxxxxxx'.replace(/[x]/g, function (/*c*/) {
        return (Math.random() * 16 | 0).toString(16);
    }),
};

const bulkPropagation = {
    nested: 0,
    events: [],
};

function consolidatePropagation(proc) {
    startConsolidatedPropagation();
    proc();
    finishConsolidatedPropagationAndEmit();
}

function startConsolidatedPropagation() {
    bulkPropagation.nested += 1;
}

function finishConsolidatedPropagationAndEmit() {
    bulkPropagation.nested -= 1;
    if (bulkPropagation.nested > 0) {
        return;
    }
    console.log("finishBulkPropagateAndEmit events", bulkPropagation.events.length);
    socket.emit('bulk propagate', {
        tablename: context.tablename,
        originator: context.client_connection_id,
        events: bulkPropagation.events,
    });
    bulkPropagation.events = [];
}

function isInBulkPropagate() {
    return bulkPropagation.nested > 0;
}

function emit(eventName, data) {
    if (isInBulkPropagate()) {
        if (data.volatile) {
            return;
        }
        bulkPropagation.events.push({ eventName: eventName, data: data });
    } else {
        socket.emit(eventName, data);
    }
}

function setTableContext(tablename, connector) {
    context.tablename = tablename;
    context.initializeTable = connector.initializeTable;
    context.update_single_component = connector.update_single_component;
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
            socket.emit(update.eventName, update.data);
        }
    }
}

setInterval(sendComponentUpdateFromQueue, 75);

function pushComponentUpdate(table, componentId, diff, volatile) {
    console.log("pushComponentUpdate", componentId, diff, volatile);
    if (!table.data.components[componentId]) {
        console.log("no such component", componentId, table.data);
    }
    const oldData = table.data;
    Object.assign(oldData.components[componentId], diff);
    table.update(oldData);

    const eventName = "update single component";
    const data = {
        tablename: context.tablename,
        originator: context.client_connection_id,
        componentId: componentId,
        diff: diff,
        volatile: volatile === true,
    };
    if (isInBulkPropagate()) {
        bulkPropagation.events.push({ eventName: eventName, data: data });
    } else {
        componentUpdateQueue.push({ eventName: eventName, data: data });
    }
}

socket.on("update single component", (msg) => {
    if (msg.tablename !== context.tablename) {
        return;
    }
    if (msg.originator === context.client_connection_id) {
        return;
    }
    context.update_single_component(msg.componentId, msg.diff);
});


socket.on('update many components', (msg) => {
    if (msg.tablename !== context.tablename) {
        return;
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
    // this event will never be in bulk
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
    startConsolidatedPropagation,
    finishConsolidatedPropagationAndEmit,
    consolidatePropagation,
};