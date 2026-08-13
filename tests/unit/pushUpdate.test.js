import {beforeEach, describe, expect} from "@jest/globals";
import {pushComponentUpdate, componentUpdateBuffer} from "../../src/js/sync_table";
import {Table} from "../../src/js/table";

let table;

beforeEach(() => {
    table = new Table({
        getPlayerName: () => 'player',
        isPlayerObserver: () => false,
        availableFeats: []
    });
    table.receiveData({
        components: {
            'component1': { value: 1 },
            'component2': { value: 2 },
            'component3': { value: 3 },
            'another': {}
        },
        kits: {},
        players: [],
    })
    componentUpdateBuffer.reset();
});

describe('pushComponentUpdate add updates in buffer', () => {
    describe('only one update', () => {
        beforeEach(() => {
            pushComponentUpdate(table, 'component1', { value: 100 }, false);
        })
        test('diff is buffered', () => {
            expect(componentUpdateBuffer.updateOf('component1')).toMatchObject({ value: 100 });
        })
        test('will be at 1st', () => {
            expect(componentUpdateBuffer.orderOfComponentId).toStrictEqual(['component1']);
        })
    })

    describe('three update on different components', () => {
        beforeEach(() => {
            pushComponentUpdate(table, 'component1', { value: 100 }, false);
            pushComponentUpdate(table, 'component2', { value: 200 }, false);
            pushComponentUpdate(table, 'component3', { value: 300 }, false);
        })
        test('diff is buffered', () => {
            expect(componentUpdateBuffer.updateOf('component1')).toMatchObject({ value: 100 });
            expect(componentUpdateBuffer.updateOf('component2')).toMatchObject({ value: 200 });
            expect(componentUpdateBuffer.updateOf('component3')).toMatchObject({ value: 300 });
        })
        test('order is correct', () => {
            expect(componentUpdateBuffer.orderOfComponentId).toStrictEqual(['component1', 'component2', 'component3']);
        })
    })

    describe('updates for same component is merged', () => {
        beforeEach(() => {
            pushComponentUpdate(table, 'component1', { value: 100 }, false);
            pushComponentUpdate(table, 'component2', { value: 200 }, false);
            pushComponentUpdate(table, 'component1', { value2: 300 }, false);
        })
        test('diff is merged', () => {
            expect(componentUpdateBuffer.updateOf('component1')).toMatchObject({ value: 100, value2: 300 });
        })
        test('order represents when FIRST added', () => {
            expect(componentUpdateBuffer.orderOfComponentId).toStrictEqual(['component1', 'component2']);
            expect(componentUpdateBuffer.orderOfComponentId.length).toBe(2);
        })
    })
});

describe('ComponentUpdateBuffer builds message', () => {
    test('no updates', () => {
        expect(() => componentUpdateBuffer.buildMessageToEmit()).toThrow('no updates to emit')
    });

    test('one simple update', () => {
        pushComponentUpdate(table, 'component1', { value: 100 }, false);
        expect(componentUpdateBuffer.buildMessageToEmit()).toMatchObject({
            eventName: 'update many components',
            data: {
                tablename: table.tablename,
                originator: expect.stringMatching(/.*/),
                diffs: [
                    { component1: { value: 100 } },
                ]
            },
        })
    });

    test('three simple update', () => {
        pushComponentUpdate(table, 'component1', { value: 100 }, false);
        pushComponentUpdate(table, 'component2', { value: 200 }, false);
        pushComponentUpdate(table, 'component3', { value: 300 }, false);
        expect(componentUpdateBuffer.buildMessageToEmit()).toMatchObject({
            eventName: 'update many components',
            data: {
                tablename: table.tablename,
                originator: expect.stringMatching(/.*/),
                diffs: [
                    { component1: { value: 100 } },
                    { component2: { value: 200 } },
                    { component3: { value: 300 } },
                ]
            },
        })
    });
});

describe('volatile updates are excluded from persistence but not from broadcast', () => {
    test('a volatile-only key is listed in volatileKeys', () => {
        pushComponentUpdate(table, 'component1', { left: 10 }, true);
        const msg = componentUpdateBuffer.buildMessageToEmit();
        expect(msg.data.diffs).toMatchObject([{ component1: { left: 10 } }]);
        expect(msg.data.volatileKeys.component1).toEqual(['left']);
    });

    test('a non-volatile key is not listed in volatileKeys', () => {
        pushComponentUpdate(table, 'component1', { value: 100 }, false);
        const msg = componentUpdateBuffer.buildMessageToEmit();
        expect(msg.data.volatileKeys.component1).toBeUndefined();
    });

    test('a non-volatile write after a volatile write on the same key persists it', () => {
        pushComponentUpdate(table, 'component1', { left: 10 }, true);
        pushComponentUpdate(table, 'component1', { left: 20 }, false);
        const msg = componentUpdateBuffer.buildMessageToEmit();
        expect(msg.data.diffs).toMatchObject([{ component1: { left: 20 } }]);
        expect(msg.data.volatileKeys.component1).toBeUndefined();
    });

    test('a volatile write after a non-volatile write on the same key stays persisted', () => {
        pushComponentUpdate(table, 'component1', { left: 20 }, false);
        pushComponentUpdate(table, 'component1', { left: 30 }, true);
        const msg = componentUpdateBuffer.buildMessageToEmit();
        expect(msg.data.diffs).toMatchObject([{ component1: { left: 30 } }]);
        expect(msg.data.volatileKeys.component1).toBeUndefined();
    });

    test('other keys on the same component stay volatile independently', () => {
        pushComponentUpdate(table, 'component1', { left: 10 }, true);
        pushComponentUpdate(table, 'component1', { value: 100 }, false);
        const msg = componentUpdateBuffer.buildMessageToEmit();
        expect(msg.data.diffs).toMatchObject([{ component1: { left: 10, value: 100 } }]);
        expect(msg.data.volatileKeys.component1).toEqual(['left']);
    });

    test('reset clears persisted-key tracking', () => {
        pushComponentUpdate(table, 'component1', { left: 20 }, false);
        componentUpdateBuffer.reset();
        pushComponentUpdate(table, 'component1', { left: 10 }, true);
        const msg = componentUpdateBuffer.buildMessageToEmit();
        expect(msg.data.volatileKeys.component1).toEqual(['left']);
    });
});
