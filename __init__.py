# This file is part of the sale_payment module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import device
from . import sale
from . import statement
from . import user


def register():
    Pool.register(
        statement.Journal,
        statement.Statement,
        statement.Line,
        device.SaleDevice,
        user.User,
        device.SaleDeviceStatementJournal,
        sale.Sale,
        sale.SalePaymentForm,
        statement.OpenStatementStart,
        statement.OpenStatementDone,
        statement.CloseStatementStart,
        statement.CloseStatementDone,
        module='sale_payment', type_='model')
    Pool.register(
        sale.WizardSalePayment,
        sale.WizardSaleReconcile,
        statement.OpenStatement,
        statement.CloseStatement,
        module='sale_payment', type_='wizard')
