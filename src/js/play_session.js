import {el, mount, setAttr, setStyle} from "redom";
import {Component, Table} from "./table";
import {
    joinTable,
    pushCursorMovement,
    pushNewComponent,
    pushNewKitAndComponents,
    pushRemoveComponent,
    pushSyncWithMe,
    setTableContext,
} from "./sync_table.js";
import {Menu, MenuConnector} from "./menu.js";
import {CraftBox, CraftBoxConnector, feats as featsForCraftBox} from "./craft_box.js";
import {dev_inspector} from "./dev_inspector.js"
import interact from 'interactjs';

import '../style/game.css';
import {basic, feats as basicFeats} from "./feat";
import "./feats/overlaid_controls";

const feats = basicFeats.concat(featsForCraftBox);
function baseUrl() {
    return location.protocol + "//" + location.hostname + (location.port ? ":" + location.port : "") + "/";
}

const syncTableConnector = {
    initializeTable(tableData) {
        console.log("initializeTable");
        console.log("tableData: ", tableData);
        const players = tableData.players;
        console.log("players: ", players);
        if (Object.keys(players).length === 0) {
            joinTable("host", true);  // the first player is automatically becomes host
        } else if (getPlayerName() !== "nobody") {
            joinTable(getPlayerName(), isPlayerHost());
        } else {
            setPlayerIsObserver();
        }

        table.update(tableData);
        menu.update(tableData);
    },

    updateSingleComponent(componentId, diff) {
        const tableData = table.data;
        if (tableData.components[componentId].lastUpdated) {
            if (tableData.components[componentId].lastUpdated.from === diff.lastUpdated.from
                && tableData.components[componentId].lastUpdated.epoch > diff.lastUpdated.epoch) {
                dev_inspector.tracePoint('aborted sync update single component');
                // already recieved newer update for this component; ignore the diff
                return;
            }
        }
        Object.assign(tableData.components[componentId], diff);
        table.update(tableData);
        menu.update(tableData);
        dev_inspector.tracePoint('finished sync update single component');
    },

    updateManyComponents(diffOfComponents, componentIdsToRemove) {
        const tableData = table.data;
        for (const component_diff of diffOfComponents) {
            for (const componentId in component_diff) {
                if (!component_diff.hasOwnProperty(componentId)) {
                    continue;
                }
                applyDiffToComponentData(componentId, component_diff[componentId]);
            }
        }
        applyRemoveComponents(componentIdsToRemove);
        table.update(tableData);
        menu.update(tableData);
        dev_inspector.tracePoint('finished sync update many components');

        function applyDiffToComponentData(componentId, diff) {
            if (!tableData.components.hasOwnProperty(componentId)) {
                // component is already removed from table probably
                return;
            }
            Object.assign(tableData.components[componentId], diff);
        }

        function applyRemoveComponents(componentIdsToRemove) {
            for (const componentId of componentIdsToRemove) {
                if (!tableData.components.hasOwnProperty(componentId)) {
                    continue;
                }
                // table.update() will remove components which are absent in tableData
                delete tableData.components[componentId];
            }
        }
    },

    addComponent(componentData) {
        syncTableConnector.addManyComponents([componentData])
    },

    addManyComponents(componentDataObj) {
        for (const componentId in componentDataObj) {
            if (!componentDataObj.hasOwnProperty(componentId)) {
                continue;
            }
            const componentData = componentDataObj[componentId];
            if (!table.data.components[componentData.componentId]) {
                table.data.components[componentData.componentId] = componentData;
            }
            if (!table.componentsOnTable[componentData.componentId]) {
                table.componentsOnTable[componentData.componentId] = new Component(table, componentData, table.feats, table.overlay);
                mount(table.list_el, table.componentsOnTable[componentData.componentId].el);
                table.componentsOnTable[componentData.componentId].update(componentData, componentData.componentId);
            }
        }
        table.update(table.data);
        menu.update(table.data);
    },

    addKitAndComponents(kitData, newComponents) {
        for (const existKit of table.data.kits) {
            if (existKit.kitId === kitData.kitId) {
                return;
            }
        }
        table.data.kits.push(kitData);
        syncTableConnector.addManyComponents(newComponents);
    },

    updateWholeTable(data) {
        table.update(data);
        menu.update(data);
    },

    updatePlayer(playerData) {
        if (playerData.name) {
            setPlayerIsJoined();
            setPlayerName(playerData.name);
        }
    },

    showOthersMouseMovement(playerName, mouseMovement) {
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
        const left = mouseMovement.mouseOnTableX + ICON_OFFSET_X;
        const top = mouseMovement.mouseOnTableY + ICON_OFFSET_Y;
        const className = mouseMovement.mouseButtons === 0 ? "" : "buttons_down";
        setAttr(e, { className: "others_mouse_cursor " + className });
        setStyle(e, { left: left + "px", top: top + "px", zIndex: 999999999 });
    },
};

const otherPlayersMouse = {};

function generateComponentId() {
    return 'xxxxxxxxxxxx'.replace(/[x]/g, function (/*c*/) {
        return (Math.random() * 16 | 0).toString(16);
    });
}

function createComponentWithinKit(kitId, componentData) {
    const newComponentData = Object.assign({}, componentData);
    newComponentData.kitId = kitId;
    const componentId = generateComponentId();
    newComponentData.componentId = componentId;

    return newComponentData;
}


async function addNewKit(kitData) {
    const kitName = kitData.kit.name;
    const kitId = 'xxxxxxxxxxxx'.replace(/[x]/g, function (/*c*/) {
        return (Math.random() * 16 | 0).toString(16);
    });

    const baseZIndex = table.getNextZIndex();
    const newComponents = {};
    const usedComponentsData = await (await fetch(encodeURI(baseUrl() + "components?kit_name=" + kitName))).json();
    const layouter = kitLayouter(kitData.kit.positionOfKitContents);
    const componentDataMap = {};
    for (const cmp of usedComponentsData) {
        componentDataMap[cmp['component']['name']] = cmp;
    }

    layouter();

    pushNewKitAndComponents({
        kit: { name: kitName, kitId: kitId },
    }, newComponents);
    for (const componentId in newComponents) {
        const newComponentData = newComponents[componentId];
        table.addComponent(newComponentData);
    }
    return kitId;

    function createComponent(name) {
        const newComponentData = createComponentWithinKit(kitId, componentDataMap[name].component);
        newComponents[newComponentData.componentId] = newComponentData;
        return newComponentData;
    }

    function createContentsOfBox(boxData, contentNames) {
        boxData.componentsInBox = {};
        for (const name of contentNames) {
            const boxOrComponentData = createComponent(name);
            const componentId = boxOrComponentData.componentId;

            boxData.componentsInBox[componentId] = true;
        }

        switch (boxData.positionOfBoxContents) {
            case "random":
                for (const contentId in boxData.componentsInBox) {
                    const contentData = newComponents[contentId];
                    layoutRandomly(contentData, boxData);
                }
                break;
            default:
                for (const contentId in boxData.componentsInBox) {
                    const contentData = newComponents[contentId];
                    layoutRelativelyAsDefined(contentData, boxData);
                }
        }
    }

    function layoutRandomly(newComponentData, baseRect) {
        newComponentData.left = Math.floor(parseFloat(baseRect.left) +
            (Math.random() * (parseFloat(baseRect.width) - parseFloat(newComponentData.width))));
        newComponentData.top = Math.floor(parseFloat(baseRect.top) +
            (Math.random() * (parseFloat(baseRect.height) - parseFloat(newComponentData.height))));
        if (newComponentData.zIndex) {
            newComponentData.zIndex += baseZIndex;
        } else {
            newComponentData.zIndex = baseZIndex;
        }

    }

    function layoutRelativelyAsDefined(newComponentData, baseRect) {
        newComponentData.left = parseFloat(newComponentData.left) + parseFloat(baseRect.left);
        newComponentData.top = parseFloat(newComponentData.top) + parseFloat(baseRect.top);
        if (newComponentData.zIndex) {
            newComponentData.zIndex += baseZIndex;
        } else {
            newComponentData.zIndex = baseZIndex;
        }
        if (newComponentData.onAdd) {
            Function('"use strict"; return ' + newComponentData.onAdd)()(newComponentData);
        }
    }

    function layoutInHandArea(componentsInHandArea, handAreaData) {
        const horizontalStart = parseFloat(handAreaData.left) + 1;
        const width = parseFloat(handAreaData.width) - 2;
        const verticalStart = parseFloat(handAreaData.top) + 1;
        const height = parseFloat(handAreaData.height) - 2;

        const count = componentsInHandArea.length;
        componentsInHandArea.sort((a, b) => b.zIndex - a.zIndex);
        let index = 0;
        for (const cmp of componentsInHandArea) {
            cmp.left = horizontalStart + ((width - parseFloat(cmp.width)) / count) * index;
            cmp.top = verticalStart + ((height - parseFloat(cmp.height)) / count) * index;
            index += 1;
        }

    }

    function kitLayouter(name) {
        switch (name) {
            case "on all hand areas":
                return function () {
                    const handAreasData = table.getAllHandAreas();
                    if (handAreasData.length > 0) {
                        for (const handAreaData of handAreasData) {
                            const componentsInHandArea = [];
                            for (const name in kitData.kit.boxAndComponents) {
                                if (!kitData.kit.boxAndComponents.hasOwnProperty(name)) {
                                    continue;
                                }
                                const boxOrComponentData = createComponent(name);
                                if (boxOrComponentData.zIndex) {
                                    boxOrComponentData.zIndex += baseZIndex;
                                } else {
                                    boxOrComponentData.zIndex = baseZIndex;
                                }
                                componentsInHandArea.push(boxOrComponentData);
                            }
                            layoutInHandArea(componentsInHandArea, handAreaData);

                            const contents = kitData.kit.boxAndComponents[name];
                            if (contents) {
                                createContentsOfBox(boxOrComponentData, contents);
                            }
                        }
                    } else {
                        const emptySpaceRect = table.findEmptySpace(kitData.kit.width, kitData.kit.height);

                        for (const name in kitData.kit.boxAndComponents) {
                            if (!kitData.kit.boxAndComponents.hasOwnProperty(name)) {
                                continue;
                            }
                            const boxOrComponentData = createComponent(name);
                            layoutRelativelyAsDefined(boxOrComponentData, emptySpaceRect);

                            const contents = kitData.kit.boxAndComponents[name];
                            if (contents) {
                                createContentsOfBox(boxOrComponentData, contents);
                            }
                        }
                    }
                };
            case "random":
                return function () {
                    const emptySpaceRect = table.findEmptySpace(kitData.kit.width, kitData.kit.height);

                    for (const name in kitData.kit.boxAndComponents) {
                        if (!kitData.kit.boxAndComponents.hasOwnProperty(name)) {
                            continue;
                        }
                        const boxOrComponentData = createComponent(name);
                        layoutRandomly(boxOrComponentData, emptySpaceRect);

                        const contents = kitData.kit.boxAndComponents[name];
                        if (contents) {
                            createContentsOfBox(boxOrComponentData, contents);
                        }
                    }
                };

            default:
                return function () {
                    const emptySpaceRect = table.findEmptySpace(kitData.kit.width, kitData.kit.height);

                    for (const name in kitData.kit.boxAndComponents) {
                        if (!kitData.kit.boxAndComponents.hasOwnProperty(name)) {
                            continue;
                        }
                        const boxOrComponentData = createComponent(name);
                        layoutRelativelyAsDefined(boxOrComponentData, emptySpaceRect);

                        const contents = kitData.kit.boxAndComponents[name];
                        if (contents) {
                            createContentsOfBox(boxOrComponentData, contents);
                        }
                    }
                };
        }
    }
}

function removeKit(kitId) {
    const after = {};
    for (const componentId in table.data.components) {
        const cmp = table.data.components[componentId];
        if (cmp.kitId === kitId) {
            table.removeComponent(componentId);
        } else {
            after[componentId] = cmp;
        }
    }
    table.data.components = after;
    table.data.kits.splice(table.data.kits.findIndex((e) => e.kitId === kitId), 1);
    pushSyncWithMe(table.data);
}

function placeNewComponent(newComponent, baseZIndex) {
    const rect = table.findEmptySpace(parseInt(newComponent.width), parseInt(newComponent.height));
    newComponent.left = rect.left + "px";
    newComponent.top = rect.top + "px";
    if (newComponent.zIndex) {
        if (baseZIndex) {
            newComponent.zIndex += baseZIndex;
        }
    } else {
        newComponent.zIndex = table.getNextZIndex();
    }

    if (newComponent.onAdd) {
        Function('"use strict"; return ' + newComponent.onAdd)()(newComponent);
    }
}

function addNewComponent(newComponentData) {
    newComponentData.componentId = generateComponentId();
    placeNewComponent(newComponentData);
    table.addComponent(newComponentData);
    pushNewComponent(newComponentData);
    return false;
}

function addNewCraftBoxComponent(newComponentData, kitId) {
    newComponentData.componentId = generateComponentId();
    newComponentData.kitId = kitId;
    placeNewComponent(newComponentData);
    table.addComponent(newComponentData);
    pushNewComponent(newComponentData);
    return false;
}

function removeHandArea() {
    for (const componentId in table.data.components) {
        const cmp = table.data.components[componentId];
        if (cmp.handArea && cmp.owner === getPlayerName()) {
            table.removeComponent(componentId);
            pushRemoveComponent(componentId);
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

function isPlayerObserver() {
    const value = sessionStorage.getItem(SESSION_STORAGE_KEY.status);
    return value == null || value === "observer";
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
document.title = tablename + " on asobann";
const container = el("div.container");
mount(document.body, container);
const table = new Table({
    getPlayerName,
    isPlayerObserver,
    availableFeats: feats});
table.el.addEventListener('tableContentsChanged', () => {
    menu.update(table.data);
});
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
            let left = table.el.style.left === "" ? 0 : parseFloat(table.el.style.left);
            left += event.dx;
            let top = table.el.style.top === "" ? 0 : parseFloat(table.el.style.top);
            top += event.dy;
            table.el.style.left = left + "px";
            table.el.style.top = top + "px";

            tableContainer.style.backgroundPositionX = left + "px";
            tableContainer.style.backgroundPositionY = top + "px";
        },
    },
    ignoreFrom: 'textarea,button',
});


function isTherePlayersHandArea(playerName) {
    if (table.data.components) {
        for (const cmpId in table.data.components) {
            const cmp = table.data.components[cmpId];
            if (cmp.handArea && cmp.owner === playerName) {
                return true;
            }
        }
    }
    return false;
}

setTableContext(tablename, syncTableConnector);

const craftBox = new CraftBox(
    tablename,
    new CraftBoxConnector({
        addNewCraftBoxComponent: addNewCraftBoxComponent,
        pushNewKitAndComponents: pushNewKitAndComponents,
        isKitOnTable: (kitName) => { return table.isKitOnTable(kitName); },
        getKitIdByName: (kitName) => { return table.getKitIdByName(kitName); },
        removeKit: removeKit,
    })
);

const menu = new Menu(
    new MenuConnector({
        tablename: tablename,
        getTableData: () => {
            return table.data;
        },
        fireMenuUpdate: () => {
            menu.update(table.data);
        },
        getPlayerName: getPlayerName,
        addNewKit: addNewKit,
        removeKit: removeKit,
        addNewComponent: addNewComponent,
        removeHandArea: removeHandArea,
        isPlayerObserver: isPlayerObserver,
        isTherePlayersHandArea: isTherePlayersHandArea,
        openCraftBox: () => {
            craftBox.open();
            menu.update({});
        },
        closeCraftBox: () => {
            craftBox.close();
            menu.update({});
        },
        isCraftBoxOpen: () => { return craftBox.isOpen(); },
    }));
mount(container, menu.el);

tableContainer.addEventListener("mousemove", (event) => {
    if (isPlayerObserver()) {
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