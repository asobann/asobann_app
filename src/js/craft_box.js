import {el, mount, unmount} from "redom";
import {_} from "./i18n.js";

const CRAFT_BOX_CONNECTOR_DEFINITION = {
    addNewComponentWithinKit: null,
    pushNewKitAndComponents: null,
};

class CraftBoxConnector {
    constructor(connector) {
        for (const key in CRAFT_BOX_CONNECTOR_DEFINITION) {
            if (!connector[key]) {
                console.debug(`CaftBoxConnector connector must have ${key}`);
            }
        }
        this.connector = connector;
    }
}

class CraftBox {
    constructor(connector) {
        this.connector = connector.connector;
    }

    open() {
        const kitData = getCraftBoxKit();
        const kitId = 'xxxxxxxxxxxx'.replace(/[x]/g, function (/*c*/) {
            return (Math.random() * 16 | 0).toString(16);
        });

        this.connector.addNewComponentWithinKit(
            {
                "boxOfComponents": true,
                "cardistry": [
                    "collect"
                ],
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
        this.connector.addNewComponentWithinKit(
            {
                "color": "cyan",
                "draggable": true,
                "flippable": false,
                "height": "100px",
                "left": "60px",
                "name": "Export Table",
                "ownable": false,
                "resizable": true,
                "text": "Export Table",
                "textColor": "black",
                "craftBoxFunction": "export table",
                "top": "0px",
                "width": "125px",
                "zIndex": 100
            }, kitId);
        this.connector.addNewComponentWithinKit(
            {
                "color": "cyan",
                "draggable": true,
                "flippable": false,
                "height": "100px",
                "left": "195px",
                "name": "Upload Kit",
                "ownable": false,
                "resizable": true,
                "text": "Upload Kit",
                "textColor": "black",
                "craftBoxFunction": "upload kit",
                "top": "0px",
                "width": "125px",
                "zIndex": 99
            }, kitId);
        this.connector.pushNewKitAndComponents({
                kit: { name: kitData.kit.name, kitId: kitId },
            }, {}
        );
    }
}

const craft_box = {
    map: {
        'export table': "exportTable",
        'upload kit': "uploadKit",
    },
    use: (funcationName) => {
        craft_box[craft_box.map[funcationName]]();
    },
    exportTable: function () {
        location.assign("/export?tablename=" + craft_box.context.tablename);
    },
    uploadKit: function () {
        const background = el('div.modal_background');
        mount(document.body, background);
        const contents = el('div.modal_contents');
        mount(background, contents);
        const form = el('form', { method: 'POST', action: '/kits/create', enctype: 'multipart/form-data' },
            [
                el('label', { 'for': 'data' }, _('Kit JSON File')),
                el('input', { 'type': 'file', 'name': 'data', 'id': 'data' }),
                el('br'),
                el('label', { 'for': 'images' }, _('Image Files')),
                el('input', { 'type': 'file', 'name': 'images', 'id': 'images', 'multiple': true }),
                el('br'),
                el('button', { onclick: submitUploadKitForm, id: 'upload' }, _('Upload Kit')),
                el('br'),
                el('button', { onclick: cancelForm, id: 'cancel' }, _('Cancel')),
            ]);
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
    setTableName: function (tablename) {
        craft_box.context.tablename = tablename;
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
            "name": "CraftBox",
            "usedComponentNames": ["Export Table", "CraftBox", "Upload Kit"],
            "width": "400px"
        }
    }
    return kit;
}


export {craft_box, getCraftBoxKit, CraftBox, CraftBoxConnector};
