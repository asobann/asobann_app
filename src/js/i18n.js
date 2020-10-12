const dictionary = {
    ja: {
        'Spread Out': '広げる',
        'Collect Components': '集める',
        'Shuffle': 'シャッフル',
        'face up / down': '裏返す',
        "enter name and join": "名前を入力して参加してください",
        "Join!": "参加する",
        "You are observing.  Join to play!  On the left side, enter name and click Join!": "現在見学中です。参加するには、左側で名前を入力して「参加する」を押してください",
        "Add / Remove Kits": "テーブルに出す・テーブルからしまう",
        "Add Hand Area": "手札エリアを作る",
        "Remove Hand Area": "手札エリアを消す",
        "Share URL for invitation": "URLをシェアすれば招待できます",
        "copy": "URLコピー",
        "Export Table": "テーブルエクスポート",
        "Import Table": "テーブルインポート",
        "'s hand": "さんの手札エリア",
        "Cancel": "キャンセル",
        "Add": "追加",
        "Remove": "消す",
        ' on the table': 'つテーブルにあります',
        "Done": "戻る",
        "you are ": "プレイヤー: ",
        "observing": "見学中",
        "Do you want to collect even in-hand components?": "手札エリアにあるものまで集めますか？",
        "About asobann": "asobannについて",
        "Copyright (C) 2020 Yattom": "Copyright © 2020 合同会社やっとむ屋, やっとむ",
        "release notes": "リリースノート",
    },
    en: {
        'Spread Out': 'Spread Out',
        'Collect Components': 'Collect Components',
        'Shuffle': 'Shuffle',
        'face up / down': 'face up / down',
        "enter name and join": "enter name and join",
        "Join!": "Join!",
        "You are observing.  Join to play!  On the left side, enter name and click Join!": "You are observing.  Join to play!  On the left side, enter name and click Join!",
        "Add / Remove Kits": "Add / Remove Kits",
        "Add Hand Area": "Add Hand Area",
        "Remove Hand Area": "Remove Hand Area",
        "Share URL for invitation": "Share URL for invitation",
        "copy": "copy",
        "Export Table": "Export Table",
        "Import Table": "Import Table",
        "'s hand": "'s hand",
        "Cancel": "Cancel",
        "Add": "Add",
        "Remove": "Remove",
        ' on the table': ' on the table',
        "Done": "Done",
        "you are ": "you are ",
        "observing": "observing",
        "Do you want to collect even in-hand components?": "Do you want to collect even in-hand components?",
        "About asobann": "About asobann",
        "Copyright (C) 2020 Yattom": "Copyright © 2020 Yattom",
        "release notes": "release notes",
    },
};

const language = (() => {
    for (const l of window.navigator.languages) {
        if (dictionary[l]) {
            return l;
        }
    }
    return null;
})();

function _(text) {
    try {
        return dictionary[language][text] || text;
    } catch (e) {
        return text;
    }
}

console.log("language", language);
export {_, language};