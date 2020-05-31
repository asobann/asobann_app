import {el, list, mount, setAttr, setStyle, unmount} from "./redom.es.js";
import {joinTable} from "./sync_table.js";
import {names} from "./names.js";

function baseUrl() {
    return location.protocol + "//" + location.hostname + (location.port ? ":" + location.port : "") + "/";
}

function getPlaceholderName() {
    return names[Math.floor(Math.random() * names.length)];
}

const CONNECTOR_TEMPLATE = {
    tablename: null,
    getTableData: null,
    fireMenuUpdate: null,
    getPlayerName: null,
    addNewComponent: null,
    removeComponent: null,
    removeHandArea: null,
    isPlayerObserver: null,
    isTherePlayersHandArea: null,
};

class Menu {
    constructor(connector) {
        for (const key in CONNECTOR_TEMPLATE) {
            if (!connector[key]) {
                console.debug(`menu connector must have ${key}`);
            }
        }
        const self = this;
        this.connector = connector;
        this.playerStatusEl = el("span", this.connector.getPlayerName());

        this.el = el("div.menu",
            [
                el("div.title", "asobann 遊盤"),
                el("div", ["you are ", this.playerStatusEl]),
                this.joinItem = el("div.menuitem", [
                    "enter name and join",
                    this.playerNameInput = el("input#player_name", { value: getPlaceholderName() }),
                    el("button#join_button", {
                        onclick: () => joinTable(this.playerNameInput.value, false)
                    }, "Join!"),
                    el("div", {
                        style: {
                            position: 'absolute',
                            top: '10%',
                            left: '30%',
                            width: '40%',
                            textAlign: 'center',
                            fontSize: '200%',
                            color: 'lightgreen',
                        }
                    }, "You are observing.  Join to play!  On the left side, enter name and click Join!"),
                ], { style: { display: 'none' } }),
                this.addRemoveComponentItem = el("div.menuitem#add_remove_component",
                    el("a", { href: "", onclick: showAddRemoveKitsMenu }, "Add / Remove Kits")),
                this.addHandAreaItem = el("div.menuitem#add_hand_area",
                    el("a", { href: "", onclick: addHandArea }, "Add Hand Area")),
                this.removeHandAreaItem = el("div.menuitem#remove_hand_area",
                    el("a", { href: "", onclick: this.connector.removeHandArea }, "Remove Hand Area")),
                el("div.menuitem", [
                    "Share URL for invitation",
                    el("input#invitation_url", {
                        value: location.href,
                        readonly: true,
                        onclick: (e) => {
                            e.target.select();
                        }
                    }),
                    el("a#copy_invitation_url", {
                        href: "", onclick: () => {
                            document.querySelector('#invitation_url').select();
                            document.execCommand('copy');
                            return false;
                        }
                    }, "copy"),
                ]),
                el("div.menuitem",
                    el("a", { href: "/export?tablename=" + this.connector.tablename }, "Export Table")),
                el("div.menuitem#import_table",
                    el("a", { href: "", onclick: showImport }, "Import Table")),
            ],
        );

        function addHandArea() {
            const newComponent = {
                name: self.connector.getPlayerName() + "'s hand",
                text: self.connector.getPlayerName() + "'s hand",
                handArea: true,
                owner: self.connector.getPlayerName(),
                top: "0px",
                left: "0px",
                width: "320px",
                height: "60px",
                draggable: true,
                flippable: false,
                resizable: true,
                ownable: false,
                traylike: true,
                zIndex: 0,
            };
            self.connector.addNewComponent(newComponent);
            return false;
        }

        function showImport() {
            const importEl = el("div",
                el("form", { action: "/import", method: "POST", enctype: "multipart/form-data" },
                    [
                        el("input", { type: "hidden", value: self.connector.tablename, name: "tablename" }),
                        el("input#file", { type: "file", name: "data" }),
                        el("input#submit", { type: "submit" }),
                        el("button", { onclick: hideImport }, "Cancel"),
                    ]
                )
            );
            mount(self.el, importEl);

            function hideImport() {
                unmount(self.el, importEl);
            }

            return false;
        }

        function showAddRemoveKitsMenu() {
            self.componentMenu = createAddRemoveKitsMenu(self.addRemoveComponentItem, self.connector);
            mount(self.addRemoveComponentItem, self.componentMenu.el);
            connector.fireMenuUpdate();
            return false;
        }
    }

    update(tableData) {
        if (this.connector.isPlayerObserver()) {
            setStyle(this.joinItem, { display: null });
            this.playerStatusEl.innerText = "observing";
            setStyle(this.addHandAreaItem, { display: 'none' });
            setStyle(this.removeHandAreaItem, { display: 'none' });
            return;
        }

        setStyle(this.joinItem, { display: 'none' });
        if (tableData.playerName) {
            this.playerStatusEl.innerText = tableData.playerName;
        }

        if (this.connector.isTherePlayersHandArea(this.connector.getPlayerName())) {
            setStyle(this.addHandAreaItem, { display: 'none' });
            setStyle(this.removeHandAreaItem, { display: null });
        } else {
            setStyle(this.addHandAreaItem, { display: null });
            setStyle(this.removeHandAreaItem, { display: 'none' });
        }

        if (this.componentMenu) {
            this.componentMenu.update(tableData);
        }
    }
}


function createAddRemoveKitsMenu(parent, connector) {
    class KitsMenuItem {
        constructor(props) {
            this.el = el("div.item", [
                this.nameEl = el("div"),
                this.countEl = el("div"),
                this.addEl = el("a.add_new_component", {
                    href: '',
                }, "Add"),
                this.removeEl = el("a.remove_component", {
                    href: '',
                }, "Remove"),
            ]);
        }

        update(kitData, index, items, context) {
            const self = this;
            setAttr(self.el, { 'data-kit-name': kitData.kit.name });
            self.nameEl.innerText = kitData.kit.name;
            updateNumberOnTable();
            self.component = kitData.component;
            self.addEl.onclick = () => {
                addKitOnTable();
                return false;
            };
            this.removeEl.onclick = () => {
                removeOneKitFromTable();
                return false;
            };

            function addKitOnTable() {
                const newComponent = Object.assign({}, kitData.component);
                if(kitData.component.onAdd) {
                    const s = '"use strict"; return ' + kitData.component.onAdd;
                    const f = Function(s);
                    f()(newComponent);
                }
                connector.addNewComponent(newComponent);
            }

            function removeOneKitFromTable() {
                for (let i = connector.getTableData().components.length - 1; i >= 0; i -= 1) {
                    const cmp = connector.getTableData().components[i];
                    if (cmp.name === kitData.component.name) {
                        connector.removeComponent(i);
                        break;
                    }
                }
            }

            function updateNumberOnTable() {
                let numberOnTable = 0;
                for (const cmp of connector.getTableData().components) {
                    if (cmp.name === kitData.kit.name) {
                        numberOnTable += 1;
                    }
                }
                if (numberOnTable > 0) {
                    self.countEl.innerText = `${numberOnTable} on the table`;
                    self.removeEl.style.display = null;
                } else {
                    self.countEl.innerText = '';
                    self.removeEl.style.display = 'none';
                }
            }
        }
    }

    class KitsMenu {
        constructor(props) {
            const REASONABLY_BIG_ZINDEX_VALUE = 99999999;
            const self = this;
            this.kitsMenuItemList = list("div", KitsMenuItem);
            this.el = el("div.kit_selection_container", { style: { zIndex: REASONABLY_BIG_ZINDEX_VALUE } },
                [
                    el("div.kit_selection", [
                        el("button", { onclick: hideAddRemoveKitsMenu }, "Done"),
                        this.kitsMenuItemList.el,
                        el("button", { onclick: hideAddRemoveKitsMenu }, "Done"),
                    ])
                ]
            );
            loadKitList();

            async function loadKitList() {
                const url = baseUrl() + "kits";
                const response = await fetch(url);
                const kits = (await response).json();
                self.kitsList = await kits;
                self.kitsMenuItemList.update(self.kitsList);
            }

            function hideAddRemoveKitsMenu() {
                unmount(parent, self.el);
            }
        }

        update(tableData, context) {
            this.kitsMenuItemList.update(this.kitsList, tableData);
        }
    }

    return new KitsMenu();
}

export {Menu};
