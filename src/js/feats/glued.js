import {Level} from "../table";
import {el, mount, setStyle, unmount} from "redom";
import {_} from "../i18n";
import {addFeat, featsContext} from "../feat";

// Glued feat is used to put (glue) simple fragments together on a component.
// Glued fragments are only on faceup side (current limitation.)
// Component with glued feat is defined as below:
// "components": [
// {
//     "name": "Card 01",
//     ...
//     "glued": [
//        {
//            "top": "5px",
//            "left": "27px",
//            "height": "14px",
//            "width": "12px",
//            "text": "Text 1"
//        },
//         {
//             "top": "5px",
//             "left": "56px",
//             "height": "14px",
//             "width": "12px",
//             "text": "Text 2"
//         },
//      ],
//     ...
//
// Glued fragments are text only (current limitation.)

const glued = {
    install: function (component, data) {
        if (!glued.isEnabled(component, data)) {
            return;
        }
        component.gluedComponents = [];
        for (const fragment of data.glued) {
            const fragmentEl = el('div', { 'class': 'glued' });
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
        for (const fragment of data.glued) {
            const fragmentEl = component.gluedComponents[i];
            if (shouldShowFaceup()) {
                setStyle(fragmentEl, {
                    display: null,
                });
                setStyle(fragmentEl, {
                    left: parseFloat(fragment.left) + "px",
                    top: parseFloat(fragment.top) + "px",
                    width: parseFloat(fragment.width) + "px",
                    height: parseFloat(fragment.height) + "px",
                    zIndex: component.zIndex,
                });
                if (fragment.textColor) {
                    setStyle(fragmentEl, {
                        color: fragment.textColor,
                    });
                }
                if (fragment.color) {
                    setStyle(fragmentEl, {
                        backgroundColor: fragment.color,
                    });
                }
                fragmentEl.innerText = fragment.text;
            } else {
                // Glued fragment is not on the facedown side
                setStyle(fragmentEl, {
                    display: 'none',
                });
            }
            i += 1;
        }

        function shouldShowFaceup() {
            return !component.flippable || (component.faceup && (isPublic() || isMyCard()));
        }

        function isPublic() {
            return !component.owner;
        }

        function isMyCard() {
            return component.owner === featsContext.getPlayerName();
        }
    },
    uninstall: function (component) {
        delete component.gluedComponents;
    },
};

addFeat(glued);
