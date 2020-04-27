const socket = io();
console.log(socket);

const context = {
    client_connection_id: 'xxxxxxxxxxxx'.replace(/[x]/g, function(c) {
        return (Math.random() * 16 | 0).toString(16);
    }),
};

function setTableContext(tablename, getPlayer, connector) {
    context.tablename = tablename;
    context.getPlayer = getPlayer;
    context.initializeTable = connector.initializeTable;
    context.update_single_component = connector.update_single_component;
    context.update_whole_table = connector.update_whole_table;
}

socket.on("initialize table", (msg) => {
    context.initializeTable(msg);
});

socket.on('connect', () => {
    socket.emit('join', { tablename: context.tablename, player: context.getPlayer() });
});

socket.on("update table", (msg) => {
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


function pushUpdate(table, index, diff) {
    const oldData = table.data;
    Object.assign(oldData[index], diff);
    table.update(oldData);
    socket.emit("update table", {
        tablename: context.tablename,
        originator: context.client_connection_id,
        index: index,
        diff: diff,
    })
}

function pushNewComponent(data) {
    socket.emit("add component", {
        tablename: context.tablename,
        originator: context.client_connection_id,
        data: data,
    })
}

export {setTableContext, pushUpdate, pushNewComponent};