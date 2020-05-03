import {el, mount, setStyle, unmount} from "./redom.es.js";
import {joinTable} from "./sync_table.js";
import {names} from "./names.js";

function getPlaceholderName() {
    return names[Math.floor(Math.random() * names.length)];
}

class Menu {
    constructor(connector) {
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
                this.addHandAreaItem = el("div.menuitem#add_hand_area",
                    el("a", { href: "", onclick: this.connector.addHandArea }, "Add Hand Area")),
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

        function showImport(ev) {
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
