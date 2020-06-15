function doSpreadOut(component, featsContext) {
    if (!component.onTray) {
        return;
    }

    const spread = [];
    let left = 0;
    let maxHeight = 0;
    for (const cmpId in component.onTray) {
        const cmp = featsContext.table.componentsOnTable[cmpId];
        spread.push({ left: left, component: cmp });
        left += parseFloat(cmp.el.style.width) + 16;
        if (maxHeight < parseFloat(cmp.el.style.height)) {
            maxHeight = parseFloat(cmp.el.style.height);
        }
    }
    const maxWidth = Math.ceil(left / Math.sqrt(left / (2 * maxHeight)));
    let top = 0;
    left = 0;
    let localMaxHeight = 0;
    for (const pos of spread) {
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
        for (const pos of spread) {
            featsContext.fireEvent(pos.component, featsContext.events.onPositionChanged,
                {
                    top: pos.top + rect.top,
                    left: pos.left + rect.left,
                    height: parseFloat(pos.component.el.style.height),
                    width: parseFloat(pos.component.el.style.width),
                });
        }
    });
}

export {doSpreadOut};