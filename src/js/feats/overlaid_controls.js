import {Level} from "../table";
import {el, mount, setStyle, unmount} from "redom";
import {_} from "../i18n";
import {addFeat, featsContext} from "../feat";

const editability = {
    install: function (component, data) {
        if (!editability.isEnabled(component, data)) {
            return;
        }

        function isEditingPermitted() {
            return component.editable && featsContext.canOperateOn(component);
        }


        function startEditing(component) {
            data.editing = true;
            let textareaEl;
            // TODO keep element for reuse; delete when uninstall()ed
            const formEl = el('div.note_editor', [
                textareaEl = el('textarea', { oninput: editing }, data.text),
                el('br', {}, data.text),
                el('div.button_frame', [
                    el('button', { onclick: endEditing }, _('Finish')),
                ])
            ]);
            mount(component.el, formEl);

            function editing() {
                component.applyUserAction(Level.A, () => {
                    component.propagate({ 'text': textareaEl.value });
                });
            }

            function endEditing() {
                component.applyUserAction(Level.A, () => {
                    component.propagate({ 'text': textareaEl.value });
                    unmount(component.el, formEl);
                    data.editing = false;
                });
            }
        }

        overlaid.addOverlayItem(component, {
            createElement: () => {
                const e = el('div.overlay_button', {
                        onclick: () => {
                            startEditing(component);
                        }
                    },
                    [
                        el('img', { src: '/static/images/edit.png' }),
                    ]);
                return e;
            }
        });

        component.el.addEventListener("dblclick", (e) => {
            if (!isEditingPermitted()) {
                return;
            }

            if (data.editing) {
                return;
            }

            if (e.shiftKey) {
                // TODO: temporal workaround for rotatability
                return;
            }

            startEditing(component);
        });

    },
    isEnabled: function (component, data) {
        return data.editable === true;
    },
    receiveData: function (component, data) {
        component.editable = data.editable;
    },
    updateView() {

    },
    uninstall: function (component) {
    },
};


const rotatability = {
    install: function (component, data) {
        if (!rotatability.isEnabled(component, data)) {
            return;
        }

        function isRotationPermitted() {
            return component.rotatable && featsContext.canOperateOn(component);
        }

        function rotate(component) {
            if (!component.rotation) {
                component.rotation = 0;
            }
            component.rotation += 45;
            if (component.rotation >= 360) {
                component.rotation %= 360;
            }
            component.applyUserAction(Level.A, () => {
                component.propagate({
                    'rotation': component.rotation
                });
            });
        }

        overlaid.addOverlayItem(component, {
            createElement: () => {
                const e = el('div.overlay_button', {
                        onclick: () => {
                            rotate(component, data);
                        }
                    },
                    [
                        el('img', { src: '/static/images/rotate.png' }),
                    ]);
                return e;
            }
        });

        component.el.addEventListener("dblclick", (e) => {
            if (!isRotationPermitted()) {
                return;
            }
            if (e.shiftKey) {
                rotate(component);
            }
        });
    },
    isEnabled: function (component, data) {
        return data.rotatable === true;
    },
    receiveData: function (component, data) {
        component.rotatable = data.rotatable;
        component.rotation = data.rotation;
    },
    updateView(component, data) {
        setStyle(component.el, {
            transform: "rotate(" + String(data.rotation) + "deg)",
        });
    },
    uninstall: function (component) {
    },
}


const overlaid = {
    install: function (component, data) {
        if (!overlaid.isEnabled(component, data)) {
            return;
        }
        component.el.addEventListener("mouseover", (e) => {
            component.overlay.select(component, component.overlayItems);
        });
        component.el.addEventListener("mouseout", (e) => {
            component.overlay.notifyMouseIsOut(component, e);
        });
    },
    isEnabled: function (component) {
        return component.overlayItems && component.overlayItems.length > 0;
    },
    receiveData: function () {
    },
    updateView(component, data) {
        if (!component.overlay.isSelected(component)) {
            return;
        }
        component.overlay.show(component.overlayItems);
    },
    uninstall: function (component) {
        delete component.overlayItems;
    },
    addOverlayItem(component, item) {
        if (!component.overlayItems) {
            component.overlayItems = [];
        }
        component.overlayItems.push(item);
    }
};

addFeat(editability);
addFeat(rotatability);
addFeat(overlaid);  // overlaid must be added at the last
