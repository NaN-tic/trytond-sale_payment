# This file is part of the sale_payment module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import device
from . import invoice
from . import sale
from . import statement
from . import user

module = 'sale_payment'

def register():
    Pool.register(
        device.SaleDevice,
        device.SaleDeviceStatementJournal,
        invoice.Invoice,
        sale.Sale,
        sale.SalePaymentForm,
        statement.Journal,
        statement.Statement,
        statement.Line,
        statement.OpenStatementStart,
        statement.OpenStatementDone,
        statement.CloseStatementStart,
        statement.CloseStatementDone,
        user.User,
        module=module, type_='model')
    Pool.register(
        sale.WizardSalePayment,
        sale.WizardSaleReconcile,
        statement.OpenStatement,
        statement.CloseStatement,
        module=module, type_='wizard')
