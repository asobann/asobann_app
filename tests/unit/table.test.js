import {expect} from "@jest/globals";

const { Component, Table } = require('../../src/js/table');

test('create Table', () => {
    expect(new Table({
        isPlayerObserver: () => false,
        getPlayerName: () => 'player',
    })).toBeDefined();
})