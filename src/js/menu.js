import {el, list, mount, setAttr, setStyle, unmount} from "redom";
import {joinTable} from "./sync_table.js";
import {names} from "./names.js";
import {getCraftBoxKit} from "./craft_box";
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

        function menuitem(id, label, attrs) {
            let tag;
            if (id) {
                tag = "div.menuitem#" + id;
            } else {
                tag = "div.menuitem";
            }
            return el(tag, el("a", attrs, label));
        }

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
                this.addRemoveComponentItem = menuitem("add_remove_component", _("Add / Remove Kits"),
                    { href: "", onclick: showAddRemoveKitsMenu }),
                this.addHandAreaItem = menuitem("add_hand_area", _("Add Hand Area"),
                    { href: "", onclick: addHandArea }),
                this.removeHandAreaItem = menuitem("remove_hand_area", _("Remove Hand Area"),
                    { href: "", onclick: this.connector.removeHandArea }),
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
                menuitem("open_toolbox", _("Open Toolbox"), { href: "", onclick: openToolbox }),
                menuitem("import_table", _("Import Table"), { href: "", onclick: showImport }),
                el("div.menuitem.about", [
                    el("a", {
                        class: 'about',
                        href: 'https://games.yattom.jp/asobann',
                        target: '_blank'
                    }, _("About asobann")),
                    el("br"),
                    el("a", {
                        class: 'about',
                        href: '#',
                        onclick: showReleaseNote,
                    }, _("release notes")),
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

        function openToolbox() {
            async function doOpen() {
                const kitData = await getCraftBoxKit(baseUrl());
                connector.addNewKit(await kitData);
            }

            doOpen().then(/* do nothing */);
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

        function showReleaseNote(ev) {
            const noteEl = el("div.release_note",
                [
                    el('div.text',
                        [
                            'リリースノート\n', el('br'),
                            '\n', el('br'),
                            '2021.8.10\n', el('br'),
                            '・手札エリアを消すの問題に対処\n', el('br'),
                            '\n', el('br'),
                            '2021.8.2\n', el('br'),
                            '・カードを回転させる、オーバーレイを追加\n', el('br'),
                            '\n', el('br'),
                            '2020.10.17\n', el('br'),
                            '・大幅な高速化と、4人以上で使うときの遅延と同期ズレを改善\n', el('br'),
                            '\n', el('br'),
                            '2020.9.16\n', el('br'),
                            '・カウンターを追加\n', el('br'),
                            '\n', el('br'),
                            '2020.9.5\n', el('br'),
                            '・道具箱を追加しUIを微調整\n', el('br'),
                            '・ゲームのアップロードに対応(非公式)\n', el('br'),
                            '\n', el('br'),
                            '2020.8.27\n', el('br'),
                            '・テーブルの最終更新時刻を記録\n', el('br'),
                            '\n', el('br'),
                            '2020.8.26\n', el('br'),
                            '・新しいドメイン asobann.yattom.jp へ移行\n', el('br'),
                            '・AWSへ引っ越し\n', el('br'),
                            '\n', el('br'),
                            '2020.8.9\n', el('br'),
                            '・プレイヤー間の同期ズレを軽減\n', el('br'),
                            '\n', el('br'),
                            '2020.7.16\n', el('br'),
                            '・石の置き場を軽くした(心理的安全性ゲーム)\n', el('br'),
                            '・負荷テスト自動化\n', el('br'),
                            '\n', el('br'),
                            '2020.6.23\n', el('br'),
                            '・ダイヤモンドゲームを追加\n', el('br'),
                            '\n', el('br'),
                            '2020.6.22\n', el('br'),
                            '・心理的安全性ゲームを追加\n', el('br'),
                            '・プランニングポーカーを追加\n', el('br'),
                            '\n', el('br'),
                            '2020.6.19', el('br'),
                            '・トランプのシャッフル、広げる・集める、裏返すを実装\n', el('br'),
                            '・使わないコンポーネント置き場を実装\n', el('br'),
                            '・リリースと最初のアナウンス\n', el('br'),
                        ],
                    ),
                    el('button.close', { onclick: hide }, _("Close")),
                ]);
            mount(self.el, noteEl);

            function hide() {
                unmount(self.el, noteEl);
            }

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
