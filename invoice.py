# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import PoolMeta, Pool
from trytond.model import ModelView, Workflow, fields


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    @ModelView.button
    @Workflow.transition('posted')
    def post(cls, invoices):
        pool = Pool()
        SaleLine = pool.get('sale.line')

        payments = {}
        for invoice in invoices:
            if invoice.type == 'out':
                origins = []
                invoice_payments = []
                for line in invoice.lines:
                    if (line.origin and isinstance(line.origin, SaleLine)
                            and line.origin.sale not in origins):
                        origins.append(line.origin.sale)
                        for payment in line.origin.sale.payments:
                            if payment.move:
                                for line in payment.move.lines:
                                    if line.account == payment.account:
                                        invoice_payments.append(line)
                if invoice_payments:
                    payments[invoice] = invoice_payments
        cls.add_payment_lines(payments)
        super().post(invoices)
