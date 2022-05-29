import {beforeEach, describe, expect} from "@jest/globals";

const { Table, Level } = require('../../src/js/table');
const { setFeatsContext } = require('../../src/js/feat');

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
    let component1 = null;
    let component2 = null;
    let componentData1 = null;
    let componentData2 = null;
    beforeEach(() => {
        table = new Table({
            getPlayerName: () => 'player',
            isPlayerObserver: () => false,
            available_feats: [feat_for_test]
        });
        feat_for_test.updateView = jest.fn();
        table.receiveData({
            components: { 'component1': { value: 0 }, 'component2': { value: 0 }, 'another': {} },
            kits: {},
            players: [],
        })
        component1 = table.componentsOnTable['component1'];
        component2 = table.componentsOnTable['component2'];
        componentData1 = table.data.components['component1'];
        componentData2 = table.data.components['component2'];
        setFeatsContext(() => 'player', () => false, table);
    });

    describe('level A - immediate ', () => {
        test('table data is updated immediately', () => {
            component1.applyUserAction(Level.A, () => {
                component1.propagate({ value: 100 });
            });
            expect(componentData1.value).toBe(100);
        });

        test('component view is updated immediately', () => {
            feat_for_test.updateView = jest.fn();
            component1.applyUserAction(Level.A, () => {
                component1.propagate({ value: 100 });
            });
            expect(feat_for_test.updateView.mock.calls.length).toBe(1);
        });

        describe('propagate updates other components', () => {
            test('applyUserAction within applyUserAction', () => {
                component1.applyUserAction(Level.A, () => {
                    component1.propagate({ value: 100 });
                    component2.applyUserAction(Level.A, () => {
                        component2.propagate({ value: 200 });
                    });
                });
                expect(feat_for_test.updateView.mock.calls.length).toBe(2);
            });

            test('innner applyUserAction has different level', () => {
                component1.applyUserAction(Level.A, () => {
                    component1.propagate({ value: 100 });
                    component2.applyUserAction(Level.C, () => {
                        component2.propagate({ value: 200 });
                    });
                });
                expect(feat_for_test.updateView.mock.calls.length).toBe(1);
            });

            test('only updated component will call updateView', () => {
                table.receiveData({
                    components: { 'component1': { value: 0 }, 'component2': { value: 0 }, 'another': {} },
                    kits: {},
                    players: [],
                })
                component1.applyUserAction(Level.A, () => {
                    component1.propagate({ value: 100 });
                    component2.applyUserAction(Level.A, () => {
                        component2.propagate({ value: 200 });
                    });
                });
                expect(feat_for_test.updateView.mock.calls.length).toBe(2);
            });
        });
    });

    describe('level B - consolidate following ', () => {
        test('table data is updated immediately', () => {
            component1.applyUserAction(Level.B, () => {
                component1.propagate({ value: 100 });
            });
            expect(componentData1.value).toBe(100);
        });

        describe('level B is complex when nested', () =>{
            test('table data is updated immediately', () => {
                component1.applyUserAction(Level.B, () => {
                    component1.propagate({ value: 100 });
                    component2.applyUserAction(Level.A, () => {
                        component2.propagate({ value: 200 });
                    });
                });
                expect(componentData1.value).toBe(100);
                expect(componentData2.value).toBe(200);
            });
            test('only first applyUserAction update view', () => {
                component1.applyUserAction(Level.B, () => {
                    component1.propagate({ value: 100 });
                    component2.applyUserAction(Level.A, () => {
                        component2.propagate({ value: 200 });
                    });
                });
                expect(feat_for_test.updateView.mock.calls.length).toBe(1);
                expect(feat_for_test.updateView.mock.calls[0][0]).toBe(component1);
            });
        })
    });

    describe('level C - consolidate ', () => {
        test('table data is updated immediately', () => {
            component1.applyUserAction(Level.C, () => {
                component1.propagate({ value: 100 });
            });
            expect(componentData1.value).toBe(100);
        });

        test('component view is not updated (will be later)', () => {
            component1.applyUserAction(Level.C, () => {
                component1.propagate({ value: 100 });
            });
            expect(feat_for_test.updateView.mock.calls.length).toBe(0);
        });

        test('component view will be updated later (queued)', () => {
            component1.applyUserAction(Level.C, () => {
                component1.propagate({ value: 100 });
            });
            expect(table.queueForUpdatingView.queueToConsolidate).toContain('component1');
        });

        describe('propagate updates other components', () => {
            test('applyUserAction within applyUserAction', () => {
                component1.applyUserAction(Level.C, () => {
                    component1.propagate({ value: 100 });
                    component2.applyUserAction(Level.C, () => {
                        component2.propagate({ value: 200 });
                    });
                });
                expect(feat_for_test.updateView.mock.calls.length).toBe(0);
                expect(table.queueForUpdatingView.queueToConsolidate).toContain('component1');
                expect(table.queueForUpdatingView.queueToConsolidate).toContain('component2');
            });

            test('inner applyUserAction cannot elevate level', () => {
                component1.applyUserAction(Level.C, () => {
                    component1.propagate({ value: 100 });
                    component2.applyUserAction(Level.A, () => {
                        component2.propagate({ value: 200 });
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

    test('level retains after inner applyUserAction', ()=>{
        component1.applyUserAction(Level.A, () => {
            component1.propagate({ value: 100 });
            component2.applyUserAction(Level.C, () => {
                // zip
            });
            component2.propagate({ value: 200 });
        });
        expect(feat_for_test.updateView.mock.calls.length).toBe(2);
    })

    test('propagate works in legacy way without applyUserAction', ()=>{
        component1.propagate({ value: 100 });
        table.updateView();
        expect(feat_for_test.updateView.mock.calls.length).toBe(3);
        expect(table.queueForUpdatingView.queueToConsolidate.length).toBe(0);
        expect(table.queueForUpdatingView.queueForImmediate.length).toBe(0);
    })

    test('can propagate within other components applyUserAction', () => {
        component1.applyUserAction(Level.C, () => {
            component2.propagate({ value: 100 });
        });
        expect(feat_for_test.updateView.mock.calls.length).toBe(0);
        expect(table.queueForUpdatingView.queueToConsolidate).not.toContain('component1');
        expect(table.queueForUpdatingView.queueToConsolidate).toContain('component2');
    });

})

