import {Level} from "../table";
import {el, mount, setAttr, setStyle, unmount} from "redom";
import {_} from "../i18n";
import {addFeat, featsContext} from "../feat";

const counter = {
    install: function (component, data) {
        if (!data.counter) {
            return;
        }

        setAttr(component.el, { className: component.el.getAttribute('class') + " counter_component" });

        if (!data.hasOwnProperty("counterValue")) {
            data.counterValue = 0;
        }
        const counterValue = data.counterValue;
        component.el.appendChild(
            el('div.counter', [
                el('div.valueContainer', [
                    component.valueEl = el('div.counterValue', {}, counterValue)
                ]),
                el('div.buttons', [
                    el('div.button', [
                        el('button#subTen', {
                            onclick: (() => {
                                count((v) => v - 10)
                            })
                        }, '-10'),
                    ]),
                    el('div.button', [
                        el('button#subOne', {
                            onclick: (() => {
                                count((v) => v - 1)
                            })
                        }, '-1'),
                    ]),
                    el('div.button', [
                        el('button#addOne', {
                            onclick: (() => {
                                count((v) => v + 1)
                            })
                        }, '+1'),
                    ]),
                    el('div.button', [
                        el('button#addTen', {
                            onclick: (() => {
                                count((v) => v + 10)
                            })
                        }, '+10'),
                    ]),
                ]),
                el('div.buttons', [
                    el('div.button.reset', [
                        el('button.reset#reset', {
                            onclick: (() => {
                                count((/* v */) => 0)
                            })
                        }, 'RESET'),
                    ]),
                ]),
            ])
        );

        function count(fn) {
            component.applyUserAction(Level.A, () => {
                if (!data.hasOwnProperty("counterValue")) {
                    data.counterValue = 0;
                }
                const counterValue = data.counterValue;
                const newValue = fn(counterValue);
                data.counterValue = component.valueEl.innerText = newValue;
                component.propagate({ counterValue: newValue });
            });
        }
    },
    isEnabled: function (component, data) {
        return data.counter === true;
    },
    receiveData() {

    },
    updateView: function (component, componentData) {
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

addFeat(counter);
