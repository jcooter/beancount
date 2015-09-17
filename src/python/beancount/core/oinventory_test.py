"""
Unit tests for the Inventory class.
"""
__author__ = "Martin Blais <blais@furius.ca>"

import datetime
import unittest
import copy
from datetime import date
import types

from beancount.core import oposition as position
from beancount.core import oinventory as inventory
from beancount.core.oposition import Position
from beancount.core.oposition import Lot
from beancount.core.oposition import Cost
from beancount.core.oinventory import Inventory
from beancount.core.oinventory import Booking

from beancount.core.number import D
from beancount.core.number import ZERO
from beancount.core import amount
from beancount.utils import invariants


A = amount.from_string
P = position.from_string
I = inventory.from_string


def setUp(module):
    invariants.instrument_invariants(Inventory,
                                     inventory.check_invariants,
                                     inventory.check_invariants)

def tearDown(module):
    invariants.uninstrument_invariants(Inventory)


class TestInventory(unittest.TestCase):

    def checkAmount(self, inventory, number, currency):
        amount_ = amount.Amount(number, currency)
        inv_amount = inventory.get_units(amount_.currency)
        self.assertEqual(inv_amount, amount_)

    def test_from_string(self):
        inv = inventory.from_string('')
        self.assertEqual(Inventory(), inv)

        inv = inventory.from_string('10 USD')
        self.assertEqual(
            Inventory([Position(Lot("USD", None), D('10'))]),
            inv)

        inv = inventory.from_string(' 10.00  USD ')
        self.assertEqual(
            Inventory([Position(Lot("USD", None), D('10'))]),
            inv)

        inv = inventory.from_string('1 USD, 2 CAD')
        self.assertEqual(
            Inventory([Position(Lot("USD", None), D('1')),
                       Position(Lot("CAD", None), D('2'))]),
            inv)

        inv = inventory.from_string('2.2 HOOL {532.43 USD}, 3.413 EUR')
        self.assertEqual(
            Inventory([Position(Lot("HOOL", Cost(D('532.43'), 'USD', None, None)),
                                D('2.2')),
                       Position(Lot("EUR", None), D('3.413'))]),
            inv)

        inv = inventory.from_string(
            '2.2 HOOL {532.43 USD}, 2.3 HOOL {564.00 USD, 2015-07-14}, 3.413 EUR')
        self.assertEqual(
            Inventory([Position(Lot("HOOL", Cost(D('532.43'), 'USD', None, None)),
                                D('2.2')),
                       Position(Lot("HOOL", Cost(D('564.00'), 'USD',
                                                 datetime.date(2015, 7, 14), None)),
                                D('2.3')),
                       Position(Lot("EUR", None),
                                D('3.413'))]),
            inv)

        inv = inventory.from_string(
            '1.1 HOOL {500.00 # 11.00 USD}, 100 CAD')
        self.assertEqual(
            Inventory([Position(Lot("HOOL", Cost(D('510.00'), 'USD', None, None)),
                                D('1.1')),
                       Position(Lot("CAD", None),
                                D('100'))]),
            inv)

    def test_ctor_empty_len(self):
        # Test regular constructor.
        inv = Inventory()
        self.assertTrue(inv.is_empty())
        self.assertEqual(0, len(inv))

        inv = Inventory([P('100.00 USD'),
                         P('101.00 USD')])
        self.assertFalse(inv.is_empty())
        self.assertEqual(1, len(inv))

        inv = Inventory([P('100.00 USD'),
                         P('100.00 CAD')])
        self.assertFalse(inv.is_empty())
        self.assertEqual(2, len(inv))

        inv = Inventory()
        self.assertEqual(0, len(inv))
        inv.add_amount(A('100 USD'))
        self.assertEqual(1, len(inv))
        inv.add_amount(A('100 CAD'))
        self.assertEqual(2, len(inv))

    def test_str(self):
        inv = I('100.00 USD, 101.00 CAD')
        self.assertEqual('(100.00 USD, 101.00 CAD)', str(inv))

    def test_copy(self):
        inv = Inventory()
        inv.add_amount(A('100.00 USD'))
        self.checkAmount(inv, '100', 'USD')

        # Test copying.
        inv2 = copy.copy(inv)
        inv2.add_amount(A('50.00 USD'))
        self.checkAmount(inv2, '150', 'USD')

        # Check that the original object is not modified.
        self.checkAmount(inv, '100', 'USD')

    def test_op_eq(self):
        inv1 = I('100 USD, 100 CAD')
        inv2 = I('100 CAD, 100 USD')
        self.assertEqual(inv1, inv2)
        self.assertEqual(inv2, inv1)

        inv3 = I('200 USD, 100 CAD')
        self.assertNotEqual(inv1, inv3)
        self.assertNotEqual(inv3, inv1)

        inv4 = I('100 USD, 100 JPY')
        self.assertNotEqual(inv1, inv4)
        self.assertNotEqual(inv4, inv1)

        inv5 = I('100 JPY, 100 USD')
        self.assertEqual(inv4, inv5)

    def test_is_small__value(self):
        test_inv = I('1.50 JPY, 1.51 USD, 1.52 CAD')
        for inv in test_inv, -test_inv:
            self.assertFalse(inv.is_small(D('1.49')))
            self.assertFalse(inv.is_small(D('1.50')))
            self.assertTrue(inv.is_small(D('1.53')))
            self.assertTrue(inv.is_small(D('1.52')))

    def test_is_small__dict(self):
        test_inv = I('0.03 JPY, 0.003 USD')
        for inv in test_inv, -test_inv:
            # Test all four types of inequalities.
            self.assertTrue(inv.is_small({'JPY': D('0.05'), 'USD': D('0.005')}))
            self.assertFalse(inv.is_small({'JPY': D('0.005'), 'USD': D('0.0005')}))
            self.assertTrue(inv.is_small({'JPY': D('0.05'), 'USD': D('0.5')}))
            self.assertFalse(inv.is_small({'JPY': D('0.005'), 'USD': D('0.005')}))

            # Test border case and an epsilon under.
            self.assertTrue(inv.is_small({'JPY': D('0.03'), 'USD': D('0.003')}))
            self.assertFalse(inv.is_small({'JPY': D('0.02999999999999'),
                                           'USD': D('0.003')}))
            self.assertFalse(inv.is_small({'JPY': D('0.03'), 'USD': D('0.00299999')}))

            # Test missing precisions.
            self.assertFalse(inv.is_small({'JPY': D('0.05')}))
            self.assertFalse(inv.is_small({'USD': D('0.005')}))

            # Test extra precisions.
            self.assertTrue(inv.is_small({'JPY': D('0.05'),
                                          'USD': D('0.005'),
                                          'CAD': D('0.0005')}))

            # Test no precisions.
            self.assertFalse(inv.is_small({}))

    def test_is_small__with_default(self):
        inv = I('0.03 JPY')
        self.assertTrue(inv.is_small({'JPY': D('0.05')}))
        self.assertFalse(inv.is_small({'JPY': D('0.02')}))
        self.assertTrue(inv.is_small({}, {'JPY': D('0.05')}))
        self.assertFalse(inv.is_small({}, {'JPY': D('0.02')}))

    def test_is_mixed(self):
        inv = I('100 HOOL {250 USD}, 101 HOOL {251 USD}')
        self.assertFalse(inv.is_mixed())

        inv = I('100 HOOL {250 USD}, -1 HOOL {251 USD}')
        self.assertTrue(inv.is_mixed())

        inv = I('-2 HOOL {250 USD}, -1 HOOL {251 USD}')
        self.assertFalse(inv.is_mixed())

    def test_op_neg(self):
        inv = Inventory()
        inv.add_amount(A('10 USD'))
        ninv = -inv
        self.checkAmount(ninv, '-10', 'USD')

        pinv = I('1.50 JPY, 1.51 USD, 1.52 CAD')
        ninv = I('-1.50 JPY, -1.51 USD, -1.52 CAD')
        self.assertEqual(pinv, -ninv)

    def test_get_units(self):
        inv = I('40.50 JPY, 40.51 USD {1.01 CAD}, 40.52 CAD')
        self.assertEqual(inv.get_units('JPY'), A('40.50 JPY'))
        self.assertEqual(inv.get_units('USD'), A('40.51 USD'))
        self.assertEqual(inv.get_units('CAD'), A('40.52 CAD'))
        self.assertEqual(inv.get_units('AUD'), A('0 AUD'))
        self.assertEqual(inv.get_units('NZD'), A('0 NZD'))

    def test_segregate_units(self):
        inv = I(
            '2.2 HOOL {532.43 USD}, 2.3 HOOL {564.00 USD, 2015-07-14}, 3.41 CAD, 101.20 USD')
        ccymap = inv.segregate_units(['HOOL', 'USD', 'EUR'])
        self.assertEqual({
            None: I('3.41 CAD'),
            'USD': I('101.20 USD'),
            'EUR': inventory.Inventory(),
            'HOOL': I('2.2 HOOL {532.43 USD}, '
                                          '2.3 HOOL {564.00 USD, 2015-07-14}')}, ccymap)

    def test_units1(self):
        inv = Inventory()
        self.assertEqual(inv.units(), I(''))

        inv = I('40.50 JPY, 40.51 USD {1.01 CAD}, 40.52 CAD')
        self.assertEqual(inv.units(),
                         I('40.50 JPY, 40.51 USD, 40.52 CAD'))

        # Check that the same units coalesce.
        inv = I('2 HOOL {400 USD}, 3 HOOL {410 USD}')
        self.assertEqual(inv.units(), I('5 HOOL'))

        inv = I('2 HOOL {400 USD}, -3 HOOL {410 USD}')
        self.assertEqual(inv.units(), I('-1 HOOL'))

    POSITIONS_ALL_KINDS = [
        P('40.50 USD'),
        P('40.50 USD {1.10 CAD}'),
        P('40.50 USD {1.10 CAD, 2012-01-01}')]

    def test_units(self):
        inv = Inventory(self.POSITIONS_ALL_KINDS +
                        [P('50.00 CAD')])
        inv_cost = inv.units()
        self.assertEqual(I('121.50 USD, 50.00 CAD'), inv_cost)

    def test_cost(self):
        inv = Inventory(self.POSITIONS_ALL_KINDS +
                        [P('50.00 CAD')])
        inv_cost = inv.cost()
        self.assertEqual(I('40.50 USD, 139.10 CAD'), inv_cost)

    def test_average(self):
        # Identity, no aggregation.
        inv = I('40.50 JPY, 40.51 USD {1.01 CAD}, 40.52 CAD')
        self.assertEqual(inv.average(), inv)

        # Identity, no aggregation, with a mix of lots at cost and without cost.
        inv = I('40 USD {1.01 CAD}, 40 USD')
        self.assertEqual(inv.average(), inv)

        # Aggregation.
        inv = I('40 USD {1.01 CAD}, 40 USD {1.02 CAD}')
        self.assertEqual(inv.average(), I('80.00 USD {1.015 CAD}'))

        # Aggregation, more units.
        inv = I('2 HOOL {500 USD}, 3 HOOL {520 USD}, 4 HOOL {530 USD}')
        self.assertEqual(inv.average(), I('9 HOOL {520 USD}'))

    def test_currencies(self):
        inv = Inventory()
        self.assertEqual(set(), inv.currencies())

        inv = I('40 USD {1.01 CAD}, 40 USD')
        self.assertEqual({'USD'}, inv.currencies())

        inv = I('40 AAPL {1.01 USD}, 10 HOOL {2.02 USD}')
        self.assertEqual({'AAPL', 'HOOL'}, inv.currencies())

    def test_currency_pairs(self):
        inv = Inventory()
        self.assertEqual(set(), inv.currency_pairs())

        inv = I('40 USD {1.01 CAD}, 40 USD')
        self.assertEqual(set([('USD', 'CAD'), ('USD', None)]), inv.currency_pairs())

        inv = I('40 AAPL {1.01 USD}, 10 HOOL {2.02 USD}')
        self.assertEqual(set([('AAPL', 'USD'), ('HOOL', 'USD')]), inv.currency_pairs())

    def test_add(self):
        inv = Inventory()
        inv.add_amount(A('100.00 USD'))
        self.checkAmount(inv, '100', 'USD')

        # Add some amount
        inv.add_amount(A('25.01 USD'))
        self.checkAmount(inv, '125.01', 'USD')

        # Subtract some amount.
        inv.add_amount(A('-12.73 USD'))
        self.checkAmount(inv, '112.28', 'USD')

        # Subtract some to be negative (should be allowed if no lot).
        inv.add_amount(A('-120 USD'))
        self.checkAmount(inv, '-7.72', 'USD')

        # Subtract some more.
        inv.add_amount(A('-1 USD'))
        self.checkAmount(inv, '-8.72', 'USD')

        # Add to above zero again
        inv.add_amount(A('18.72 USD'))
        self.checkAmount(inv, '10', 'USD')

    def test_add__booking(self):
        inv = Inventory()
        _, booking = inv.add_amount(A('100.00 USD'))
        self.assertEqual(Booking.CREATED, booking)

        _, booking = inv.add_amount(A('20.00 USD'))
        self.assertEqual(Booking.AUGMENTED, booking)

        _, booking = inv.add_amount(A('-20 USD'))
        self.assertEqual(Booking.REDUCED, booking)

        _, booking = inv.add_amount(A('-100 USD'))
        self.assertEqual(Booking.REDUCED, booking)

    def test_add_multi_currency(self):
        inv = Inventory()
        inv.add_amount(A('100 USD'))
        inv.add_amount(A('100 CAD'))
        self.checkAmount(inv, '100', 'USD')
        self.checkAmount(inv, '100', 'CAD')

        inv.add_amount(A('25 USD'))
        self.checkAmount(inv, '125', 'USD')
        self.checkAmount(inv, '100', 'CAD')

    def test_add_withlots(self):
        # Testing the strict case where everything matches, with only a cost.
        inv = Inventory()
        inv.add_amount(A('50 HOOL'), Cost(D('700'), 'USD', None, None))
        self.checkAmount(inv, '50', 'HOOL')

        inv.add_amount(A('-40 HOOL'), Cost(D('700'), 'USD', None, None))
        self.checkAmount(inv, '10', 'HOOL')

        position_, _ = inv.add_amount(A('-12 HOOL'),
                                      Cost(D('700'), 'USD', None, None))
        self.assertTrue(position_.is_negative_at_cost())

        # Testing the strict case where everything matches, a cost and a lot-date.
        inv = Inventory()
        inv.add_amount(A('50 HOOL'), Cost(D('700'),  'USD', date(2000, 1, 1), None))
        self.checkAmount(inv, '50', 'HOOL')

        inv.add_amount(A('-40 HOOL'), Cost(D('700'), 'USD', date(2000, 1, 1), None))
        self.checkAmount(inv, '10', 'HOOL')

        position_, _ = inv.add_amount(A('-12 HOOL'), Cost(D('700'), 'USD',
                                                          date(2000, 1, 1), None))
        self.assertTrue(position_.is_negative_at_cost())

    def test_add_allow_negative(self):

        def check_allow_negative(inv):
            position_, _ = inv.add_amount(A('-11 USD'))
            self.assertFalse(position_.is_negative_at_cost())
            position_, _ = inv.add_amount(A('-11 USD'), Cost(D('1.10'), 'CAD', None, None))
            self.assertTrue(position_.is_negative_at_cost())
            position_, _ = inv.add_amount(A('-11 USD'),
                                          Cost(None, None, date(2012, 1, 1), None))
            self.assertTrue(position_.is_negative_at_cost())
            inv.add_amount(A('-11 USD'), Cost(D('1.10'), 'CAD', None, None))
            inv.add_amount(A('-11 USD'), Cost(None, None, date(2012, 1, 1), None))

        # Test adding to a position that does not exist.
        inv = Inventory()
        check_allow_negative(inv)

        # Test adding to a position that does exist.
        inv = I(
            '10 USD, 10 USD {1.10 CAD}, 10 USD {1.10 CAD, 2012-01-01}')
        check_allow_negative(inv)

    def test_add_position(self):
        inv = Inventory()
        for pos in self.POSITIONS_ALL_KINDS:
            inv.add_position(pos)
        self.assertEqual(Inventory(self.POSITIONS_ALL_KINDS), inv)

    def test_op_add(self):
        inv1 = I('17.00 USD')
        orig_inv1 = I('17.00 USD')
        inv2 = I('21.00 CAD')
        inv3 = inv1 + inv2
        self.assertEqual(I('17.00 USD, 21.00 CAD'), inv3)
        self.assertEqual(orig_inv1, inv1)

    def test_update(self):
        inv1 = I('11 USD')
        inv2 = I('12 CAD')
        inv_updated = inv1.add_inventory(inv2)
        expect_updated = I('11 USD, 12 CAD')
        self.assertEqual(expect_updated, inv_updated)
        self.assertEqual(expect_updated, inv1)

    def test_sum_inventories(self):
        inv1 = Inventory()
        inv1.add_amount(A('10 USD'))

        inv2 = Inventory()
        inv2.add_amount(A('20 CAD'))
        inv2.add_amount(A('55 HOOL'))

        inv1 + inv2


class TestDefaultTolerance(unittest.TestCase):

    def test_default_tolerance__present(self):
        self.assertEqual(
            D('0.001'),
            inventory.get_tolerance({'USD': D('0.001')},
                                    {},
                                    'USD'))
        self.assertEqual(
            D('0.001'),
            inventory.get_tolerance({'USD': D('0.001')},
                                    {'USD': D('0.00001')},
                                    'USD'))
        self.assertEqual(
            D('0.001'),
            inventory.get_tolerance({'USD': D('0.001')},
                                    {'*': D('0.5')},
                                    'USD'))

    def test_default_tolerance__global(self):
        self.assertEqual(
            D('0.001'),
            inventory.get_tolerance({},
                                    {'USD': D('0.001'), '*': D('0.5')},
                                    'USD'))

    def test_default_tolerance__global_default(self):
        self.assertEqual(
            D('0.5'),
            inventory.get_tolerance({},
                                    {'USD': D('0.001'), '*': D('0.5')},
                                    'JPY'))

    def test_default_tolerance__not_found(self):
        self.assertEqual(
            ZERO,
            inventory.get_tolerance({'USD': D('0.001')}, {},
                                    'JPY'))
