import {el, mount, setAttr} from "./redom.es.js";
// import interact from './interact.js'

const draggability = {
    add: function (component) {
        function isDraggingPermitted() {
            return component.draggable && featsContext.canOperateOn(component);
        }

        interact(component.el).draggable({
            listeners: {
                move(event) {
                    if (!isDraggingPermitted()) {
                        return;
                    }
                    const top = parseFloat(component.el.style.top) + event.dy;
                    const left = parseFloat(component.el.style.left) + event.dx;
                    component.propagate_volatile({ top: top + "px", left: left + "px" });
                },
                end(event) {
                    if (!isDraggingPermitted()) {
                        return;
                    }
                    const top = parseFloat(component.el.style.top) + event.dy;
                    const left = parseFloat(component.el.style.left) + event.dx;
                    const diff = { top: top + "px", left: left + "px" };

                    if (component.ownable) {
                        const handArea = getOverlappingHandArea(component);
                        if (handArea) {
                            if (!(component.owner === handArea.owner)) {
                                component.owner = handArea.owner;
                                diff.owner = component.owner;
                            }
                        } else {
                            if (component.owner) {
                                component.owner = null;
                                diff.owner = component.owner;
                            }
                        }
                    }

                    component.propagate(diff);
                }
            }
        });

        function getOverlappingHandArea(component) {
            const rect = {
                top: parseFloat(component.el.style.top),
                left: parseFloat(component.el.style.left),
                bottom: parseFloat(component.el.style.top) + parseFloat(component.el.style.height),
                right: parseFloat(component.el.style.left) + parseFloat(component.el.style.width),
                height: parseFloat(component.el.style.height),
                width: parseFloat(component.el.style.width),
            };


            for (const target of featsContext.tableData.components) {
                if (target.handArea) {
                    const targetLeft = parseFloat(target.left);
                    const targetTop = parseFloat(target.top);
                    const targetRight = targetLeft + parseFloat(target.width);
                    const targetBottom = targetTop + parseFloat(target.height);
                    if (rect.left <= targetRight &&
                        targetLeft <= rect.right &&
                        rect.top <= targetBottom &&
                        targetTop <= rect.bottom) {
                        return target;
                    }
                }
            }
            return null;
        }
    },
    isEnabled: function (component, data) {
        return data.draggable === true;
    },
    update: function (component, data) {
        component.draggable = data.draggable;
        component.owner = data.owner;
        component.ownable = data.ownable;
    },
};

const flippability = {
    add: function (component) {
        function isFlippingPermitted() {
            return component.flippable && featsContext.canOperateOn(component);
        }

        component.el.addEventListener("dblclick", () => {
            if (!isFlippingPermitted()) {
                return;
            }
            let diff = {};
            if (component.owner && component.owner !== featsContext.playerName) {
                return;
            }
            if (component.faceup) {
                diff.faceup = component.faceup = false;
            } else {
                diff.faceup = component.faceup = true;
            }
            component.propagate(diff);
        });
    },
    isEnabled: function (component, data) {
        return data.flippable === true;
    },
    update: function (component, data) {
        component.flippable = data.flippable;
        component.faceup = data.faceup;
        if (component.faceup) {
            if (!component.owner || component.owner === featsContext.playerName) {
                if (data.showImage) {
                    setAttr(component.image, { src: data.faceupImage });
                }
                if (data.faceupText) {
                    component.textEl.innerText = data.faceupText;
                }
            } else {
                if (data.showImage) {
                    setAttr(component.image, { src: data.facedownImage });
                }
                if (data.facedownText) {
                    component.textEl.innerText = data.facedownText;
                }
            }
        } else {
            if (data.showImage) {
                setAttr(component.image, { src: data.facedownImage });
            }
            if (data.faceupText) {
                component.textEl.innerText = data.facedownText;
            }
        }
        component.faceup = data.faceup;

    },
};


const resizability = {
    add: function (component) {
        function isResizingPermitted() {
            return component.resizable && featsContext.canOperateOn(component);
        }

        interact(component.el).resizable({
            edges: {
                top: true,
                left: true,
                bottom: true,
                right: true,
            },
            invert: 'reposition',

            onmove: (event) => {
                if (!isResizingPermitted()) {
                    return;
                }
                let top = parseFloat(component.el.style.top) + event.deltaRect.top;
                let left = parseFloat(component.el.style.left) + event.deltaRect.left;
                let width = parseFloat(component.el.style.width) + event.deltaRect.width;
                let height = parseFloat(component.el.style.height) + event.deltaRect.height;
                component.propagate_volatile({ top: top, left: left, width: width, height: height });
            },
            onend: (event) => {
                if (!isResizingPermitted()) {
                    return;
                }
                // resizeend event have wrong value in deltaRect so just ignore it
                let top = parseFloat(component.el.style.top);
                let left = parseFloat(component.el.style.left);
                let width = parseFloat(component.el.style.width);
                let height = parseFloat(component.el.style.height);
                component.propagate({ top: top, left: left, width: width, height: height });
            },
        })
    },
    isEnabled: function (component, data) {
        return data.resizable === true;
    },
    update: function (component, data) {
        component.resizable = data.resizable;
    },
};

const rollability = {
    add: function (component) {
        function isRollingPermitted() {
            return component.rollable && featsContext.canOperateOn(component);
        }

        component.el.addEventListener("dblclick", startRoll);

        function startRoll(event) {
            if(!isRollingPermitted()) {
                return;
            }
            const duration = Math.random() * 1000 + 500;
            const finalValue = Math.floor(Math.random() * 6) + 1;
            component.propagate({ rollDuration: duration, rollFinalValue: finalValue, startRoll: true });

            rollability.roll(component, duration, finalValue);
            return false;
        }
    },
    isEnabled: function (component, data) {
        return data.rollable === true;
    },
    update: function (component, data) {
        component.rollable = data.rollable;

        if(data.startRoll) {
            data.startRoll = undefined;
            rollability.roll(component, data.rollDuration, data.rollFinalValue);
        }
    },
    roll: function (component, duration, finalValue) {
        const startTime = Date.now();
        setTimeout(() => showRolling(Math.floor(Math.random() * 6) + 1, Math.floor(Math.random() * 6) + 1), 200);

        function showRolling(fromValue, toValue) {
            component.el.innerText = fromValue;
            if (Date.now() < startTime + duration - 200) {
                setTimeout(() => showRolling(toValue, Math.floor(Math.random() * 6) + 1), 200);
            } else if (Date.now() < startTime + duration) {
                setTimeout(() => showRolling(toValue, finalValue), 200);
            }
            component.el.innerText = toValue;
            component.propagate({ rollDuration: 0, rollFinalValue: finalValue, startRoll: false });
        }
    }
};

const featsContext = {
    canOperateOn: function (component) {
        return ((!component.owner || component.owner === featsContext.playerName)
            && !featsContext.isPlayerObserver);
    }
};

function setFeatsContext(playerName, isPlayerObserver, tableData) {
    featsContext.playerName = playerName;
    featsContext.isPlayerObserver = isPlayerObserver;
    featsContext.tableData = tableData;
}

const feats = [
    draggability, flippability, resizability, rollability,
];

export {setFeatsContext, feats};