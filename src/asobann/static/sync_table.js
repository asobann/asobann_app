const socket = io();
console.log(socket);

const context = {};

function setTableContext(tablename, getPlayer, initializeTable, myself, update_single_component, update_whole_table) {
    context.tablename = tablename;
    context.getPlayer = getPlayer;
    context.initializeTable = initializeTable;
    context.myself = myself;
    context.update_single_component = update_single_component;
    context.update_whole_table = update_whole_table;
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
    if (msg.originator === context.myself) {
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


export {socket, setTableContext};