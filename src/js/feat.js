import {el, mount, setAttr, setStyle, unmount} from "./redom.es.js";
import {allCardistry} from "./cardistry.js";
import {_, language} from "./i18n.js";
import {dev_inspector} from "./dev_inspector.js"
import {toolbox} from "./toolbox.js";

import interact from 'interactjs';

function arraysEqual(a, b) {
    if (a === b) return true;
    if (a == null || b == null) return false;
    if (a.length !== b.length) return false;

    for (let i = 0; i < a.length; ++i) {
        if (a[i] !== b[i]) return false;
    }
    return true;
}

function toRect(c) {
    if (c.left !== undefined && c.top !== undefined && c.width !== undefined && c.height !== undefined) {
        return {
            left: parseFloat(c.left),
            top: parseFloat(c.top),
            width: parseFloat(c.width),
            height: parseFloat(c.height),
        }
    }
    if (c.el) {
        return {
            left: parseFloat(c.el.style.left),
            top: parseFloat(c.el.style.top),
            width: parseFloat(c.el.style.width),
            height: parseFloat(c.el.style.height),
        }
    }
    throw 'Cannot detect rect';
}

const basic = {
    install: function (component, data) {
        if (data.showImage) {
            if (component.imageEl == null) {
                component.imageEl = el("img", { draggable: false });
                component.imageEl.ondragstart = () => {
                    return false;
                };
                mount(component.el, component.imageEl);
            }
            if (data.image) {
                setAttr(component.imageEl, { src: data.image });
            }
        } else {
            component.imageEl = null;
        }

        component.rect = {
            left: data.left,
            top: data.top,
            width: data.width,
            height: data.height,
        };

    },
    isEnabled: function () {
        return true;
    },
    receiveData(component, data) {
        component.rect.left = parseFloat(data.left);
        component.rect.top = parseFloat(data.top);
        component.rect.width = parseFloat(data.width);
        component.rect.height = parseFloat(data.height);
    },
    updateView(component, data) {
        if (data.showImage) {
            if (component.imageEl.src !== data.image) {
                setAttr(component.imageEl, { src: data.image });
            }
        }

        if (component.textEl == null) {
            if (data.toolboxFunction) {
                component.textEl = el("button.component_text", {
                    onclick: () => {
                        toolbox.use(data.toolboxFunction);
                    }
                });
                if (component.el.children.length > 0) {
                    mount(component.el, el('div', [component.textEl]), component.el.children[0]);
                } else {
                    mount(component.el, el('div', [component.textEl]));
                }
            } else {
                component.textEl = el("span.component_text");
                if (component.el.children.length > 0 && component.el.children[0].tagName !== 'IMG') {
                    mount(component.el, el('div', [component.textEl]), component.el.children[0]);
                } else {
                    mount(component.el, el('div', [component.textEl]));
                }
            }
        }
        if (data.text) {
            if (data["text_" + language]) {
                component.textEl.innerText = data["text_" + language];
            } else {
                component.textEl.innerText = data.text;
            }
        }
        if (data.textColor) {
            setStyle(component.textEl, { color: data.textColor });
        }
        if (data.textAlign) {
            switch (data.textAlign.trim()) {
                case 'center':
                    setStyle(component.textEl, {
                        "text-align": "center",
                        "vertical-align": "center",
                    });
                    break;
                case 'center bottom':
                    setStyle(component.textEl, {
                        "text-align": "center",
                        "bottom": 0,
                    });
                    break;
                default:
                    console.warn(`unsupported textAlign "${data.textAlign}"`);
            }
        }

        setAttr(component.el, {
            'data-component-name': data.name,
        });

        setStyle(component.el, {
            left: parseFloat(data.left) + "px",
            top: parseFloat(data.top) + "px",
            width: parseFloat(data.width) + "px",
            height: parseFloat(data.height) + "px",
            backgroundColor: data.color,
            zIndex: component.zIndex,
        });
    },
    uninstall: function () {
    },
}

const draggability = {
    install: function (component, data) {
        function isDraggingPermitted() {
            return component.draggable && featsContext.canOperateOn(component);
        }

        if (!data.draggable) {
            return;
        }

        interact(component.el).draggable({
            listeners: {
                start(event) {
                    if (!isDraggingPermitted()) {
                        return;
                    }

                    component.dragStartXonTarget = event.x0 - component.rect.left;
                    component.dragStartYonTarget = event.y0 - component.rect.top;
                },
                move(event) {
                    if (!isDraggingPermitted()) {
                        return;
                    }
                    dev_inspector.startTrace('draggability.move');
                    dev_inspector.tracePoint('event listener');
                    featsContext.table.consolidatePropagation(() => {
                        featsContext.fireEvent(component, draggability.events.onMoving,
                            {
                                left: (event.x - component.dragStartXonTarget) + 'px',
                                top: (event.y - component.dragStartYonTarget) + 'px',
                                dx: event.dx,
                                dy: event.dy,
                                x: event.page.x,
                                y: event.page.y,
                            });
                    });
                    featsContext.table.updateView();
                    dev_inspector.endTrace();
                },
                end(event) {
                    if (!isDraggingPermitted()) {
                        return;
                    }
                    dev_inspector.startTrace('draggability.end');
                    dev_inspector.tracePoint('event listener');
                    console.log("draggable end", component.componentId);
                    // featsContext.table.consolidatePropagation(() => {
                    featsContext.fireEvent(component, featsContext.events.onPositionChanged,
                        {
                            left: event.page.x - component.dragStartXonTarget,
                            top: event.page.y - component.dragStartYonTarget,
                            width: component.rect.width,
                            height: component.rect.height,
                        });
                    featsContext.fireEvent(component, draggability.events.onMoveEnd, {});
                    // });
                    featsContext.table.updateView();
                    dev_inspector.tracePoint('event listener');
                }
            }
        });

        featsContext.addEventListener(component, draggability.events.onMoving, (e) => {
            // component.propagate_volatile({
            //     top: e.top + "px",
            //     left: e.left + "px",
            //     moving: true
            // });
            component.propagate_volatile({
                left: (e.x - component.dragStartXonTarget) + 'px',
                top: (e.y - component.dragStartYonTarget) + 'px',
                moving: true
            });
            featsContext.table.updateView();
        });

        featsContext.addEventListener(component, featsContext.events.onPositionChanged, (e) => {
            component.propagate({
                left: e.left + "px",
                top: e.top + "px",
                width: e.width + "px",
                height: e.height + "px",
                moving: false,
            });
            featsContext.table.updateView();

        });
    },
    isEnabled: function (component, data) {
        return data.draggable === true;
    },
    onComponentUpdate: function (component, data) {
        component.draggable = data.draggable;
        component.ownable = data.ownable;  // TODO: good chance ownable will not be used
    },
    uninstall: function (component) {
        interact(component.el).draggable(false);
    },
    events: {
        onMoving: "draggability.onMoving",
        onMoveEnd: "draggability.onMoveEnd",
    }
};

const flippability = {
    install: function (component, data) {
        if (!flippability.isEnabled(component, data)) {
            return;
        }

        function isFlippingPermitted() {
            return component.flippable && featsContext.canOperateOn(component);
        }

        component.el.addEventListener("dblclick", () => {
            if (!isFlippingPermitted()) {
                return;
            }
            dev_inspector.startTrace('flippability.dblclick');
            dev_inspector.tracePoint('event listener');
            let diff = {};
            if (component.owner && component.owner !== featsContext.getPlayerName()) {
                return;
            }
            if (component.faceup) {
                diff.faceup = component.faceup = false;
            } else {
                diff.faceup = component.faceup = true;
            }
            component.propagate(diff);
            featsContext.table.updateView();
            dev_inspector.endTrace();
        });
    },
    isEnabled: function (component, data) {
        return data.flippable === true;
    },
    receiveData(component, data) {
        component.flippable = data.flippable;
        component.owner = data.owner;
        component.faceup = data.faceup;
    },
    updateView(component, data) {
        if (component.faceup) {
            if (!component.owner || component.owner === featsContext.getPlayerName()) {
                if (data.showImage) {
                    if (component.imageEl.src !== data.faceupImage) {
                        setAttr(component.imageEl, { src: data.faceupImage });
                    }
                }
                if (data.faceupText) {
                    if (data["faceupText_" + language]) {
                        component.textEl.innerText = data["faceupText_" + language];
                    } else {
                        component.textEl.innerText = data.faceupText;
                    }
                } else {
                    component.textEl.innerText = '';
                }
            } else {
                if (data.showImage) {
                    if (component.imageEl.src !== data.facedownImage) {
                        setAttr(component.imageEl, { src: data.facedownImage });
                    }
                }
                if (data.facedownText) {
                    if (data["facedownText_" + language]) {
                        component.textEl.innerText = data["facedownText_" + language];
                    } else {
                        component.textEl.innerText = data.facedownText;
                    }
                } else {
                    component.textEl.innerText = '';
                }
            }
        } else {
            if (data.showImage) {
                if (component.imageEl.src !== data.facedownImage) {
                    setAttr(component.imageEl, { src: data.facedownImage });
                }
            }
            if (data.facedownText) {
                if (data["facedownText_" + language]) {
                    component.textEl.innerText = data["facedownText_" + language];
                } else {
                    component.textEl.innerText = data.facedownText;
                }
            } else {
                component.textEl.innerText = '';
            }
        }

    },
    uninstall: function (component) {
    },

};


const resizability = {
    install: function (component, componentData) {
        function isResizingPermitted() {
            return component.resizable && featsContext.canOperateOn(component);
        }

        if (!componentData.resizable) {
            // do not install resizability
            return;
        }

        interact(component.el).resizable({
            edges: {
                left: true,
                top: true,
                right: true,
                bottom: true,
            },
            invert: 'reposition',

            onmove: (event) => {
                if (!isResizingPermitted()) {
                    return;
                }
                let left = parseFloat(component.el.style.left) + event.deltaRect.left;
                let top = parseFloat(component.el.style.top) + event.deltaRect.top;
                let width = parseFloat(component.el.style.width) + event.deltaRect.width;
                let height = parseFloat(component.el.style.height) + event.deltaRect.height;
                component.propagate_volatile({ left: left, top: top, width: width, height: height });
                featsContext.table.updateView();
            },
            onend: (/*event*/) => {
                if (!isResizingPermitted()) {
                    return;
                }
                // resizeend event have wrong value in deltaRect so just ignore it
                let left = parseFloat(component.el.style.left);
                let top = parseFloat(component.el.style.top);
                let width = parseFloat(component.el.style.width);
                let height = parseFloat(component.el.style.height);
                featsContext.fireEvent(component, featsContext.events.onPositionChanged,
                    {
                        left: left,
                        top: top,
                        width: width,
                        height: height,
                    });
            },
        })
    },
    isEnabled: function (component, data) {
        return data.resizable === true;
    },
    onComponentUpdate: function (component, data) {
        component.resizable = data.resizable;
    },
    uninstall: function (component) {
        interact(component.el).resizable(false);
    },
};

const rollability = {
    install: function (component, data) {
        function isRollingPermitted() {
            return component.rollable && featsContext.canOperateOn(component);
        }

        if (!rollability.isEnabled(component, data)) {
            return;
        }

        component.el.addEventListener("dblclick", startRoll);

        function startRoll(/*event*/) {
            if (!isRollingPermitted()) {
                return;
            }
            if (component.rolling) {
                return false;
            }
            const duration = Math.random() * 1000 + 500;
            const finalValue = Math.floor(Math.random() * 6) + 1;
            component.rolling = true;
            component.propagate({ rollDuration: duration, rollFinalValue: finalValue, startRoll: true });
            featsContext.table.updateView();
            return false;
        }
    },
    isEnabled: function (component, data) {
        return data.rollable === true;
    },
    onComponentUpdate: function (component, data) {
        component.rollable = data.rollable;

        if (data.startRoll) {
            data.startRoll = undefined;
            component.rolling = true;
            rollability.roll(component, data.rollDuration, data.rollFinalValue);
        }

        if (data.rollFinalValue && !component.rolling) {
            if (data.rollFinalValue === component.rollCurrentValue) {
                return;
            }
            const previousEls = [];
            for (const e of component.el.children) {
                if (e.className === 'dice_image') {
                    previousEls.push(e);
                }
            }
            for (const e of previousEls) {
                unmount(component.el, e);
            }
            const finalEl = el("div.dice_image", { style: { width: "100%", height: "100%" } });
            setStyle(finalEl, {
                animation: 'none',
                backgroundImage: `url("/static/images/dice_blue_${data.rollFinalValue}.jpg")`,
                backgroundSize: '100% 100%',
                backgroundPosition: 'left',
                backgroundRepeat: 'no-repeat',
            });
            mount(component.el, finalEl);
            component.rollCurrentValue = data.rollFinalValue;
        }
    },
    uninstall: function (component) {
    },
    roll: function (component, duration, finalValue) {
        const ANIMATION_INTERVAL = 200;

        component.rolling = true;
        component.rollCurrentValue = null;
        const fromValue = Math.floor(Math.random() * 6) + 1;
        const toValue = Math.floor(Math.random() * 6) + 1;
        const startTime = Date.now();
        let previousRollingEl = null;
        for (const e of component.el.children) {
            if (e.className === 'dice_image') {
                previousRollingEl = e;
            }
        }
        showRolling(fromValue, toValue, previousRollingEl);

        function showRolling(fromValue, toValue, previousRollingEl) {
            if (previousRollingEl) {
                unmount(component.el, previousRollingEl);
            }
            // repeating animation requires new element
            const rollingEl = el("div.dice_image", { style: { width: "100%", height: "100%" } });
            setStyle(rollingEl, {
                animation: `dice_rolling ${ANIMATION_INTERVAL}ms linear 0s 1  `,
                backgroundImage: `url("/static/images/dice_blue_${toValue}.jpg"), url("/static/images/dice_blue_${fromValue}.jpg")`,
                backgroundPosition: 'left, right',
                backgroundRepeat: 'no-repeat, no-repeat',
            });
            mount(component.el, rollingEl);

            if (Date.now() < startTime + duration - ANIMATION_INTERVAL) {
                setTimeout(() => showRolling(toValue, Math.floor(Math.random() * 6) + 1, rollingEl), ANIMATION_INTERVAL);
            } else if (Date.now() < startTime + duration) {
                setTimeout(() => showRolling(toValue, finalValue, rollingEl), ANIMATION_INTERVAL);
            } else {
                setTimeout(() => {
                    component.rolling = false;
                    component.propagate({ rollDuration: 0, rollFinalValue: finalValue, startRoll: false });
                    featsContext.table.updateView();
                }, ANIMATION_INTERVAL);
            }

        }
    }
};

/* not used for the time being */
/*
const collidability = {
    install: function (component) {
        if (!component.currentCollisions) {
            component.currentCollisions = {};
        }

        featsContext.addEventListener(component, featsContext.events.onPositionChanged, (e) => {
            const collided = pickCollidedComponents();
            processAllStart(collided);
            processAllEnd(collided);

            function pickCollidedComponents() {
                const collided = [];
                for (const componentId in featsContext.table.componentsOnTable) {
                    const target = featsContext.table.componentsOnTable[componentId];
                    if (target === component) {
                        continue;
                    }
                    if (!areTheyCollidable(component, target)) {
                        continue;
                    }
                    if (isOverlapped({ top: e.top, left: e.left, height: e.height, width: e.width }, target)) {
                        collided.push(target);
                    }
                }
                return collided;
            }

            function areTheyCollidable(c1, c2) {
                if (c1.traylike && !c2.traylike) {
                    return true;
                }
                if (!c1.traylike && c2.traylike) {
                    return true;
                }
                return false;
            }

            function isOverlapped(c1, c2) {
                const rect1 = toRect(c1);
                const rect2 = toRect(c2);
                return (rect1.left <= rect2.left + rect2.width &&
                    rect2.left <= rect1.left + rect1.width &&
                    rect1.top <= rect2.top + rect2.height &&
                    rect2.top <= rect1.top + rect1.height);
            }

            function processAllStart(collided) {
                for (const other of collided) {
                    if (component.currentCollisions[other.componentId]) {
                        continue;
                    }
                    component.currentCollisions[other.componentId] = true;
                    other.currentCollisions[component.componentId] = true;

                    component.propagate({ 'currentCollisions': component.currentCollisions });
                    other.propagate({ 'currentCollisions': other.currentCollisions });
                    featsContext.fireEvent(component, collidability.events.onCollisionStart, { collider: other });
                    featsContext.fireEvent(other, collidability.events.onCollisionStart, { collider: component });
                }
            }

            function processAllEnd(collided) {
                for (const componentId in component.currentCollisions) {
                    if (collided.find(e => e.componentId === componentId)) {
                        continue;
                    }

                    delete component.currentCollisions[componentId];
                    component.propagate({ 'currentCollisions': component.currentCollisions });

                    const other = featsContext.table.componentsOnTable[componentId];
                    if (other) {
                        // there is a chance that other is already removed from table
                        delete other.currentCollisions[component.componentId];

                        other.propagate({ 'currentCollisions': other.currentCollisions });
                        featsContext.fireEvent(component, collidability.events.onCollisionEnd, { collider: other });
                        featsContext.fireEvent(other, collidability.events.onCollisionEnd, { collider: component });
                    }
                }
            }

        });
    },
    isEnabled: function (component, data) {
        return true;
    },
    onComponentUpdate: function (component, data) {
        if (data.currentCollisions) {
            component.currentCollisions = data.currentCollisions;
        }

        component.moving = data.moving;
    },
    uninstall: function (component) {
        const currentCollisions = component.currentCollisions;
        component.currentCollisions = [];  // avoid recurse
        for (const componentId in currentCollisions) {
            const other = featsContext.table.componentsOnTable[componentId];
            if (other) {
                // there is a chance that other is already removed from table
                delete other.currentCollisions[component.componentId];

                other.propagate({ 'currentCollisions': other.currentCollisions });
                featsContext.fireEvent(component, collidability.events.onCollisionEnd, { collider: other });
                featsContext.fireEvent(other, collidability.events.onCollisionEnd, { collider: component });
            }
        }
    },

    events: {
        onCollisionStart: 'collidability.onCollisionStart',
        onCollisionEnd: 'collidability.onCollisionEnd',
    },
};
*/

const within = {
    install: function (component) {
        if (!component.thingsWithinMe) {
            component.thingsWithinMe = {};
            component.iAmWithin = {};
        }

        featsContext.addEventListener(component, featsContext.events.onPositionChanged, (e) => {
            dev_inspector.tracePoint('within.onPositionChanged');
            const withinCheckResult = pickCollidedComponents();
            processAllStart(withinCheckResult);
            processAllEnd(withinCheckResult);
            dev_inspector.tracePoint('finished within.onPositionChanged');

            function pickCollidedComponents() {
                const thingsWithinMe = [];
                const iAmWithin = [];
                for (const componentId in featsContext.table.componentsOnTable) {
                    if (!featsContext.table.componentsOnTable.hasOwnProperty(componentId)) {
                        continue;
                    }
                    const target = featsContext.table.componentsOnTable[componentId];
                    if (target === component) {
                        continue;
                    }
                    if (canThisEverWithin(component, target)) {
                        if (isWithin({ left: e.left, top: e.top, width: e.width, height: e.height }, target)) {
                            thingsWithinMe.push(target);
                        }
                    }
                    if (canThisEverWithin(target, component)) {
                        if (isWithin(target, { left: e.left, top: e.top, width: e.width, height: e.height })) {
                            iAmWithin.push(target);
                        }
                    }

                }
                return { thingsWithinMe: thingsWithinMe, iAmWithin: iAmWithin };
            }

            function canThisEverWithin(area, visitor) {
                return area.traylike && !visitor.traylike;
            }

            function isWithin(area, visitor) {
                const areaRect = toRect(area);
                const visitorRect = toRect(visitor);
                return (areaRect.left <= visitorRect.left &&
                    visitorRect.left + visitorRect.width <= areaRect.left + areaRect.width &&
                    areaRect.top <= visitorRect.top &&
                    visitorRect.top + visitorRect.height <= areaRect.top + areaRect.height);
            }

            function processAllStart(withinCheckResult) {
                console.log("processAllStart start");
                const thingsWithinMe = withinCheckResult.thingsWithinMe;
                const iAmWithin = withinCheckResult.iAmWithin;
                for (const other of thingsWithinMe) {
                    processStartWithin(component, other);
                }

                for (const other of iAmWithin) {
                    processStartWithin(other, component);
                }
                console.log("processAllStart end");

                function processStartWithin(area, visitor) {
                    if (area.thingsWithinMe[visitor.componentId]) {
                        return;
                    }
                    area.thingsWithinMe[visitor.componentId] = true;
                    visitor.iAmWithin[area.componentId] = true;

                    area.propagate({ 'thingsWithinMe': area.thingsWithinMe });
                    visitor.propagate({ 'iAmWithin': visitor.iAmWithin });
                    featsContext.fireEvent(area, within.events.onWithin, { visitor: visitor });
                    featsContext.table.updateView();
                }
            }

            function processAllEnd(withinCheckResult) {
                console.log("processAllEnd start");

                for (const visitorId in component.thingsWithinMe) {
                    if (withinCheckResult.thingsWithinMe.find(e => e.componentId === visitorId)) {
                        continue;
                    }

                    delete component.thingsWithinMe[visitorId];
                    component.propagate({ 'thingsWithinMe': component.thingsWithinMe });

                    const other = featsContext.table.componentsOnTable[visitorId];
                    if (other) {
                        // there is a chance that other is already removed from table
                        delete other.iAmWithin[component.componentId];

                        other.propagate({ 'iAmWithin': other.iAmWithin });
                        featsContext.fireEvent(component, within.events.onWithinEnd, { visitor: other });
                    }
                }

                for (const otherId in component.iAmWithin) {
                    if (withinCheckResult.iAmWithin.find(e => e.componentId === otherId)) {
                        continue;
                    }

                    delete component.iAmWithin[otherId];
                    component.propagate({ 'iAmWithin': component.iAmWithin });

                    const other = featsContext.table.componentsOnTable[otherId];
                    if (other) {
                        // there is a chance that other is already removed from table
                        delete other.thingsWithinMe[component.componentId];

                        other.propagate({ 'thingsWithinMe': other.thingsWithinMe });
                        featsContext.fireEvent(other, within.events.onWithinEnd, { visitor: component });
                    }
                }
                featsContext.table.updateView();
                console.log("processAllEnd end");

            }

        });
    },
    isEnabled: function (/*component, data*/) {
        return true;
    },
    onComponentUpdate: function (component, data) {
        if (data.thingsWithinMe) {
            component.thingsWithinMe = data.thingsWithinMe;
        }
        if (data.iAmWithin) {
            component.iAmWithin = data.iAmWithin;
        }

        component.moving = data.moving;
    },
    uninstall: function (component) {
        const thingsWithinMe = component.thingsWithinMe;
        const iAmWithin = component.iAmWithin;
        component.thingsWithinMe = [];  // avoid recurse
        component.iAmWithin = [];  // avoid recurse
        for (const componentId in thingsWithinMe) {
            if (!thingsWithinMe.hasOwnProperty(componentId)) {
                continue;
            }
            const other = featsContext.table.componentsOnTable[componentId];
            if (other) {
                // there is a chance that other is already removed from table
                delete other.iAmWithin[component.componentId];

                other.propagate({ 'iAmWithin': other.iAmWithin });
                featsContext.fireEvent(component, within.events.onWithinEnd, { visitor: other });
            }
        }
        for (const otherId in iAmWithin) {
            if (!iAmWithin.hasOwnProperty(otherId)) {
                continue;
            }
            const other = featsContext.table.componentsOnTable[otherId];
            if (other) {
                // there is a chance that other is already removed from table
                delete other.thingsWithinMe[component.componentId];

                other.propagate({ 'thingsWithinMe': other.thingsWithinMe });
                featsContext.fireEvent(other, within.events.onWithinEnd, { visitor: component });
            }
        }
        featsContext.table.updateView();
    },

    events: {
        onWithin: 'within.onCollisionStart',
        onWithinEnd: 'within.onCollisionEnd',
    },
};

const ownership = {
    install: function (component) {
        featsContext.addEventListener(component, within.events.onWithin, (e) => {
            const other = e.visitor;
            if (component.handArea && !other.handArea) {
                const hand = component;
                const onHand = other;
                if (!(onHand.owner === hand.owner)) {
                    onHand.propagate({ owner: onHand.owner = hand.owner });
                }
            }
            featsContext.table.updateView();
        });
        featsContext.addEventListener(component, within.events.onWithinEnd, (e) => {
            const other = e.visitor;
            if (component.handArea && !other.handArea) {
                const hand = component;
                const onHand = other;
                if (onHand.owner === hand.owner) {
                    onHand.propagate({ owner: onHand.owner = null });
                }
            }
            featsContext.table.updateView();
        });
    },
    isEnabled: function (/*component, data*/) {
        return true;
    },
    onComponentUpdate: function (component, data) {
        if (component.owner !== data.owner) {
            console.log("ownership update change", component.componentId, component.owner, "to", data.owner);
        }
        component.owner = data.owner;
        component.handArea = data.handArea;
        if (component.moving) {
            return;
        }
        if (!component.handArea) {
            if (component.owner) {
                setStyle(component.el, {
                    boxShadow: '0 0 20px green',
                })
            } else {
                setStyle(component.el, {
                    boxShadow: null,
                })
            }
        }
    },
    uninstall: function (component) {

    }
};


const handArea = {
    install: function (component, componentData) {
        if (componentData.handArea) {
            component.handArea = componentData.handArea;
            const className = component.el.getAttribute('class');
            if (!className.includes('hand_area')) {
                setAttr(component.el, 'class', className + ' hand_area');
            }
        }
    },
    isEnabled: function (component, data) {
        return data.handArea === true;
    },
    onComponentUpdate: function () {
    },
    uninstall: function () {

    }
};

const traylike = {
    // This feat is for tray-like object.  Non tray-like object can be put on tray-like objects.
    // Objects on a tray moves with the tray.
    // Hand Area is a tray-like object.  A box is another example of tray-like object.
    // Currently everything not tray-like can be put on tray-like.  Tray-like does not be put on another tray-like.
    install: function (component, data) {
        if (!traylike.isEnabled(component, data)) {
            // do not install
            return;
        }

        component.onTray = {};

        featsContext.addEventListener(component, within.events.onWithin, (e) => {
            if (!component.traylike) {
                return;
            }
            if (e.visitor.traylike) {
                return;
            }
            component.onTray[e.visitor.componentId] = true;
            component.propagate({ onTray: component.onTray });
            if (e.visitor.zIndex < component.zIndex) {
                e.visitor.propagate({ zIndex: featsContext.table.getNextZIndex() });
            }
            featsContext.table.updateView();
        });

        featsContext.addEventListener(component, within.events.onWithinEnd, (e) => {
            if (!component.traylike) {
                return;
            }
            if (e.visitor.traylike) {
                return;
            }
            delete component.onTray[e.visitor.componentId];
            component.propagate({ onTray: component.onTray });
            featsContext.table.updateView();
        });

        featsContext.addEventListener(component, draggability.events.onMoving, (e) => {
            if (!component.traylike) {
                return;
            }
            const dx = e.dx;
            const dy = e.dy;
            for (const componentId in component.onTray) {
                const target = featsContext.table.componentsOnTable[componentId];
                target.propagate_volatile({
                    left: target.rect.left + dx,
                    top: target.rect.top + dy,
                });
            }
            featsContext.table.updateView();
        });

        featsContext.addEventListener(component, draggability.events.onMoveEnd, (/*e*/) => {
            if (!component.traylike) {
                return;
            }
            for (const componentId in component.onTray) {
                const target = featsContext.table.componentsOnTable[componentId];
                target.propagate({
                    left: target.rect.left,
                    top: target.rect.top,
                });
            }
            featsContext.table.updateView();
        })
    },
    isEnabled: function (component, data) {
        return data.traylike === true;
    },
    onComponentUpdate: function (component, data) {
        // On or off of a tray decision is handled in tray-like object's update.
        // This is chiefly to reduce computation.  And also for simplicity.
        component.traylike = data.traylike;
        if (data.onTray) {
            component.onTray = data.onTray;
        }
    },
    uninstall: function (component) {

    }
};

const touchToRaise = {
    install: function (component, componentData) {
        component.el.addEventListener("mousedown", (/*event*/) => {
            if (featsContext.isPlayerObserver()) {
                return;
            }
            if (component.handArea || component.traylike || componentData.boxOfComponents) {
                return;
            }
            const nextZIndex = featsContext.table.getNextZIndexFor(componentData);
            if (nextZIndex > component.zIndex) {
                component.zIndex = nextZIndex
                setStyle(component.el, { zIndex: component.zIndex });
                component.propagate({ zIndex: component.zIndex });
            }
            featsContext.table.updateView();
        });
    },

    isEnabled: function (/*component, data*/) {
        return true;
    },

    onComponentUpdate: function (component, data) {
        if (data.zIndex) {
            component.zIndex = data.zIndex;
        } else {
            component.zIndex = featsContext.table.getNextZIndex();
        }
    },

    uninstall: function (component) {
    }
};

const stowage = {
    install: function (component, componentData) {
        if (!componentData.stowage) {
            return;
        }
        featsContext.addEventListener(component, within.events.onWithin, (e) => {
            if (e.visitor.traylike) {
                return;
            }
            e.visitor.propagate({ isStowed: true });
            featsContext.table.updateView();
        });

        featsContext.addEventListener(component, within.events.onWithinEnd, (e) => {
            if (!component.traylike) {
                return;
            }
            if (e.visitor.traylike) {
                return;
            }
            e.visitor.propagate({ isStowed: false });
            featsContext.table.updateView();
        });
    },
    isEnabled: function (/*component, data*/) {
        // stowage feat works for both stowage traylike and stowed components
        return true;
    },

    onComponentUpdate: function (component, data) {
        if (data.isStowed === undefined) {
            return;
        }
        component.isStowed = data.isStowed;

        if (component.isStowed) {
            setStyle(component.el, { opacity: 0.4 });
        } else {
            setStyle(component.el, { opacity: null });
        }
    },
    uninstall: function (component) {
    }
};

const cardistry = {
    install: function (component, data) {
        if (!data.cardistry) {
            return;
        }
        component.cardistry = {};
        setStyle(component.el, {
            'flex-flow': 'column wrap',
            'justify-content': 'left',
            'align-items': 'flex-start'
        });

        for (const cardistry of allCardistry) {
            const button = el('button', {
                    'data-button-name': cardistry.name,
                    onclick: () => {
                        cardistry.execute(component, featsContext);
                    },
                },
                cardistry.label,
            );
            component.el.appendChild(button);
            component.cardistry[cardistry.name] = {
                button: button,
            };
        }
    },
    isEnabled: function (component, data) {
        return data.hasOwnProperty('cardistry');
    },
    onComponentUpdate: function (component, componentData) {
        if (!componentData.cardistry) {
            return;
        }

        for (const cardistry of allCardistry) {
            if (componentData.cardistry.includes(cardistry.name)) {
                setStyle(component.cardistry[cardistry.name].button, { display: null });
                if (cardistry.isEnabled(component, featsContext)) {
                    setAttr(component.cardistry[cardistry.name].button, 'disabled', null);
                } else {
                    setAttr(component.cardistry[cardistry.name].button, 'disabled', true);
                }
                cardistry.onComponentUpdate(component, componentData);
            } else {
                setStyle(component.cardistry[cardistry.name].button, { display: 'none' });
            }
        }
    },
    uninstall: function (component) {
    }
};

const counter = {
    install: function (component, data) {
        if (!data.counter) {
            return;
        }

        if (!data.hasOwnProperty("counterValue")) {
            data.counterValue = 0;
        }
        const counterValue = data.counterValue;
        component.el.appendChild(
            el('div.counter', [
                el('div.labelContainer', [
                    el('div.counterLabel', {}, _("Counter"))
                ]),
                el('div.valueContainer', [
                    component.valueEl = el('div.counterValue', {}, counterValue)
                ]),
                el('div.buttons', [
                    el('button#subTen', {
                        onclick: (() => {
                            count((v) => v - 10)
                        })
                    }, '-10'),
                    el('button#subOne', {
                        onclick: (() => {
                            count((v) => v - 1)
                        })
                    }, '-1'),
                    el('button#reset', {
                        onclick: (() => {
                            count((/* v */) => 0)
                        })
                    }, '0'),
                    el('button#addOne', {
                        onclick: (() => {
                            count((v) => v + 1)
                        })
                    }, '+1'),
                    el('button#addTen', {
                        onclick: (() => {
                            count((v) => v + 10)
                        })
                    }, '+10'),
                ]),
            ])
        );

        function count(fn) {
            if (!data.hasOwnProperty("counterValue")) {
                data.counterValue = 0;
            }
            const counterValue = data.counterValue;
            const newValue = fn(counterValue);
            data.counterValue = component.valueEl.innerText = newValue;
            component.propagate({ counterValue: newValue });
            featsContext.table.updateView();
        }
    },
    isEnabled: function (component, data) {
        return data.counter === true;
    },
    onComponentUpdate: function (component, componentData) {
        if (!componentData.counter) {
            return;
        }

        if (componentData.hasOwnProperty("counterValue")) {
            component.valueEl.innerText = componentData.counterValue;
        }
    },
    uninstall: function (component) {
    }
};

const editability = {
    install: function (component, data) {
        if (!editability.isEnabled(component, data)) {
            return;
        }

        function isEditingPermitted() {
            return component.editable && featsContext.canOperateOn(component);
        }

        component.el.addEventListener("dblclick", () => {
            if (!isEditingPermitted()) {
                return;
            }

            if (data.editing) {
                return;
            }

            data.editing = true;
            let textareaEl;
            const formEl = el('div.note_editor', [
                textareaEl = el('textarea', { oninput: editing }, data.text),
                el('br', {}, data.text),
                el('div.button_frame', [
                    el('button', { onclick: endEditing }, _('Finish')),
                ])
            ]);
            mount(component.el, formEl);

            function editing() {
                component.propagate({ 'text': textareaEl.value });
                featsContext.table.updateView();
            }

            function endEditing() {
                component.propagate({ 'text': textareaEl.value });
                unmount(component.el, formEl);
                data.editing = false;
                featsContext.table.updateView();
            }
        });

    },
    isEnabled: function (component, data) {
        return data.editable === true;
    },
    onComponentUpdate: function (component, data) {
        component.editable = data.editable;
    },
    uninstall: function (component) {
    },
};


const featsContext = {
    canOperateOn: function (component) {
        return ((!component.owner || component.owner === featsContext.getPlayerName())
            && !featsContext.isPlayerObserver());
    },
    addEventListener: function (component, eventName, handler) {
        if (!eventName) {
            throw `addEventListener: eventName must be specified but was ${eventName}`
        }
        if (!component.featEventListeners) {
            component.featEventListeners = {};
        }
        if (!component.featEventListeners[eventName]) {
            component.featEventListeners[eventName] = [];
        }
        component.featEventListeners[eventName].push({ component: component, handler: handler });
    },
    fireEvent: function (component, eventName, event) {
        if (!eventName) {
            throw `fireEvent: eventName must be specified but was ${eventName}`
        }
        if (!component.featEventListeners[eventName]) {
            return;
        }
        for (const entry of component.featEventListeners[eventName]) {
            if (entry.component === component) {
                entry.handler(event);
            }
        }
    },
    events: {
        /*
        This event is fired when position or size of component is changed.
        Event must have these parameters.
            top:
            left:
            height:
            width:
            moving: true if in transition (being dragged)
         */
        onPositionChanged: 'onPositionChanged',
    }
};

function setFeatsContext(getPlayerName, isPlayerObserver, table) {
    featsContext.getPlayerName = getPlayerName;
    featsContext.isPlayerObserver = isPlayerObserver;
    featsContext.table = table;
}

const event = {
    events: featsContext.events,
    fireEvent: function (component, eventName, event) {
        featsContext.fireEvent(component, eventName, event);
    }
};

const feats = [
    basic,  // this must be the first ability in feats
    within,
    draggability,
    flippability,
    resizability,
    rollability,
    traylike,
    handArea,
    ownership,
    touchToRaise,
    stowage,
    cardistry,
    counter,
    editability
];

// dynamic validation
// It also helps removing some of 'unused property' warning but not all.
for (const feat of feats) {
    console.assert(feat.install !== undefined);
    console.assert(feat.isEnabled !== undefined);
    console.assert(feat.onComponentUpdate !== undefined);
    console.assert(feat.uninstall !== undefined);
}

export {setFeatsContext, feats, event};