const socket = io();
console.log(socket);

const table = {};

function setTableContext(tablename, getPlayer, initializeTable, myself, _table, update_single_component) {
    table.tablename = tablename;
    table.getPlayer = getPlayer;
    table.initializeTable = initializeTable;
    table.myself = myself;
    table.table = _table;
    table.update_single_component = update_single_component;
}

socket.on("initialize table", (msg) => {
    table.initializeTable(msg);
});

socket.on('connect', () => {
    socket.emit('join', { tablename: table.tablename, player: table.getPlayer() });
});

socket.on("update table", (msg) => {
    if (msg.tablename !== table.tablename) {
        return;
    }
    if (msg.originator === table.myself) {
        return;
    }
    table.update_single_component(msg.index, msg.diff);
});

export {socket, setTableContext};