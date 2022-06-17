import {Level} from "../table";
import {el, mount, setStyle, unmount} from "redom";
import {_} from "../i18n";
import {addFeat, featsContext} from "../feat";

const glued = {
    install: function (component, data) {
        if (!glued.isEnabled(component, data)) {
            return;
        }
        component.gluedComponents = [];
        for(const fragment of data.glued) {
            const fragmentEl = el('div', {'class': 'glued'});
            mount(component.el, fragmentEl);
            component.gluedComponents.push(fragmentEl);
        }
    },
    isEnabled: function (component, data) {
        return data.glued;
    },
    receiveData: function () {
    },
    updateView(component, data) {
        let i = 0;
        for(const fragment of data.glued) {
            const fragmentEl = component.gluedComponents[i];
            setStyle(fragmentEl, {
                left: parseFloat(fragment.left) + "px",
                top: parseFloat(fragment.top) + "px",
                width: parseFloat(fragment.width) + "px",
                height: parseFloat(fragment.height) + "px",
                zIndex: component.zIndex,
            });
            if(fragment.color) {
                setStyle(fragmentEl, {
                    backgroundColor: fragment.color,
                });
            }
            if(component.flippable && component.faceup === false) {
                // Glued fragment is not on the facedown side
                fragmentEl.innerText = '';
            } else {
                fragmentEl.innerText = fragment.text;
            }
            i += 1;
        }
    },
    uninstall: function (component) {
        delete component.gluedComponents;
    },
};

addFeat(glued);
