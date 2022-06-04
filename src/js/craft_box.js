import {el, mount, setAttr, setStyle, unmount} from "redom";
import {_, language} from "./i18n.js";

const CRAFT_BOX_KIT_NAME = "asobann/CraftBox"

const CRAFT_BOX_CONNECTOR_DEFINITION = {
    addNewCraftBoxComponent: null,
    pushNewKitAndComponents: null,
    isKitOnTable: null,
    getKitIdByName: null,
    removeKit: null,
};

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
    constructor(tablename, connector) {
        craft_box.context.tablename = tablename;
        this.connector = connector.connector;
    }

    open() {
        const kitData = getCraftBoxKit();
        const kitId = 'xxxxxxxxxxxx'.replace(/[x]/g, function (/*c*/) {
            return (Math.random() * 16 | 0).toString(16);
        });

        this.connector.pushNewKitAndComponents({
            kit: { name: kitData.kit.name, kitId: kitId },
        }, {});
        this.connector.addNewCraftBoxComponent({
            "craftBox": true,
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
        }, kitId);
    }

    close() {
        this.connector.removeKit(this.connector.getKitIdByName(CRAFT_BOX_KIT_NAME));
    }

    isOpen() {
        return this.connector.isKitOnTable(CRAFT_BOX_KIT_NAME);
    }
}

const craft_box = {
    exportTable: function () {
        location.assign("/export?tablename=" + craft_box.context.tablename);
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

const basicCraftBox = {
    install: function (component, data) {
        if(!this.isEnabled(component, data)) {
            return;
        }
        mount(component.el,
            el('div', [
                el("button.component_text#upload_kit", {
                    onclick: () => { craft_box.uploadKit(); }
                }, [_('Upload Kit')])
            ])
        );
        mount(component.el,
            el('div', [
                el("button.component_text#export_table", {
                    onclick: () => { craft_box.exportTable(); }
                }, [_('Export Table')])
            ])
        );
    },
    isEnabled: function (component, data) {
        return data.craftBox === true;
    },
    receiveData(component, data) {
    },
    updateView(component, data) {
    },
    uninstall: function () {
    },
}

const feats = [
    basicCraftBox,
];

export {CraftBox, CraftBoxConnector, feats};
