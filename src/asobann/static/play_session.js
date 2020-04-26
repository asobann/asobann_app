import {el, mount, unmount, list, setStyle, setAttr} from "./redom.es.js";
import {draggability, flippability, resizability} from "./feat.js";

const socket = io();
console.log(socket);
socket.on('connect', () => {
    socket.emit('join', { tablename: tablename, player: getPlayer() });
});
socket.on("initialize table", (msg) => {
    initializeTable(msg);
});
socket.on("update table", (msg) => {
    if (msg.tablename !== tablename) {
        return;
    }
    if (msg.originator === myself) {
        return;
    }
    const oldData = table.data;
    Object.assign(oldData[msg.index], msg.diff);
    table.update(oldData);
});
socket.on("refresh table", (msg) => {
    console.log("event received: refresh table");
    if (msg.tablename !== tablename) {
        return;
    }
    table.update(msg.table);
});


class Component {
    constructor() {
        this.el = el(".component");
        this.image = null;

        draggability.add(this);
        flippability.add(this);
        resizability.add(this);

        this.el.addEventListener("mousedown", (ev) => {
            maxZIndex += 1;
            this.zIndex = maxZIndex;
            setStyle(this.el, { zIndex: maxZIndex });
            this.pushUpdate({ zIndex: this.zIndex });
        });
    }

    update(data, index, allData, context) {
        this.index = index;
        if(data == null) {
            // this component is removed
            setStyle({display: "none"});
            return;
        }
        if (data.showImage) {
            if (this.image == null) {
                this.image = el("img", { draggable: false });
                this.image.ondragstart = () => {
                    return false;
                };
                mount(this.el, this.image);
            }
        } else {
            this.el.innerText = data.name;
        }

        if (draggability.enabled(this, data)) {
            draggability.update(this, data);
        }
        if (flippability.enabled(this, data)) {
            flippability.update(this, data);
        }
        if (resizability.enabled(this, data)) {
            resizability.update(this, data);
        }
        if (data.zIndex) {
            this.zIndex = data.zIndex;
            if (maxZIndex < this.zIndex) {
                maxZIndex = this.zIndex;
            }
        } else {
            maxZIndex += 1;
            this.zIndex = maxZIndex;
        }

        setStyle(this.el, {
            top: parseFloat(data.top) + "px",
            left: parseFloat(data.left) + "px",
            width: parseFloat(data.width) + "px",
            height: parseFloat(data.height) + "px",
            backgroundColor: data.color,
            zIndex: this.zIndex,
        });
    }

    pushUpdate(diff) {
        const oldData = table.data;
        Object.assign(oldData[this.index], diff);
        table.update(oldData);
        socket.emit("update table", {
            tablename: tablename,
            originator: myself,
            index: this.index,
            diff: diff,
        })
    }
}

class Table {
    constructor() {
        this.el = el("div.table");
        this.list = list(this.el, Component);
        this.data = [];

        interact("div.table").draggable({
            listeners: {
                move(event) {
                    let top = event.target.style.top === "" ? 0 : parseFloat(event.target.style.top);
                    top += event.dy;
                    let left = event.target.style.left === "" ? 0 : parseFloat(event.target.style.left);
                    left += event.dx;
                    event.target.style.top = top + "px";
                    event.target.style.left = left + "px";
                },
            },
        });
    }

    update(data) {
        draggability.setContext(getPlayer(), data);
        flippability.setContext(getPlayer(), data);
        resizability.setContext(getPlayer(), data);

        this.data = data;
        this.list.update(this.data);
    }
}


function showImport(ev) {
    const importEl = el("div",
        el("form", { action: "/import", method: "POST", enctype: "multipart/form-data" },
            [
                el("input", { type: "hidden", value: tablename, name: "tablename" }),
                el("input", { type: "file", name: "data" }),
                el("input", { type: "submit" }),
                el("button", { onclick: hideImport }, "Cancel"),
            ]
        )
    );
    mount(document.body, importEl);

    function hideImport() {
        unmount(document.body, importEl);
    }
}

function initializeTable(tableData) {
    console.log("initializeTable");
    console.log("components: ", tableData);
    let found = false;
    for (const cmp of tableData) {
        if (cmp.handArea && cmp.owner === getPlayer()) {
            found = true;
            break;
        }
    }
    if (!found) {
        const newComponent = {
            name: getPlayer() + "'s hand",
            handArea: true,
            owner: getPlayer(),
            top: "64px",
            left: "64px",
            width: "320px",
            height: "64px",
            draggable: true,
            flippable: false,
            resizable: true,
            ownable: false,
            zIndex: maxZIndex + 1,
        };
        pushNewComponent(newComponent);
        return;  // let refresh table event to add actual component
    }
    table.update(tableData);
}


function getPlayer() {
    for (const c of document.cookie.split(';')) {
        const ar = c.split("=");
        if (ar[0] === 'player') {
            return ar[1];
        }
    }
    return "nobody";
}


function pushNewComponent(data) {
    socket.emit("add component", {
        tablename: tablename,
        originator: myself,
        data: data,
    })
}



const tablename = location.pathname.split("/")[2];
const myself = Math.floor(Math.random() * 1000000);
const container = el("div.container");
mount(document.body, container);
const table = new Table();
mount(container, el("div.table_container", [ table.el ]));


const menu = el("div.menu", { style: { textAlign: "right" } },
    [
        el("div", "you are " + getPlayer()),
        "Menu",
        el("br"),
        el("a", { href: "/export?tablename=" + tablename }, "Export Table"),
        el("br"),
        el("a", { href: "#", onclick: showImport }, "Import Table"),
        el("br"),
        el("a", { href: "/" }, "Abandon Table"),
    ],
);
mount(container, menu);

let maxZIndex = 0;