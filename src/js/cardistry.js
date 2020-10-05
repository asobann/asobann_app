import {_} from "./i18n.js";

function countProperties(obj) {
    let count = 0;
    for (const prop in obj) {
        if (obj.hasOwnProperty(prop)) {
            count += 1;
        }
    }
    return count;
}

const spreadOut = {
    name: 'spread out',
    label: _('Spread Out'),
    execute: function (component, featsContext) {
        if (!component.onTray) {
            return;
        }

        // Spread cards in rows and columns in the order of current zIndex
        // Cards go left to right and then top to bottom
        // Collecting does the reverse
        const spreading = [];
        for (const cmpId in component.onTray) {
            // noinspection JSUnfilteredForInLoop
            spreading.push(cmpId);
        }
        spreading.sort((id1, id2) => {
            return featsContext.table.componentsOnTable[id2].zIndex - featsContext.table.componentsOnTable[id1].zIndex;
        });

        const newPositions = [];
        let left = 0;
        let maxHeight = 0;
        for (const cmpId of spreading) {
            const cmp = featsContext.table.componentsOnTable[cmpId];
            newPositions.push({ left: left, component: cmp });
            left += parseFloat(cmp.el.style.width) + 16;
            if (maxHeight < parseFloat(cmp.el.style.height)) {
                maxHeight = parseFloat(cmp.el.style.height);
            }
        }
        const maxWidth = Math.ceil(left / Math.sqrt(left / (2 * maxHeight)));
        let top = 0;
        left = 0;
        let localMaxHeight = 0;
        for (const pos of newPositions) {
            if (pos.left - left > maxWidth) {
                top += localMaxHeight + 16;
                left = pos.left;
                localMaxHeight = 0;
            }
            pos.top = top;
            pos.left -= left;
            if (localMaxHeight < parseFloat(pos.component.el.style.height)) {
                localMaxHeight = parseFloat(pos.component.el.style.height);
            }
        }
        const rect = featsContext.table.findEmptySpace(maxWidth, top + localMaxHeight);
        featsContext.table.consolidatePropagation(() => {
            for (const pos of newPositions) {
                featsContext.fireEvent(pos.component, featsContext.events.onPositionChanged,
                    {
                        top: pos.top + rect.top,
                        left: pos.left + rect.left,
                        height: parseFloat(pos.component.el.style.height),
                        width: parseFloat(pos.component.el.style.width),
                    });
            }
        });
        featsContext.table.updateView();
    },
    onComponentUpdate: function () {
    },
    isEnabled: function (component, /*featsContext*/) {
        return component.onTray && countProperties(component.onTray) > 0;
    }
};

const collect = {
    name: 'collect',
    label: _('Collect Components'),
    execute: function (component, featsContext, collectComponentsInHand) {
        if (!component.componentsInBox) {
            return;
        }

        // Collect cards left to right then top to bottom
        // and then stack up with modifying zIndex
        // Spreading out does the reverse
        featsContext.table.consolidatePropagation(() => {
            let top = parseFloat(component.el.style.top);
            let left = parseFloat(component.el.style.left) + 100;
            let componentCount = 0;
            for (const cmpId in component.componentsInBox) {
                componentCount += 1;
            }
            let lastZIndex = featsContext.table.getNextZIndex() + componentCount;

            const collecting = [];
            for (const cmpId in component.componentsInBox) {
                // noinspection JSUnfilteredForInLoop
                collecting.push(cmpId);
            }
            collecting.sort((id1, id2) => {
                const left1 = parseFloat(featsContext.table.componentsOnTable[id1].el.style.left);
                const top1 = parseFloat(featsContext.table.componentsOnTable[id1].el.style.top);
                const left2 = parseFloat(featsContext.table.componentsOnTable[id2].el.style.left);
                const top2 = parseFloat(featsContext.table.componentsOnTable[id2].el.style.top);
                if (top1 < top2 || (top1 === top2 && left1 < left2)) {
                    return -1;
                } else if (top2 < top1 || top1 === top2 && left2 < left1) {
                    return 1;
                }
                return 0;
            });
            for (const cmpId of collecting) {
                // noinspection JSUnfilteredForInLoop
                const cmp = featsContext.table.componentsOnTable[cmpId];
                if (cmp.isStowed) {
                    continue;
                }
                if (cmp.owner) {
                    if (collectComponentsInHand === undefined) {
                        collectComponentsInHand = window.confirm(_("Do you want to collect even in-hand components?"));
                    }
                    if (!collectComponentsInHand) {
                        continue;
                    }
                }
                featsContext.fireEvent(cmp, featsContext.events.onPositionChanged,
                    {
                        top: top,
                        left: left,
                        height: parseFloat(cmp.el.style.height),
                        width: parseFloat(cmp.el.style.width),
                        moving: false,
                    });
                cmp.propagate({ zIndex: lastZIndex });
                top += 1;
                left += 1;
                lastZIndex -= 1;
            }
        });
        featsContext.table.updateView();
    },
    onComponentUpdate: function (component, componentData) {
        component.componentsInBox = componentData.componentsInBox;
    },
    isEnabled: function (component, /*featsContext*/) {
        return component.onTray && component.componentsInBox &&
            countProperties(component.onTray) !== countProperties(component.componentsInBox);
    }
};

const shuffle = {
    name: 'shuffle',
    label: _('Shuffle'),
    execute: function (component, featsContext) {
        if (!component.onTray || !component.componentsInBox) {
            return;
        }

        const shuffling = [];
        for (const componentId in component.onTray) {
            // noinspection JSUnfilteredForInLoop
            shuffling.push(componentId);
        }

        let top = parseFloat(component.el.style.top);
        let left = parseFloat(component.el.style.left) + 100;
        let lastZIndex = featsContext.table.getNextZIndex() + shuffling.length;
        featsContext.table.consolidatePropagation(() => {
            while (shuffling.length > 0) {
                const idx = Math.floor(Math.random() * shuffling.length);
                const nextComponentId = shuffling.splice(idx, 1)[0];
                const cmp = featsContext.table.componentsOnTable[nextComponentId];

                featsContext.fireEvent(cmp, featsContext.events.onPositionChanged,
                    {
                        top: top,
                        left: left,
                        height: parseFloat(cmp.el.style.height),
                        width: parseFloat(cmp.el.style.width),
                        moving: false,
                    });
                cmp.propagate({ zIndex: lastZIndex });
                top += 1;
                left += 1;
                lastZIndex -= 1;
            }
        });
        featsContext.table.updateView();
    },
    onComponentUpdate: function (component, componentData) {
        component.componentsInBox = componentData.componentsInBox;
    },
    isEnabled: function (component, /*featsContext*/) {
        return component.onTray && countProperties(component.onTray) > 0;
    }
};

const flipAll = {
    name: 'flip all',
    label: _('face up / down'),
    execute: function (component, featsContext) {
        if (!component.onTray) {
            return;
        }
        let allFaceDown = true;

        for (const cmpId in component.onTray) {
            // noinspection JSUnfilteredForInLoop
            const cmp = featsContext.table.componentsOnTable[cmpId];
            if (cmp.flippable && cmp.faceup) {
                allFaceDown = false;
                break;
            }
        }

        featsContext.table.consolidatePropagation(() => {
            for (const cmpId in component.onTray) {
                // noinspection JSUnfilteredForInLoop
                const cmp = featsContext.table.componentsOnTable[cmpId];
                if (allFaceDown) {
                    // make all face up
                    if (!cmp.flippable) {
                        continue;
                    }
                    if (!cmp.faceup) {
                        cmp.propagate({ faceup: true });
                    }
                } else {
                    // make all face down
                    if (!cmp.flippable) {
                        continue;
                    }
                    if (cmp.faceup) {
                        cmp.propagate({ faceup: false });
                    }
                }
            }
            featsContext.table.updateView();
        });
    },
    onComponentUpdate: function (component, componentData) {
        component.componentsInBox = componentData.componentsInBox;
    },
    isEnabled: function (component, /*featsContext*/) {
        return component.onTray && countProperties(component.onTray) > 0;
    }
};

const collectInMess = {
    name: 'collect in mess',
    label: _('Collect Components'),
    execute: function (component, featsContext) {
        if (!component.componentsInBox) {
            return;
        }

        // Collect components into this box
        // Position randomly
        featsContext.table.consolidatePropagation(() => {
            let collectComponentsInHand = undefined;

            let placementAreaTop = parseFloat(component.el.style.top);
            let placementAreaLeft = parseFloat(component.el.style.left);
            let placementAreaHeight = parseFloat(component.el.style.height);
            let placementAreaWidth = parseFloat(component.el.style.width);

            for (const cmpId in component.componentsInBox) {
                // noinspection JSUnfilteredForInLoop
                const cmp = featsContext.table.componentsOnTable[cmpId];
                if (cmp.isStowed) {
                    continue;
                }
                if (cmp.owner) {
                    if (collectComponentsInHand === undefined) {
                        collectComponentsInHand = window.confirm(_("Do you want to collect even in-hand components?"));
                    }
                    if (!collectComponentsInHand) {
                        continue;
                    }
                }
                featsContext.fireEvent(cmp, featsContext.events.onPositionChanged,
                    {
                        top: Math.floor(
                            placementAreaTop +
                            Math.random() * (placementAreaHeight - parseFloat(cmp.el.style.height) - 1)),
                        left: Math.floor(
                            placementAreaLeft +
                            Math.random() * (placementAreaWidth - parseFloat(cmp.el.style.width) - 1)),
                        height: parseFloat(cmp.el.style.height),
                        width: parseFloat(cmp.el.style.width),
                        moving: false,
                    });
            }
        });
        featsContext.table.updateView();
    },
    onComponentUpdate: function (component, componentData) {
        component.componentsInBox = componentData.componentsInBox;
    },
    isEnabled: function (component, /*featsContext*/) {
        return component.onTray && component.componentsInBox &&
            countProperties(component.onTray) !== countProperties(component.componentsInBox);
    }
};
const allCardistry = [spreadOut, collect, shuffle, flipAll, collectInMess];
export {allCardistry};