import {dev_inspector} from "./dev_inspector.js";
import io from 'socket.io-client'

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
    context.updateManyComponents = connector.updateManyComponents;
    context.updateWholeTable = connector.updateWholeTable;
    context.updatePlayer = connector.updatePlayer;
    context.showOthersMouseMovement = connector.showOthersMouseMovement;
    context.addComponent = connector.addComponent;
    context.addKitAndComponents = connector.addKitAndComponents;
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
    context.updateWholeTable(msg.table);
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

class ComponentUpdateBuffer {
    constructor(table) {
        this.table = table;
        this.buffer = {};
        // Keys written by a non-volatile diff in the current window, per componentId.
        // A key not in here is volatile-only and won't be persisted. Once a key is
        // marked persisted it stays persisted for the rest of the window, regardless
        // of the order volatile/non-volatile diffs for that key arrive in - e.g. a
        // drop (non-volatile) followed by more volatile updates must still be saved.
        this.persistedKeys = {};
        this.orderOfComponentId = [];
        this.componentIdsToRemove = [];
    }

    addDiff(componentId, diff, volatile) {
        Object.assign(this.updateOf(componentId), diff);
        if (this.orderOfComponentId.indexOf(componentId) < 0) {
            this.orderOfComponentId.push(componentId);
        }
        if (!volatile) {
            const persisted = this.persistedKeysOf(componentId);
            for (const key of Object.keys(diff)) {
                persisted.add(key);
            }
        }
    }

    updateOf(componentId) {
        if (!this.buffer.hasOwnProperty(componentId)) {
            this.buffer[componentId] = {};
        }
        return this.buffer[componentId];
    }

    persistedKeysOf(componentId) {
        if (!this.persistedKeys.hasOwnProperty(componentId)) {
            this.persistedKeys[componentId] = new Set();
        }
        return this.persistedKeys[componentId];
    }

    volatileKeysOf(componentId) {
        const persisted = this.persistedKeysOf(componentId);
        return Object.keys(this.updateOf(componentId)).filter((key) => !persisted.has(key));
    }

    addComponentIdToRemove(componentId) {
        this.componentIdsToRemove.push(componentId);
    }

    isEmpty() {
        return this.orderOfComponentId.length === 0 && this.componentIdsToRemove.length === 0;
    }

    buildMessageToEmit() {
        if (this.isEmpty()) {
            throw new Error('no updates to emit');
        }

        const diffs = [];
        const volatileKeys = {};
        for (const componentId of this.orderOfComponentId) {
            const diff = {};
            diff[componentId] = this.updateOf(componentId);
            diffs.push(diff);
            const keys = this.volatileKeysOf(componentId);
            if (keys.length > 0) {
                volatileKeys[componentId] = keys;
            }
        }
        return {
            eventName: 'update many components',
            data: {
                tablename: context.tablename,
                originator: context.client_connection_id,
                diffs: diffs,
                componentIdsToRemove: this.componentIdsToRemove.slice(),
                volatileKeys: volatileKeys,
            },
        }
    }

    /**
     * Reset the buffer and discard all buffered updates.
     */
    reset() {
        this.buffer = {};
        this.persistedKeys = {};
        this.orderOfComponentId.splice(0);
        this.componentIdsToRemove.splice(0);
    }

    startBufferedEmit() {
        setInterval(() => {
            try {
                const event = this.buildMessageToEmit();
                socket.emit(event.eventName, event.data);
                this.reset();
            } catch (e) {
                if (e.message === 'no updates to emit') {
                    // ignore
                } else {
                    console.log(e)
                }
            }
        }, 75);
    }
}

const componentUpdateBuffer = new ComponentUpdateBuffer();
componentUpdateBuffer.startBufferedEmit();

function pushComponentUpdate(table, componentId, diff, volatile) {
    if (!table.data.components[componentId]) {
        console.log("no such component", componentId, table.data);
    }

    dev_inspector.tracePoint('queued');
    componentUpdateBuffer.addDiff(componentId, diff, volatile === true);
    updateTableDataWithComponentDiff(table, componentId, diff);
}

function updateTableDataWithComponentDiff(table, componentId, diff) {
    const oldData = table.data;
    Object.assign(oldData.components[componentId], diff);
    table.receiveData(oldData);
}

socket.on('update many components', (msg) => {
    if (msg.tablename !== context.tablename) {
        return;
    }
    if (msg.originator === context.client_connection_id) {
        return;
    }
    context.updateManyComponents(msg.diffs, msg.componentIdsToRemove);
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


function pushNewKitAndComponents(kitData, newComponents) {
    emit("add kit", {
        tablename: context.tablename,
        originator: context.client_connection_id,
        kitData: kitData,
        newComponents: newComponents,
    })
}

socket.on("add kit", (msg) => {
    console.log("event received: add kit", msg);
    if (msg.tablename !== context.tablename) {
        return;
    }
    if (msg.originator === context.client_connection_id) {
        return;
    }
    context.addKitAndComponents(msg.kit, msg.newComponents);
});

function pushRemoveComponent(componentId) {
    console.log("pushRemoveComponent", componentId);
    componentUpdateBuffer.addComponentIdToRemove(componentId);
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
    pushNewKitAndComponents,
    pushSyncWithMe,
    joinTable,
    pushCursorMovement,
    componentUpdateBuffer,
};