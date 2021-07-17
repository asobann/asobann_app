import {el, mount, setStyle, unmount} from "redom";
import {setFeatsContext, event} from "./feat.js";
import {dev_inspector} from "./dev_inspector.js"
import {pushComponentUpdate} from "./sync_table";

const Level = {
    A: 0,
    B: 1,
    C: 2,
};


// Single instance with single HTML Element to show overlay control
class Overlay {
    selectedComponent = null;
    element = null;

    constructor() {
        this.element = el('div.component_overlay', 'OVERLAY');
    }

    isSelected(component) {
        return this.selectedComponent === component;
    }

    select(component) {
        console.assert(component != null);
        this.selectedComponent = component;
        this.show();
    }

    unselect() {
        this.selectedComponent = null;
        this.show();
    }

    show() {
        if(this.selectedComponent == null) {
            setStyle(this.element, {
                display: 'none',
            });
        } else {
            setStyle(this.element, {
                left: this.selectedComponent.rect.left + this.selectedComponent.rect.width + 'px',
                top: this.selectedComponent.rect.top + 'px',
                zIndex: this.selectedComponent.zIndex,
                display: 'block',
            });
        }
    }
}


class Component {
    constructor(table, data, feats_to_use, overlay) {
        this.table = table;
        this.el = el(".component");
        this.feats = feats_to_use;
        this.overlay = overlay;
        for (const ability of this.feats) {
            ability.install(this, data);
        }
    }

    update(data, componentId) {
        this.receiveData(data, componentId);
        this.updateView(data);
    }

    receiveData(data, componentId) {
        this.componentId = componentId;
        for (const ability of this.feats) {
            if (ability.isEnabled(this, data)) {
                if (ability.hasOwnProperty('receiveData')) {
                    ability.receiveData(this, data);
                }
            }
        }
    }

    updateView(data) {
        for (const ability of this.feats) {
            if (ability.isEnabled(this, data)) {
                if (ability.hasOwnProperty('updateView')) {
                    ability.updateView(this, data);
                }
            }
        }
    }

    disappear() {
        for (const ability of this.feats) {
            ability.uninstall(this);
        }
    }

    /**
     * propagate does three things:
     *   - update whole table data with diff
     *   - update view of affected components
     *   - emit diff to server to update other players's browser
     *
     * @param diff
     * @param volatile - true if diff is one of points in a series of rapid changes (e.g. dragging) and can be ignored
     */
    propagate(diff, volatile) {
        if (volatile !== true) {
            volatile = false;
        }
        dev_inspector.tracePoint('propagate');
        this.table.queueForUpdatingView.pushComponentIdForUpdate(this.componentId);
        pushComponentUpdate(this.table, this.componentId, diff, volatile);
    }

    propagate_volatile(diff) {
        this.propagate(diff, true);
    }

    applyUserAction(level, proc) {
        this.table.queueForUpdatingView.startLevel(level);
        proc();

        this.table.queueForUpdatingView.exitLevel();
        if (this.table.queueForUpdatingView.isOutOfApplication()) {
            this.table.updateViewForImmediateOnly();
            this.table.queueForUpdatingView.queueForImmediate = [];
        }
    }
}

class QueueForUpdatingView {
    constructor() {
        this.queueToConsolidate = [];
        this.queueForImmediate = [];
        this.currentEffectiveLevel = null;
        this.runningApplications = [];
    }

    startLevel(level) {
        if (this.currentEffectiveLevel == null || this.currentEffectiveLevel < level) {
            this.currentEffectiveLevel = level;
        }
        this.runningApplications.push(level);
    }

    exitLevel() {
        this.runningApplications.pop();
        const previousLevel = this.runningApplications[this.runningApplications.length - 1];
        if (previousLevel < this.currentEffectiveLevel) {
            this.currentEffectiveLevel = previousLevel;
        }
    }

    isInTopLevel() {
        return this.runningApplications.length === 1;
    }

    isOutOfApplication() {
        return this.runningApplications.length === 0;
    }

    pushComponentIdForUpdate(componentId) {
        if (this.isOutOfApplication()) {
            return;
        }
        if (this.currentEffectiveLevel <= Level.A) {
            if (this.queueForImmediate.indexOf(componentId) === -1) {
                this.queueForImmediate.push(componentId);
            }
        } else if (this.currentEffectiveLevel === Level.B) {
            if (this.isInTopLevel()) {
                if (this.queueForImmediate.indexOf(componentId) === -1) {
                    this.queueForImmediate.push(componentId);
                }
            } else {
                if (this.queueToConsolidate.indexOf(componentId) === -1) {
                    this.queueToConsolidate.push(componentId);
                }
            }
        } else {
            if (this.queueToConsolidate.indexOf(componentId) === -1) {
                this.queueToConsolidate.push(componentId);
            }
        }
    }

    startConsolidatedUpdatingView(table) {
        setInterval(() => {
            table.updateViewForComponents(this.queueToConsolidate);
            this.queueToConsolidate.splice(0);
        }, 50);
    }
}

class Table {
    constructor({ getPlayerName, isPlayerObserver, feats_to_use }) {
        this.getPlayerName = getPlayerName;
        this.isPlayerObserver = isPlayerObserver;
        this.feats = feats_to_use;
        this.overlay = new Overlay();
        setFeatsContext(this.getPlayerName, this.isPlayerObserver, this);
        console.log("new Table");
        this.el = el("div.table", { style: { left: '0px', top: '0px' } },
            this.list_el = el("div.table_list")
        );
        mount(this.el, this.overlay.element);
        this.componentsOnTable = {};
        this.data = {};
        this.queueForUpdatingView = new QueueForUpdatingView();
        this.queueForUpdatingView.startConsolidatedUpdatingView(this);
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
                this.componentsOnTable[componentId] = new Component(this, componentData, this.feats, this.overlay);
                mount(this.list_el, this.componentsOnTable[componentId].el);
            }
            this.componentsOnTable[componentId].receiveData(componentData, componentId);
        }

        dev_inspector.tracePoint('finish updating table data');
    }

    updateView() {
        const notUpdatedComponents = Object.assign({}, this.componentsOnTable);

        for (const componentId in this.data.components) {
            if (!this.data.components.hasOwnProperty(componentId)) {
                continue;
            }
            const componentData = this.data.components[componentId];
            this.componentsOnTable[componentId].updateView(componentData);

            delete notUpdatedComponents[componentId];
        }

        for (const componentIdToRemove in notUpdatedComponents) {
            if (!notUpdatedComponents.hasOwnProperty(componentIdToRemove)) {
                continue;
            }
            delete this.componentsOnTable[componentIdToRemove];
            unmount(this.list_el, notUpdatedComponents[componentIdToRemove].el);
            delete notUpdatedComponents[componentIdToRemove].el;
        }
        dev_inspector.tracePoint('finish updating table view');
    }

    updateViewForComponents(componentIds) {
        for (const componentId of componentIds) {
            if (!this.data.components.hasOwnProperty(componentId)) {
                continue;
            }
            if(!this.componentsOnTable[componentId]) {
                // component is already removed
                continue;
            }
            const componentData = this.data.components[componentId];
            this.componentsOnTable[componentId].updateView(componentData);
        }
    }

    updateViewForImmediateOnly() {
        this.updateViewForComponents(this.queueForUpdatingView.queueForImmediate);
    }

    update(data) {
        this.receiveData(data);
        this.updateView();
        dev_inspector.tracePoint('finish updating table');
    }

    addComponent(componentData) {
        // This is called when a component is added ON THIS BROWSER.
        this.data.components[componentData.componentId] = componentData;
        this.componentsOnTable[componentData.componentId] = new Component(this, componentData, this.feats, this.overlay);
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
        // Component removal is synced through 'update many components' event.
        // The originating browser (this browser) needs to remove component element here.
        // Synced browsers will use Table.update() to remove component elements.
        const component = this.componentsOnTable[componentId];
        component.disappear();
        unmount(this.list_el, component.el);
        delete component.el;
        delete this.componentsOnTable[componentId];

        this.el.dispatchEvent(new Event('tableContentsChanged'));
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
    Level,
}
