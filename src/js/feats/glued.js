import {Level} from "../table";
import {el, mount, setStyle, unmount} from "redom";
import {_} from "../i18n";
import {addFeat, featsContext, shrinkFontSizeToFit} from "../feat";

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
//        {
//            "top": "5px",
//            "left": "56px",
//            "height": "14px",
//            "width": "12px",
//            "image": "path/to/image.png",
//            "text": ""
//        },
//     ],
//     ...
//

const glued = {
    install: function (component, data) {
        if (!glued.isEnabled(component, data)) {
            return;
        }
        component.gluedFragments = [];
        for (const fragment of data.glued) {
            const fragmentEl = el('div', { 'class': 'glued' }, [
                el('div', [el('span.text')])
                ]);
            mount(component.el, fragmentEl);
            component.gluedFragments.push(fragmentEl);
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
            const fragmentEl = component.gluedFragments[i];
            if (featsContext.shouldShowFaceup(component)) {
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
                if(fragment.image) {
                    setStyle(fragmentEl, {
                        'background-image': 'url(' + fragment.image + ')',
                        'background-size': 'cover',
                    });
                } else if (fragment.color) {
                    setStyle(fragmentEl, {
                        backgroundColor: fragment.color,
                    });
                }

                let spanEl = null;
                const elements = [fragmentEl];
                while(elements.length > 0) {
                    const el = elements.shift();
                    if(el.tagName && el.tagName === "SPAN") {
                        spanEl = el;
                        break;
                    }
                    el.childNodes.forEach((v) => elements.push(v));
                }

                if(spanEl) {
                    spanEl.innerText = fragment.text;
                    shrinkFontSizeToFit(spanEl.parentNode, fragmentEl.getBoundingClientRect());
                }
            } else {
                // Glued fragment is not on the facedown side
                setStyle(fragmentEl, {
                    display: 'none',
                });
            }
            i += 1;
        }
    },
    uninstall: function (component) {
        delete component.gluedFragments;
    },
};

addFeat(glued);
