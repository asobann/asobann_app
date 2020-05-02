const socket = io();
console.log(socket);

const context = {
    client_connection_id: 'xxxxxxxxxxxx'.replace(/[x]/g, function(c) {
        return (Math.random() * 16 | 0).toString(16);
    }),
};

function setTableContext(tablename, connector) {
    context.tablename = tablename;
    context.initializeTable = connector.initializeTable;
    context.update_single_component = connector.update_single_component;
    context.update_whole_table = connector.update_whole_table;
    context.updatePlayer = connector.updatePlayer;
}

socket.on("load table", (msg) => {
    context.initializeTable(msg);
});

socket.on('connect', () => {
    socket.emit('come by table', { tablename: context.tablename });
});

socket.on("update single component", (msg) => {
    if (msg.tablename !== context.tablename) {
        return;
    }
    if (msg.originator === context.client_connection_id) {
        return;
    }
    context.update_single_component(msg.index, msg.diff);
});

socket.on("refresh table", (msg) => {
    console.log("event received: refresh table");
    if (msg.tablename !== context.tablename) {
        return;
    }
    context.update_whole_table(msg.table);
});

socket.on("confirmed player name", (msg) => {
    console.log("confirmed player name: ", msg);
    context.updatePlayer({ name: msg.player.name });
});

function pushComponentUpdate(table, index, diff, volatile) {
    const oldData = table.data;
    Object.assign(oldData.components[index], diff);
    table.update(oldData);
    socket.emit("update single component", {
        tablename: context.tablename,
        originator: context.client_connection_id,
        index: index,
        diff: diff,
        volatile: volatile === true,
    })
}

function pushNewComponent(data) {
    socket.emit("add component", {
        tablename: context.tablename,
        originator: context.client_connection_id,
        data: data,
    })
}

function pushRemoveComponent(index) {
    socket.emit("remove component", {
        tablename: context.tablename,
        originator: context.client_connection_id,
        index: index,
    })
}

function joinTable(player, isHost) {
    socket.emit("set player name", {
        tablename: context.tablename,
        player: {
            name: player,
            isHost: isHost,
        },
    });
}

export {setTableContext, pushComponentUpdate, pushNewComponent, pushRemoveComponent, joinTable};