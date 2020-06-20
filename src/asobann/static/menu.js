import {el, list, mount, setAttr, setStyle, unmount} from "./redom.es.js";
import {joinTable} from "./sync_table.js";
import {names} from "./names.js";
import {_, language} from "./i18n.js";

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
    addNewKit: null,
    removeKit: null,
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
                el("div.menuitem.menuheader", [
                    el("div.title", "asobann 遊盤"),
                    el("div", [_("you are "), this.playerStatusEl]),]),
                this.joinItem = el("div.menuitem", [
                    _("enter name and join"),
                    this.playerNameInput = el("input#player_name", { value: getPlaceholderName() }),
                    el("button#join_button", {
                        onclick: () => joinTable(this.playerNameInput.value, false)
                    }, _("Join!")),
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
                    }, _("You are observing.  Join to play!  On the left side, enter name and click Join!")),
                ], { style: { display: 'none' } }),
                this.addRemoveComponentItem = el("div.menuitem#add_remove_component",
                    el("a", { href: "", onclick: showAddRemoveKitsMenu }, _("Add / Remove Kits"))),
                this.addHandAreaItem = el("div.menuitem#add_hand_area",
                    el("a", { href: "", onclick: addHandArea }, _("Add Hand Area"))),
                this.removeHandAreaItem = el("div.menuitem#remove_hand_area",
                    el("a", { href: "", onclick: this.connector.removeHandArea }, _("Remove Hand Area"))),
                el("div.menuitem", [
                    _("Share URL for invitation"),
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
                    }, _("copy")),
                ]),
                el("div.menuitem",
                    el("a", { href: "/export?tablename=" + this.connector.tablename }, _("Export Table"))),
                el("div.menuitem#import_table",
                    el("a", { href: "", onclick: showImport }, _("Import Table"))),
                el("div.menuitem.about",  [
                    el("a", {
                        class: 'about',
                        href: 'https://games.yattom.jp/asobann',
                        target: '_blank'
                    }, _("About asobann")),
                    el("div", { class: 'copyright' }, _("Copyright (C) 2020 Yattom")),
                ])
            ],
        );

        function addHandArea() {
            const newComponent = {
                name: self.connector.getPlayerName() + "'s hand",
                text: self.connector.getPlayerName() + _("'s hand"),
                handArea: true,
                owner: self.connector.getPlayerName(),
                top: "0px",
                left: "0px",
                width: "320px",
                height: "180px",
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
                        el("button", { onclick: hideImport }, _("Cancel")),
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
            this.playerStatusEl.innerText = _("observing");
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
        constructor(/*props*/) {
            this.el = el("div.item", [
                this.nameEl = el("div"),
                this.countEl = el("div"),
                this.addEl = el("button.add_new_component", {
                    href: '',
                }, _("Add")),
                this.removeEl = el("button.remove_component", {
                    href: '',
                }, _("Remove")),
            ]);
        }

        update(kitData, /*index, items, context*/) {
            const self = this;
            setAttr(self.el, { 'data-kit-name': kitData.kit.name });
            if (kitData.kit["label_" + language]) {
                self.nameEl.innerText = kitData.kit["label_" + language];
            } else {
                self.nameEl.innerText = kitData.kit.label;
            }
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
                connector.addNewKit(kitData);
            }

            function removeOneKitFromTable() {
                for (let i = connector.getTableData().kits.length - 1; i >= 0; i -= 1) {
                    const kit = connector.getTableData().kits[i];
                    if (kit.name === kitData.kit.name) {
                        connector.removeKit(kit.kitId);
                        break;
                    }
                }
            }

            function updateNumberOnTable() {
                let numberOnTable = 0;
                for (const kit of connector.getTableData().kits) {
                    if (kit.name === kitData.kit.name) {
                        numberOnTable += 1;
                    }
                }
                if (numberOnTable > 0) {
                    self.countEl.innerText = numberOnTable + _(' on the table');
                    self.removeEl.style.display = null;
                } else {
                    self.countEl.innerText = '';
                    self.removeEl.style.display = 'none';
                }
            }
        }
    }

    class KitsMenu {
        constructor(/*props*/) {
            const REASONABLY_BIG_ZINDEX_VALUE = 99999999;
            const self = this;
            this.kitsMenuItemList = list("div", KitsMenuItem);
            this.el = el("div.kit_selection_container", { style: { zIndex: REASONABLY_BIG_ZINDEX_VALUE } },
                [
                    el("div.kit_selection", [
                        el("button.done", { onclick: hideAddRemoveKitsMenu }, _("Done")),
                        this.kitsMenuItemList.el,
                        el("button.done", { onclick: hideAddRemoveKitsMenu }, _("Done")),
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

        update(tableData, /*context*/) {
            this.kitsMenuItemList.update(this.kitsList, tableData);
        }
    }

    return new KitsMenu();
}

export {Menu};
