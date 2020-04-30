import {el, mount, unmount, list, setStyle, setAttr} from "./redom.es.js";
import {draggability, flippability, resizability} from "./feat.js";
import {setTableContext, pushComponentUpdate, pushNewComponent, pushRemoveComponent, joinTable} from "./sync_table.js";


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
        this.data = {};


    }

    update(data) {
        draggability.setContext(getPlayerName(), data);
        flippability.setContext(getPlayerName(), data);
        resizability.setContext(getPlayerName(), data);

        this.data = data;
        this.list.update(this.data.components);
    }
}

const sync_table_connector = {
    initializeTable: function (tableData) {
        console.log("initializeTable");
        console.log("tableData: ", tableData);
        const players = tableData.players;
        console.log("players: ", players);
        if (Object.keys(players).length === 0) {
            joinTable("host", true);  // the first player is automatically becomes host
        } else {
            setPlayerIsObserver();
        }

        table.update(tableData);
        menu.update({})
    },

    update_single_component: function (index, diff) {
        const oldData = table.data;
        Object.assign(oldData.components[index], diff);
        table.update(oldData);
        menu.update({});
    },

    update_whole_table: function (data) {
        table.update(data);
        menu.update({});
    },

    updatePlayer: function (playerData) {
        if (playerData.name) {
            setPlayerName(playerData.name);
        }
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
        name: getPlayerName() + "'s hand",
        handArea: true,
        owner: getPlayerName(),
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

function removeHandArea() {
    for (let i = 0; i < table.data.components.length; i++) {
        const cmp = table.data.components[i];
        if (cmp.handArea && cmp.owner === getPlayerName()) {
            pushRemoveComponent(i);
            return false;
        }
    }
    return false;
}

function getPlayerName() {
    if (sessionStorage.getItem(SESSION_STORAGE_KEY.playerName)) {
        return sessionStorage.getItem(SESSION_STORAGE_KEY.playerName);
    }
    return "nobody";
}

function setPlayerName(playerName) {
    sessionStorage.setItem(SESSION_STORAGE_KEY.playerName, playerName);
    menu.update({ playerName: playerName });
}

function isPlayerHost() {
    if (sessionStorage.getItem(SESSION_STORAGE_KEY.isHost)) {
        return sessionStorage.getItem(SESSION_STORAGE_KEY.isHost) == "true";
    }
    return false;
}

function setPlayerIsHost() {
    sessionStorage.setItem(SESSION_STORAGE_KEY.isHost, "true");
    menu.update({ isHost: true });
}

function isPlayerObserver() {
    if (sessionStorage.getItem(SESSION_STORAGE_KEY.status)) {
        return sessionStorage.getItem(SESSION_STORAGE_KEY.status) == "observer";
    }
    return false;
}

function setPlayerIsObserver() {
    sessionStorage.setItem(SESSION_STORAGE_KEY.status, "observer");
    menu.update({});
}


const tablename = location.pathname.split("/")[2];
const container = el("div.container");
mount(document.body, container);
const table = new Table();
mount(container, el("div.table_container", [table.el]));

const SESSION_STORAGE_KEY = {
    playerName: "asobann: " + tablename + ": playerName",
    isHost: "asobann: " + tablename + ": isHost",
    status: "asobann: " + tablename + ": status",
};


interact("div.table_container").draggable({
    listeners: {
        move(event) {
            let top = table.el.style.top === "" ? 0 : parseFloat(table.el.style.top);
            top += event.dy;
            let left = table.el.style.left === "" ? 0 : parseFloat(table.el.style.left);
            left += event.dx;
            table.el.style.top = top + "px";
            table.el.style.left = left + "px";
        },
    },
});

setTableContext(tablename, sync_table_connector);

class Menu {
    constructor(props) {
        this.playerStatusEl = el("span", getPlayerName());

        this.el = el("div.menu",
            [
                el("div.title", "asobann 遊盤"),
                el("div", ["you are ", this.playerStatusEl]),
                this.mmm = "Menu",
                this.addHandAreaItem = el("div.menuitem#add_hand_area",
                    el("a", { href: "", onclick: addHandArea }, "Add Hand Area")),
                this.removeHandAreaItem = el("div.menuitem#remove_hand_area",
                    el("a", { href: "", onclick: removeHandArea }, "Remove Hand Area")),
                el("div.menuitem", [
                    "Share URL for invitation",
                    el("input#invitation_url", {
                        value: location.href,
                        readonly: true,
                        onclick: (e) => {
                            e.target.select();
                        }
                    }),
                    el("a#copy_invitation_url", {
                        href: "", onclick: () => {
                            document.querySelector('#invitation_url').select();
                            document.execCommand('copy');
                            return false;
                        }
                    }, "copy"),
                ]),
                el("div.menuitem",
                    el("a", { href: "/export?tablename=" + tablename }, "Export Table")),
                el("div.menuitem",
                    el("a", { href: "", onclick: showImport }, "Import Table")),
            ],
        );
    }

    update(data) {
        if (isPlayerObserver()) {
            this.playerStatusEl.innerText = "observing";
        } else if (data.playerName) {
            this.playerStatusEl.innerText = data.playerName;
        }

        let found = false;
        if (table.data.components) {
            for (const cmp of table.data.components) {
                if (cmp.handArea && cmp.owner === getPlayerName()) {
                    found = true;
                    break;
                }
            }
        }

        if (found) {
            setStyle(this.addHandAreaItem, { display: 'none' });
            setStyle(this.removeHandAreaItem, { display: null });
        } else {
            setStyle(this.addHandAreaItem, { display: null });
            setStyle(this.removeHandAreaItem, { display: 'none' });
        }

    }
}

const menu = new Menu();
mount(container, menu.el);

let maxZIndex = 0;