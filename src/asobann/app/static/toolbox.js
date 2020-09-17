import {el, mount, unmount} from "./redom.es.js";
import {_} from "./i18n.js";

const toolbox = {
    map: {
        'export table': "exportTable",
        'upload kit': "uploadKit",
    },
    use: (funcationName) => {
        toolbox[toolbox.map[funcationName]]();
    },
    exportTable: function () {
        location.assign("/export?tablename=" + tablename);
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
                const reader = new FileReader();
                reader.onloadend = () => {
                    (async () => {
                        const kitData = JSON.parse(reader.result);
                        for(const cmp of kitData['components']) {
                            for(const key of ['image', 'faceupImage', 'facedownImage']) {
                                if(!cmp.hasOwnProperty(key)) {
                                    continue;
                                }
                                if(imageUrls.hasOwnProperty(cmp[key])) {
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
};

export {toolbox};
