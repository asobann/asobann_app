import {el, mount, setAttr} from "./redom.es.js";
// import interact from './interact.js'

const draggability = {
    add: function (component) {
        function isDraggingPermitted() {
            return component.draggable && (!component.owner || component.owner === draggability.player);
        }

        interact(component.el).draggable({
            listeners: {
                move(event) {
                    if (!isDraggingPermitted()) {
                        return;
                    }
                    let top = parseFloat(component.el.style.top) + event.dy;
                    let left = parseFloat(component.el.style.left) + event.dx;
                    component.pushUpdate({ top: top + "px", left: left + "px" });
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
                            component.pushUpdate({ owner: component.owner });
                        }
                    } else {
                        if (component.owner) {
                            component.owner = null;
                            component.pushUpdate({ owner: component.owner });
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


            for (const target of draggability.tableData) {
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
    setContext(player, tableData) {
        this.player = player;
        this.tableData = tableData;
    }
};

const flippability = {
    add: function (component) {
        function disabled() {
            return !component.flippable;
        }

        component.el.addEventListener("dblclick", () => {
            if (disabled()) {
                return;
            }
            let diff = {};
            if (component.owner && component.owner !== flippability.player) {
                return;
            }
            if (component.faceup) {
                diff.faceup = component.faceup = false;
                setAttr(component.image, { src: component.facedownImage });
            } else {
                diff.faceup = component.faceup = true;
                setAttr(component.image, { src: component.faceupImage });
            }
            component.pushUpdate(diff);
        });
    },
    enabled: function (component, data) {
        return data.flippable === true;
    },
    update: function (component, data) {
        component.flippable = data.flippable;
        component.faceupImage = data.faceupImage;
        component.facedownImage = data.facedownImage;
        component.faceup = data.faceup;
        if (component.faceup) {
            if (!component.owner || component.owner === flippability.player) {
                setAttr(component.image, { src: component.faceupImage });
            } else {
                setAttr(component.image, { src: component.facedownImage });
            }
        } else {
            setAttr(component.image, { src: component.facedownImage });
        }
        component.faceup = data.faceup;

    },
    setContext(player, tableData) {
        this.player = player;
        this.tableData = tableData;
    }
};


const resizability = {
    add: function (component) {
        function isResizingPermitted() {
            return component.resizable && (!component.owner || component.owner === resizability.player);
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
                component.pushUpdate({ top: top, left: left, width: width, height: height });
            },
        })
    },
    enabled: function (component, data) {
        return data.resizable === true;
    },
    update: function (component, data) {
        component.resizable = data.resizable;
    },
    setContext(player, tableData) {
        this.player = player;
        this.tableData = tableData;
    }
};

export {draggability, flippability, resizability};