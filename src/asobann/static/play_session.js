import {el, mount, unmount, list, setStyle, setAttr} from "./redom.es.js";
import {setFeatsContext, draggability, flippability, resizability} from "./feat.js";
import {
    setTableContext,
    pushComponentUpdate,
    pushNewComponent,
    pushRemoveComponent,
    joinTable,
    pushCursorMovement
} from "./sync_table.js";
import {Menu} from "./menu.js";


class Component {
    constructor() {
        this.el = el(".component");
        this.image = null;

        draggability.add(this);
        flippability.add(this);
        resizability.add(this);

        this.el.addEventListener("mousedown", (ev) => {
            if (isPlayerObserver()) {
                return;
            }
            this.zIndex = nextZIndex;
            setStyle(this.el, { zIndex: this.zIndex });
            nextZIndex += 1;
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
        }

        if (this.textEl == null) {
            this.textEl = el("span");
            mount(this.el, this.textEl);
        }
        if (data.text) {
            this.textEl.innerText = data.text;
        }
        if (data.textColor) {
            setStyle(this.textEl, { color: data.textColor });
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
            if (nextZIndex <= this.zIndex) {
                nextZIndex = this.zIndex + 1;
            }
        } else {
            this.zIndex = nextZIndex;
            nextZIndex += 1;
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
        pushComponentUpdate(table, this.index, diff, false);
    }

    propagate_volatile(diff) {
        pushComponentUpdate(table, this.index, diff, true);
    }
}

class Table {
    constructor() {
        console.log("new Table");
        this.el = el("div.table", { style: { top: '0px', left: '0px' } },
            this.list_el = el("div.table_list")
        );
        this.list = list(this.list_el, Component);
        this.data = {};
    }

    update(data) {
        setFeatsContext(getPlayerName(), isPlayerObserver(), data);

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
        } else if (getPlayerName() != "nobody") {
            joinTable(getPlayerName(), isPlayerHost());
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
            setPlayerIsJoined();
            setPlayerName(playerData.name);
        }
    },

    showOthersMouseMovement: function (playerName, mouseMovement) {
        const ICON_OFFSET_X = -(32 / 2);  // see "div.others_mouse_cursor .icon " in game.css
        const ICON_OFFSET_Y = -(32 / 2);
        if (playerName === getPlayerName()) {
            return;
        }
        if (!otherPlayersMouse[playerName]) {
            const e = el("div.others_mouse_cursor",
                [
                    el("div.icon"),
                    el("span", playerName),
                ]);
            mount(table.el, e);
            otherPlayersMouse[playerName] = e;
        }
        const e = otherPlayersMouse[playerName];
        const top = mouseMovement.mouseOnTableY + ICON_OFFSET_Y;
        const left = mouseMovement.mouseOnTableX + ICON_OFFSET_X;
        const className = mouseMovement.mouseButtons === 0 ? "" : "buttons_down";
        setAttr(e, { className: "others_mouse_cursor " + className});
        setStyle(e, { top: top + "px", left: left + "px", zIndex: nextZIndex });
    }
};

const otherPlayersMouse = {};

function addHandArea() {
    const rect = {
        top: 64,
        left: 64,
        width: 320,
        height: 64,
    };
    for (let i = 0; i < 10; i++) {
        let collision = false;
        rect.bottom = rect.top + rect.height;
        rect.right = rect.left + rect.width;
        for (const target of table.data.components) {
            const targetLeft = parseFloat(target.left);
            const targetTop = parseFloat(target.top);
            const targetRight = targetLeft + parseFloat(target.width);
            const targetBottom = targetTop + parseFloat(target.height);
            if (rect.left <= targetRight &&
                targetLeft <= rect.right &&
                rect.top <= targetBottom &&
                targetTop <= rect.bottom) {
                collision = true;
                break;
            }
        }
        if (!collision) {
            break;
        }
        rect.top += 100;
    }
    const newComponent = {
        name: getPlayerName() + "'s hand",
        text: getPlayerName() + "'s hand",
        handArea: true,
        owner: getPlayerName(),
        top: rect.top + "px",
        left: rect.left + "px",
        width: rect.width + "px",
        height: rect.height + "px",
        draggable: true,
        flippable: false,
        resizable: true,
        ownable: false,
        zIndex: nextZIndex,
    };
    nextZIndex += 1;
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
    return sessionStorage.getItem(SESSION_STORAGE_KEY.isHost) === "true";
}

function setPlayerIsHost() {
    sessionStorage.setItem(SESSION_STORAGE_KEY.isHost, "true");
    menu.update({ isHost: true });
}

function isPlayerObserver() {
    return sessionStorage.getItem(SESSION_STORAGE_KEY.status) === "observer";
}

function setPlayerIsObserver() {
    sessionStorage.setItem(SESSION_STORAGE_KEY.status, "observer");
    menu.update({});
}

function setPlayerIsJoined() {
    sessionStorage.setItem(SESSION_STORAGE_KEY.status, "joined");
    menu.update({});
}

const tablename = location.pathname.split("/")[2];
const container = el("div.container");
mount(document.body, container);
const table = new Table();
const tableContainer = el("div.table_container", [table.el]);
mount(container, tableContainer);

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

            tableContainer.style.backgroundPositionY = top + "px";
            tableContainer.style.backgroundPositionX = left + "px";
        },
    },
});

function isTherePlayersHandArea(playerName) {
    if (table.data.components) {
        for (const cmp of table.data.components) {
            if (cmp.handArea && cmp.owner === playerName) {
                return true;
            }
        }
    }
    return false;
}

setTableContext(tablename, sync_table_connector);

const menuConnector = {
    tablename: tablename,
    getPlayerName: getPlayerName,
    addHandArea: addHandArea,
    removeHandArea: removeHandArea,
    isPlayerObserver: isPlayerObserver,
    isTherePlayersHandArea: isTherePlayersHandArea,
};

const menu = new Menu(menuConnector);
mount(container, menu.el);

let nextZIndex = 1;

tableContainer.addEventListener("mousemove", (event) => {
    if(isPlayerObserver()) {
        return;
    }
    const r = tableContainer.getBoundingClientRect();
    const mouseOnTableX = event.clientX - r.left - parseFloat(table.el.style.left);
    const mouseOnTableY = event.clientY - r.top - parseFloat(table.el.style.top);
    pushCursorMovement(getPlayerName(), {
        mouseOnTableX: mouseOnTableX,
        mouseOnTableY: mouseOnTableY,
        mouseButtons: event.buttons,
    })
});