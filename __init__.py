# This file is part of the sale_payment module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .device import *
from .sale import *
from .statement import *
from .user import *


def register():
    Pool.register(
        Journal,
        Statement,
        Line,
        SaleDevice,
        User,
        SaleDeviceStatementJournal,
        Sale,
        SalePaymentForm,
        OpenStatementStart,
        OpenStatementDone,
        CloseStatementStart,
        CloseStatementDone,
        module='sale_payment', type_='model')
    Pool.register(
        WizardSalePayment,
        WizardSaleReconcile,
        OpenStatement,
        CloseStatement,
        module='sale_payment', type_='wizard')
