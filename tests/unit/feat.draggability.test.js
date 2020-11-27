import {beforeEach, describe, expect} from "@jest/globals";

const { Table } = require('../../src/js/table');
const { setFeatsContext, draggability, traylike, feats } = require('../../src/js/feat');

import * as sync_table from '../../src/js/sync_table';

jest.spyOn(sync_table, 'pushComponentUpdate');

let table = null
beforeEach(() => {
    table = new Table(
        {
            getPlayerName: () => 'player',
            isPlayerObserver: () => false,
            feats_to_use: feats
        });
    setFeatsContext(() => 'player', () => false, table);
});

describe('feat.draggability basics', () => {
    test('start, move, then end', () => {
        table.receiveData({
            components: { 'component1': { draggable: true, left: 0, top: 0, width: 50, height: 100 } },
            kits: {},
            players: [],
        })
        const component = table.componentsOnTable['component1'];
        const data = component.data;
        draggability.move(component, data, { x: 110, y: 130, dx: 10, dy: 30, page: { x: 110, y: 130 } });
        expect(component.rect).toStrictEqual({ left: 10, top: 30, width: 50, height: 100 })
        draggability.move(component, data, { x: 125, y: 150, dx: 15, dy: 20, page: { x: 125, y: 150 } });
        draggability.end(component, data, { page: { x: 125, y: 150 } });
        expect(component.rect).toStrictEqual({ left: 25, top: 50, width: 50, height: 100 })
    })

    test('drag stacked components', () => {
        table.receiveData({
            components: {
                'component1': { draggable: true, left: 0, top: 0, width: 100, height: 200, traylike: true },
                'component2': { draggable: true, left: 10, top: 10, width: 50, height: 100 },
                'component3': { draggable: true, left: 20, top: 20, width: 50, height: 100 },
            },
            kits: {},
            players: [],
        });
        const component1 = table.componentsOnTable['component1'];
        const component2 = table.componentsOnTable['component2'];
        const component3 = table.componentsOnTable['component3'];
        traylike.comeIn(component1, { visitor: component2 });
        traylike.comeIn(component1, { visitor: component3 });
        const data = component1.data;
        draggability.move(component1, data, { x: 110, y: 130, dx: 10, dy: 30, page: { x: 110, y: 130 } });
        expect(component2.rect).toStrictEqual({ left: 20, top: 40, width: 50, height: 100 })
        expect(component3.rect).toStrictEqual({ left: 30, top: 50, width: 50, height: 100 })
        draggability.move(component1, data, { x: 125, y: 150, dx: 15, dy: 20, page: { x: 125, y: 150 } });
        draggability.end(component1, data, { page: { x: 125, y: 150 } });
        expect(component2.rect).toStrictEqual({ left: 35, top: 60, width: 50, height: 100 })
        expect(component3.rect).toStrictEqual({ left: 45, top: 70, width: 50, height: 100 })
    })

    test('end emit finalized left,top when dragging a stack', () => {
        table.receiveData({
            components: {
                'component1': { draggable: true, left: 0, top: 0, width: 100, height: 200, traylike: true },
                'component2': { draggable: true, left: 10, top: 10, width: 50, height: 100 },
                'component3': { draggable: true, left: 20, top: 20, width: 50, height: 100 },
            },
            kits: {},
            players: [],
        });
        const component1 = table.componentsOnTable['component1'];
        const component2 = table.componentsOnTable['component2'];
        const component3 = table.componentsOnTable['component3'];
        traylike.comeIn(component1, { visitor: component2 });
        traylike.comeIn(component1, { visitor: component3 });
        const data = component1.data;
        draggability.move(component1, data, { x: 110, y: 130, dx: 10, dy: 30, page: { x: 110, y: 130 } });
        draggability.move(component1, data, { x: 125, y: 150, dx: 15, dy: 20, page: { x: 125, y: 150 } });
        sync_table.pushComponentUpdate.mock.calls = [];
        draggability.end(component1, data, { page: { x: 125, y: 150 } });

        // end event is non-volatile and it must have last left, top so that server can save them
        const calls = sync_table.pushComponentUpdate.mock.calls;
        for (let i = calls.length - 1; i >= 0; i--) {
            if (calls[i][1] === 'component2' && calls[i][3] === false) {
                expect(calls[i][2].left).toBe(35);
                expect(calls[i][2].top).toBe(60);
                break;
            }
        }
    })
})
