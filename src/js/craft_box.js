import {el, mount, setAttr, setStyle, unmount} from "redom";
import interact from 'interactjs';
import {_, language} from "./i18n.js";

const CRAFT_BOX_KIT_NAME = "asobann/CraftBox"

const CRAFT_BOX_CONNECTOR_DEFINITION = {
    addNewCraftBoxComponent: null,
    pushNewKitAndComponents: null,
    isKitOnTable: null,
    getKitIdByName: null,
    removeKit: null,
};

const connector = {};

class CraftBoxConnector {
    constructor(connector) {
        for (const key in CRAFT_BOX_CONNECTOR_DEFINITION) {
            if (!connector[key]) {
                console.debug(`CaftBoxConnector connector must have ${key}`);
            }
        }
        for (const key in connector) {
            if (CRAFT_BOX_CONNECTOR_DEFINITION[key] === undefined) {
                console.debug(`CaftBoxConnector has undefined entry ${key}`);
            }
        }
        this.connector = connector;
    }
}

class CraftBox {
    constructor(tablename, connector_) {
        craftBoxActions.context.tablename = tablename;
        Object.assign(connector, connector_.connector);
    }

    open() {
        const kitData = getCraftBoxKit();
        this.kitId = 'xxxxxxxxxxxx'.replace(/[x]/g, function (/*c*/) {
            return (Math.random() * 16 | 0).toString(16);
        });

        connector.pushNewKitAndComponents({
            kit: { name: kitData.kit.name, kitId: this.kitId },
        }, {});
        connector.addNewCraftBoxComponent({
            "craftBox": 'main',
            "boxOfComponents": true,
            "color": "darkgray",
            "draggable": true,
            "flippable": false,
            "handArea": false,
            "height": "300px",
            "left": "0px",
            "name": "CraftBox",
            "ownable": false,
            "resizable": true,
            "rollable": false,
            "showImage": false,
            "text": "CraftBox",
            "text_ja": "道具箱",
            "top": "0px",
            "traylike": true,
            "width": "460px",
            "zIndex": 1
        }, this.kitId);
    }

    close() {
        connector.removeKit(connector.getKitIdByName(CRAFT_BOX_KIT_NAME));
    }

    isOpen() {
        return connector.isKitOnTable(CRAFT_BOX_KIT_NAME);
    }

}

const craftBoxActions = {
    exportTable: function () {
        location.assign("/export?tablename=" + craftBoxActions.context.tablename);
    },
    uploadKit: function () {
        const background = el('div.modal_background');
        mount(document.body, background);
        const contents = el('div.modal_contents');
        mount(background, contents);
        const form = el('form', {
            method: 'POST',
            action: '/kits/create',
            enctype: 'multipart/form-data'
        }, [el('label', { 'for': 'data' }, _('Kit JSON File')), el('input', {
            'type': 'file',
            'name': 'data',
            'id': 'data'
        }), el('br'), el('label', { 'for': 'images' }, _('Image Files')), el('input', {
            'type': 'file',
            'name': 'images',
            'id': 'images',
            'multiple': true
        }), el('br'), el('button', {
            onclick: submitUploadKitForm,
            id: 'upload'
        }, _('Upload Kit')), el('br'), el('button', { onclick: cancelForm, id: 'cancel' }, _('Cancel')),]);
        mount(contents, form);


        function submitUploadKitForm() {
            (async () => {
                const imageUrls = {};
                const imageFiles = document.getElementById('images').files;
                for (let file of imageFiles) {
                    const formData = new FormData();
                    formData.append('image', file);
                    const res = await fetch('/dummy', { method: 'POST', body: formData });
                    const response = await res.json();
                    imageUrls[file.name] = response['imageUrl'];
                }

                const jsonFile = document.getElementById('data').files[0];
                if (!jsonFile) {
                    alert('Upload Failed: please select Kit JSON File');
                    unmount(document.body, background);
                    return;
                }
                const reader = new FileReader();
                reader.onloadend = () => {
                    (async () => {
                        const kitData = JSON.parse(reader.result);
                        for (const cmp of kitData['components']) {
                            for (const key of ['image', 'faceupImage', 'facedownImage']) {
                                if (!cmp.hasOwnProperty(key)) {
                                    continue;
                                }
                                if (imageUrls.hasOwnProperty(cmp[key])) {
                                    cmp[key] = imageUrls[cmp[key]];
                                }
                            }
                        }

                        const jsonFormData = new FormData();
                        jsonFormData.append('data', new File([JSON.stringify(kitData)], 'kit.json'));
                        const res = await fetch('/kits/create', { method: 'POST', body: jsonFormData });
                        const response = await res.json();
                        console.log(response);

                        if (response.result === 'success') {
                            alert('Upload Success!');
                        } else {
                            alert('Upload Failed: \n' + response.error);
                        }
                        unmount(document.body, background);
                    })();
                }
                reader.onerror = (e) => {
                    alert('Upload Failed: \n' + JSON.stringify(e));
                    unmount(document.body, background);
                }
                reader.readAsText(jsonFile);
            })();
            return false;
        }

        function cancelForm() {
            unmount(document.body, background);
            return false;
        }
    },
    openKitBox: function () {
        connector.addNewCraftBoxComponent({
            "craftBox": 'kit_box',
            "boxOfComponents": false,
            "color": "lightblue",
            "draggable": true,
            "flippable": false,
            "handArea": false,
            "height": "300px",
            "left": "0px",
            "name": "KitBox",
            "ownable": false,
            "resizable": true,
            "rollable": false,
            "showImage": false,
            "top": "0px",
            "traylike": true,
            "width": "460px",
            "zIndex": 1
        }, this.kitId);

    },
    context: {}
};

function getCraftBoxKit() {
    const kit = {
        "kit": {
            "boxAndComponents": { "CraftBox": ["Export Table", "Upload Kit"] },
            "height": "300px",
            "label": "CraftBox",
            "label_ja": "\u9053\u5177\u7bb1",
            "name": CRAFT_BOX_KIT_NAME,
            "usedComponentNames": ["Export Table", "CraftBox", "Upload Kit"],
            "width": "400px"
        }
    }
    return kit;
}

function button(id, onClick, text) {
    return el('div', [
        el("button.component_text#" + id, {
            onclick: onClick
        }, [text])
    ]);
}

const mainCraftBox = {
    install: function (component, data) {
        if (!this.isEnabled(component, data)) {
            return;
        }
        mount(component.el,
            button(
                "upload_kit",
                craftBoxActions.uploadKit,
                _('Upload Kit')));
        mount(component.el,
            button(
                "export_table",
                craftBoxActions.exportTable,
                _('Export Table')));
        mount(component.el,
            button(
                "open_kit_box",
                craftBoxActions.openKitBox,
                _('Open Kit Box')));
    },
    isEnabled: function (component, data) {
        return data.craftBox === 'main';
    },
    receiveData(component, data) {
    },
    updateView(component, data) {
    },
    uninstall: function () {
    },
}

const kitCraftBox = {
    install: function (component, data) {
        if (!this.isEnabled(component, data)) {
            return;
        }
        mount(component.el, this.bodyEl = el('div', { id: 'kit_box_body' }));
        mount(this.bodyEl,
            button(
                "create_new",
                () => {
                    const emptyKit = {
                        'kit': {},
                        'components': [],
                    }
                    this.kitJsonEl.value = JSON.stringify(emptyKit, null, 4);
                },
                _('Create Kit Box')))
        mount(this.bodyEl, this.kitJsonEl = el('textarea.kit_json#kit_json', {}, '{}'));
    },
    isEnabled: function (component, data) {
        return data.craftBox === 'kit_box';
    },
    receiveData(component, data) {
    },
    updateView(component, data) {
    },
    uninstall: function () {
    },
}

const feats = [
    mainCraftBox,
    kitCraftBox,
];

export {CraftBox, CraftBoxConnector, feats};
