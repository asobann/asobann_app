import {el, mount, setStyle, unmount} from "./redom.es.js";
import {joinTable} from "./sync_table.js";
import {names} from "./names.js";

function getPlaceholderName() {
    return names[Math.floor(Math.random() * names.length)];
}

const CONNECTOR_TEMPLATE = {
    tablename: null,
    getPlayerName: null,
    addNewComponent: null,
    removeHandArea: null,
    isPlayerObserver: null,
    isTherePlayersHandArea: null,
};

class Menu {
    constructor(connector) {
        for(const key in CONNECTOR_TEMPLATE) {
            if(!connector[key]) {
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
                    el("a", { href: "", onclick: showAddRemoveComponentMenu }, "Add / Remove Components")),
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

        function showAddRemoveComponentMenu() {
            const REASONABLY_BIG_ZINDEX_VALUE = 99999999;
            const modalMenu = el("div.component_selection_container", { style: { zIndex: REASONABLY_BIG_ZINDEX_VALUE } },
                [
                    el("div.component_selection", [
                        el("div.item", { 'data-component-name': 'dice' }, [
                            el("span", "Dice"),
                            el("a.add_new_component", {
                                href: '',
                                'data-component-name': 'dice',
                                onclick: addNewComponent
                            }, "Add"),
                        ]),
                        el("button", { onclick: hideAddRemoveComponentMenu }, "Done"),
                    ])
                ]
            );
            mount(self.addRemoveComponentItem, modalMenu);
            return false;

            function addNewComponent(event) {
                const componentName = event.target.getAttribute("data-component-name");
                console.log("add component " + componentName);

                const newComponent = {
                    name: componentName,
                    handArea: false,
                    top: "0px",
                    left: "0px",
                    width: "64px",
                    height: "64px",
                    showImage: false,
                    draggable: true,
                    flippable: false,
                    resizable: false,
                    rollable: true,
                    ownable: false,
                    zIndex: 0,
                };
                self.connector.addNewComponent(newComponent);
                return false;
            }

            function hideAddRemoveComponentMenu() {
                unmount(self.addRemoveComponentItem, modalMenu);
            }
        }
    }

    update(data) {
        if (this.connector.isPlayerObserver()) {
            setStyle(this.joinItem, { display: null });
            this.playerStatusEl.innerText = "observing";
            setStyle(this.addHandAreaItem, { display: 'none' });
            setStyle(this.removeHandAreaItem, { display: 'none' });
            return;
        }

        setStyle(this.joinItem, { display: 'none' });
        if (data.playerName) {
            this.playerStatusEl.innerText = data.playerName;
        }

        if (this.connector.isTherePlayersHandArea(this.connector.getPlayerName())) {
            setStyle(this.addHandAreaItem, { display: 'none' });
            setStyle(this.removeHandAreaItem, { display: null });
        } else {
            setStyle(this.addHandAreaItem, { display: null });
            setStyle(this.removeHandAreaItem, { display: 'none' });
        }
    }


}

export {Menu};
