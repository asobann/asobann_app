import {beforeEach, describe, expect} from "@jest/globals";

const { Component, Table } = require('../../src/js/table');
const { feats, setFeatsContext } = require('../../src/js/feat');

function getFeatByName(featName) {
    for (const f of feats) {
        if (f.featName === featName) {
            return f;
        }
    }
    throw 'No feat named ' + featName;
}

describe('feat.draggability basics', () => {
    let table = {};
    beforeEach(() => {
        table = new Table({ getPlayerName: () => 'player', isPlayerObserver: () => false });
        table.receiveData({
            components: { 'component1': { draggable: true, left: 0, top: 0, width: 50, height: 100 } },
            kits: {},
            players: [],
        })
        setFeatsContext(() => 'player', () => false, table);
    });

    test('start, move, then end', () => {
        const component = table.componentsOnTable['component1'];
        const data = component.data;
        const draggability = getFeatByName('draggability');
        draggability.start(component, data, { x0: 100, y0: 100 });
        draggability.move(component, data, { x: 110, y: 130, dx: 10, dy: 30, page: { x: 110, y: 130 } });
        expect(component.rect).toStrictEqual({ left: 10, top: 30, width: 50, height: 100 })
        draggability.move(component, data, { x: 125, y: 150, dx: 15, dy: 20, page: { x: 125, y: 150 } });
        draggability.end(component, data, { page: { x: 125, y: 150 } });
        expect(component.rect).toStrictEqual({ left: 25, top: 50, width: 50, height: 100 })
    })
})
