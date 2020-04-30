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
                    let top = parseFloat(component.el.style.top) + event.dy;
                    let left = parseFloat(component.el.style.left) + event.dx;
                    component.propagate({ top: top + "px", left: left + "px" });
                },
                end() {
                    if (!isDraggingPermitted()) {
                        return;
                    }
                    if(!component.ownable) {
                        return;
                    }
                    const handArea = getOverlappingHandArea(component);
                    if (handArea) {
                        if (!(component.owner === handArea.owner)) {
                            component.owner = handArea.owner;
                            component.propagate({ owner: component.owner });
                        }
                    } else {
                        if (component.owner) {
                            component.owner = null;
                            component.propagate({ owner: component.owner });
                        }
                    }
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
    enabled: function (component, data) {
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
    enabled: function (component, data) {
        return data.flippable === true;
    },
    update: function (component, data) {
        component.flippable = data.flippable;
        component.faceup = data.faceup;
        if (component.faceup) {
            if (!component.owner || component.owner === featsContext.playerName) {
                if(data.showImage) {
                    setAttr(component.image, { src: data.faceupImage });
                } else {
                    component.el.innerText = data.faceupText;
                }
            } else {
                if(data.showImage) {
                    setAttr(component.image, { src: data.facedownImage });
                } else {
                    component.el.innerText = data.facedownText;
                }
            }
        } else {
            if(data.showImage) {
                setAttr(component.image, { src: data.facedownImage });
            } else {
                component.el.innerText = data.facedownText;
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
                component.propagate({ top: top, left: left, width: width, height: height });
            },
        })
    },
    enabled: function (component, data) {
        return data.resizable === true;
    },
    update: function (component, data) {
        component.resizable = data.resizable;
    },
};

const featsContext = {
    canOperateOn: function(component) {
        return ((!component.owner || component.owner === featsContext.playerName)
             && !featsContext.isPlayerObserver);
    }
};
function setFeatsContext(playerName, isPlayerObserver, tableData) {
    featsContext.playerName = playerName;
    featsContext.isPlayerObserver = isPlayerObserver;
    featsContext.tableData = tableData;
}

export {setFeatsContext, draggability, flippability, resizability};