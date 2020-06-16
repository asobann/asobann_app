const dictionary = {
    ja: {
        'Spread Out': 'J Spread Out',
        'Collect Components': 'J Collect Components',
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
        return dictionary[language][text];
    } catch (e) {
        return text;
    }
}

console.log("language", language);
export {_, language};