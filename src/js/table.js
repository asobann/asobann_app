import {el, mount, unmount, setStyle, setAttr} from "redom";
import {setFeatsContext, feats, event} from "./feat.js";
import {dev_inspector} from "./dev_inspector.js"
import {consolidatePropagation, pushComponentUpdate} from "./sync_table";

class Component {
    constructor(table, data) {
        this.table = table;
        this.el = el(".component");
        for (const ability of feats) {
            ability.install(this, data);
        }
    }

    update(data, componentId) {
        this.receiveData(data, componentId);
        this.updateView(data);
    }

    receiveData(data, componentId) {
        this.componentId = componentId;
        for (const ability of feats) {
            if (ability.isEnabled(this, data)) {
                if (ability.hasOwnProperty('receiveData')) {
                    ability.receiveData(this, data);
                }
            }
        }
    }

    updateView(data) {
        for (const ability of feats) {
            if (ability.isEnabled(this, data)) {
                if (ability.hasOwnProperty('updateView')) {
                    ability.updateView(this, data);
                } else {
                    ability.onComponentUpdate(this, data);
                }
            }
        }
    }

    disappear() {
        for (const ability of feats) {
            ability.uninstall(this);
        }
    }

    propagate(diff) {
        dev_inspector.tracePoint('propagate');
        pushComponentUpdate(this.table, this.componentId, diff, false);
    }

    propagate_volatile(diff) {
        pushComponentUpdate(this.table, this.componentId, diff, true);
    }
}

class Table {
    constructor({getPlayerName, isPlayerObserver}) {
        this.getPlayerName = getPlayerName;
        this.isPlayerObserver = isPlayerObserver;
        console.log("new Table");
        this.el = el("div.table", { style: { left: '0px', top: '0px' } },
            this.list_el = el("div.table_list")
        );
// this.list = list(this.list_el, Component);
        this.componentsOnTable = {};
        this.data = {};
    }

    receiveData(data) {
        this.data = {
            components: data.components,
            kits: data.kits,
            players: data.players,
        };
        for (const componentId in this.data.components) {
            if (!this.data.components.hasOwnProperty(componentId)) {
                continue;
            }
            const componentData = this.data.components[componentId];
            if (!this.componentsOnTable[componentId]) {
                this.componentsOnTable[componentId] = new Component(this, componentData);
                mount(this.list_el, this.componentsOnTable[componentId].el);
            }
            this.componentsOnTable[componentId].receiveData(componentData, componentId);
        }

        dev_inspector.tracePoint('finish updating table data');
    }

    updateView() {
        const notUpdatedComponents = Object.assign({}, this.componentsOnTable);
        setFeatsContext(this.getPlayerName, this.isPlayerObserver, this);

        for (const componentId in this.data.components) {
            if (!this.data.components.hasOwnProperty(componentId)) {
                continue;
            }
            const componentData = this.data.components[componentId];
            this.componentsOnTable[componentId].updateView(componentData);

            delete notUpdatedComponents[componentId]
        }

        for (const componentIdToRemove in notUpdatedComponents) {
            if (!notUpdatedComponents.hasOwnProperty(componentIdToRemove)) {
                continue;
            }
            delete this.componentsOnTable[componentIdToRemove];
            unmount(this.list_el, notUpdatedComponents[componentIdToRemove].el);
        }
        dev_inspector.tracePoint('finish updating table view');
    }

    update(data) {
        this.receiveData(data);
        this.updateView();
        dev_inspector.tracePoint('finish updating table');
    }

    addComponent(componentData) {
        // This is called when a component is added ON THIS BROWSER.
        this.data.components[componentData.componentId] = componentData;
        this.componentsOnTable[componentData.componentId] = new Component(this, componentData);
        mount(this.list_el, this.componentsOnTable[componentData.componentId].el);
        this.componentsOnTable[componentData.componentId].update(componentData, componentData.componentId);
        event.fireEvent(this.componentsOnTable[componentData.componentId], event.events.onPositionChanged,
            {
                left: parseFloat(componentData.left),
                top: parseFloat(componentData.top),
                width: parseFloat(componentData.width),
                height: parseFloat(componentData.height),
            });
    }

    removeComponent(componentId) {
        // This is called when a component is removed ON THIS BROWSER.
        // Because component removal is not directly synced but propagated as table refresh,
// table relies on update() to detect unused / non-referenced components
        // to remove Component object and DOM object.
        // TODO: maybe it's economical to sync component removal directly...
        this.componentsOnTable[componentId].disappear();
    }

    consolidatePropagation(proc) {
        consolidatePropagation(proc);
    }

    findEmptySpace(width, height) {
        const rect = {
            left: 64,
            top: 64,
            width: parseFloat(width),
            height: parseFloat(height),
        };
        for (let i = 0; i < 10; i++) {
            let collision = false;
            rect.bottom = rect.top + rect.height;
            rect.right = rect.left + rect.width;
            for (const componentId in this.data.components) {
                const target = this.data.components[componentId];
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
        return rect;
    }

    getNextZIndex() {
        let nextZIndex = 0;
        for (const otherId in this.data.components) {
            const other = this.data.components[otherId];
            if (nextZIndex <= other.zIndex) {
                nextZIndex = other.zIndex + 1;
            }
        }
        return nextZIndex;
    }

    getNextZIndexFor(componentData) {
        let currentZIndex = componentData.zIndex;
        for (const otherId in this.data.components) {
            if (otherId === componentData.componentId) {
                continue;
            }
            const other = this.data.components[otherId];
            if (currentZIndex <= other.zIndex) {
                currentZIndex = other.zIndex + 1;
            }
        }
        return currentZIndex;
    }

    getAllHandAreas() {
        const handAreasData = [];
        for (const cmpId in this.data.components) {
            const cmp = this.data.components[cmpId];
            if (cmp.handArea) {
                handAreasData.push(cmp);
            }
        }
        return handAreasData;
    }
}

export {
    Component,
    Table,
}
