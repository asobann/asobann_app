import {beforeEach, describe, expect} from "@jest/globals";

const { Table, Level } = require('../../src/js/table');
const { setFeatsContext, draggability, traylike } = require('../../src/js/feat');

import * as sync_table from '../../src/js/sync_table';

jest.spyOn(sync_table, 'pushComponentUpdate');


test('create Table', () => {
    expect(new Table({
        isPlayerObserver: () => false,
        getPlayerName: () => 'player',
    })).toBeDefined();
})


describe('3 levels of user action', () => {
    let feat_for_test =
        {
            install: () => undefined,
            isEnabled: () => true,
            receiveData: () => undefined,
            updateView: () => undefined,
            uninstall: () => undefined,
        };
    let table = null
    beforeEach(() => {
        table = new Table({
            getPlayerName: () => 'player',
            isPlayerObserver: () => false,
            feats_to_use: [feat_for_test]
        });
        feat_for_test.updateView = jest.fn();
        table.receiveData({
            components: { 'component1': { value: 0 } },
            kits: {},
            players: [],
        })
        setFeatsContext(() => 'player', () => false, table);
    });

    describe('level A - immediate ', () => {
        test('table data is updated immediately', () => {
            table.componentsOnTable['component1'].applyUserAction(Level.A, () => {
                table.componentsOnTable['component1'].propagate({ value: 100 });
            });
            expect(table.data.components['component1'].value).toBe(100);
        });

        test('component view is updated immediately', () => {
            feat_for_test.updateView = jest.fn();
            table.componentsOnTable['component1'].applyUserAction(Level.A, () => {
                table.componentsOnTable['component1'].propagate({ value: 100 });
            });
            expect(feat_for_test.updateView.mock.calls.length).toBe(1);
        });

        describe('propagate updates other components', () => {
            beforeEach(() => {
                table.receiveData({
                    components: { 'component1': { value: 0 }, 'component2': { value: 0 } },
                    kits: {},
                    players: [],
                })
                setFeatsContext(() => 'player', () => false, table);
            });

            test('applyUserAction within applyUserAction', () => {
                table.componentsOnTable['component1'].applyUserAction(Level.A, () => {
                    table.componentsOnTable['component1'].propagate({ value: 100 });
                    table.componentsOnTable['component2'].applyUserAction(Level.A, () => {
                        table.componentsOnTable['component2'].propagate({ value: 200 });
                    });
                });
                expect(feat_for_test.updateView.mock.calls.length).toBe(2);
            });

            test('only updated component will call updateView', () => {
                table.receiveData({
                    components: { 'component1': { value: 0 }, 'component2': { value: 0 }, 'another': {} },
                    kits: {},
                    players: [],
                })
                table.componentsOnTable['component1'].applyUserAction(Level.A, () => {
                    table.componentsOnTable['component1'].propagate({ value: 100 });
                    table.componentsOnTable['component2'].applyUserAction(Level.A, () => {
                        table.componentsOnTable['component2'].propagate({ value: 200 });
                    });
                });
                expect(feat_for_test.updateView.mock.calls.length).toBe(2);
            });
        });
    });

    describe('level C - consolidate ', () => {
        test('table data is updated immediately', () => {
            table.componentsOnTable['component1'].applyUserAction(Level.C, () => {
                table.componentsOnTable['component1'].propagate({ value: 100 });
            });
            expect(table.data.components['component1'].value).toBe(100);
        });

        test('component view is not updated (will be later)', () => {
            table.componentsOnTable['component1'].applyUserAction(Level.C, () => {
                table.componentsOnTable['component1'].propagate({ value: 100 });
            });
            expect(feat_for_test.updateView.mock.calls.length).toBe(0);
        });

        test('component view will be updated later (queued)', () => {
            table.componentsOnTable['component1'].applyUserAction(Level.C, () => {
                table.componentsOnTable['component1'].propagate({ value: 100 });
            });
            expect(table.queueForUpdatingView.queueToConsolidate).toContain('component1');
        });

        describe('propagate updates other components', () => {
            beforeEach(() => {
                table.receiveData({
                    components: { 'component1': { value: 0 }, 'component2': { value: 0 } },
                    kits: {},
                    players: [],
                })
                setFeatsContext(() => 'player', () => false, table);
            });

            test('applyUserAction within applyUserAction', () => {
                table.componentsOnTable['component1'].applyUserAction(Level.C, () => {
                    table.componentsOnTable['component1'].propagate({ value: 100 });
                    table.componentsOnTable['component2'].applyUserAction(Level.C, () => {
                        table.componentsOnTable['component2'].propagate({ value: 200 });
                    });
                });
                expect(feat_for_test.updateView.mock.calls.length).toBe(0);
                expect(table.queueForUpdatingView.queueToConsolidate).toContain('component1');
                expect(table.queueForUpdatingView.queueToConsolidate).toContain('component2');
            });

            test('inside applyUserAction cannot elevate level', () => {
                table.componentsOnTable['component1'].applyUserAction(Level.C, () => {
                    table.componentsOnTable['component1'].propagate({ value: 100 });
                    table.componentsOnTable['component2'].applyUserAction(Level.A, () => {
                        table.componentsOnTable['component2'].propagate({ value: 200 });
                    });
                });
                expect(feat_for_test.updateView.mock.calls.length).toBe(0);
                expect(table.queueForUpdatingView.queueToConsolidate).toContain('component1');
                expect(table.queueForUpdatingView.queueToConsolidate).toContain('component2');
            });
        });

        describe('updating same component more than two times', () => {
            test('overwrite', () => {
                // TODO
            })

            test('merge updating different property', () => {
                // TODO
            })
        })
    });
})

