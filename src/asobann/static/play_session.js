import {el, mount, unmount, list, setStyle, setAttr} from "./redom.es.js";
import {draggability, flippability, resizability} from "./feat.js";
import {setTableContext, pushComponentUpdate, pushNewComponent, joinTable} from "./sync_table.js";


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
            this.propagate({ zIndex: this.zIndex });
        });
    }

    update(data, index, allData, context) {
        this.index = index;
        if (data == null) {
            // this component is removed
            setStyle({ display: "none" });
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

    propagate(diff) {
        pushComponentUpdate(table, this.index, diff);
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

const sync_table_connector = {
    initializeTable: function (tableData) {
        console.log("initializeTable");
        console.log("tableData: ", tableData);
        const players = tableData.players;
        console.log("players: ", players);
        if (Object.keys(players) == 0) {
            joinTable("host", true);  // the first player is automatically becomes host
        }

        table.update(tableData.components);
    },

    update_single_component: function (index, diff) {
        const oldData = table.data;
        Object.assign(oldData[index], diff);
        table.update(oldData);
    },

    update_whole_table: function (data) {
        table.update(data.components);
    },
};


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
    mount(menu, importEl);

    function hideImport() {
        unmount(menu, importEl);
    }
}

function addHandArea() {
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
    return false;
}

const SESSION_STORAGE_KEY = {
    playerName: "asobann: player_name",
};

function getPlayer() {
    if (sessionStorage.getItem(SESSION_STORAGE_KEY.playerName)) {
        return sessionStorage.getItem(SESSION_STORAGE_KEY.playerName);
    }
    return "nobody";
}

function setPlayer(player) {
    sessionStorage.setItem(SESSION_STORAGE_KEY.playerName, player);
    menu.update({ player: player });
}


const tablename = location.pathname.split("/")[2];
const container = el("div.container");
mount(document.body, container);
const table = new Table();
mount(container, el("div.table_container", [table.el]));

setTableContext(tablename, getPlayer, setPlayer, sync_table_connector);

class Menu {
    constructor(props) {
        this.playerNameEl = el("span", getPlayer());
        this.el = el("div.menu",
            [
                el("div", ["you are ", this.playerNameEl]),
                "Menu",
                el("div.menuitem#add_hand_area",
                    el("a", { href: "/", onclick: addHandArea }, "Add Hand Area")),
                el("div.menuitem",
                    el("a", { href: "/export?tablename=" + tablename }, "Export Table")),
                el("div.menuitem",
                    el("a", { href: "#", onclick: showImport }, "Import Table")),
            ],
        );
    }

    update(data) {
        this.playerNameEl.innerText = data.player;
    }
}

const menu = new Menu();
mount(container, menu.el);

let maxZIndex = 0;