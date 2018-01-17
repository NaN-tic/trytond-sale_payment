# This file is part of the sale_payment module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from sql import Cast, Literal
from sql.aggregate import Sum
from sql.conditionals import Coalesce
from sql.functions import Substring, Position

from trytond.model import ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Not
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateView, StateTransition, Button


__all__ = ['Sale', 'SalePaymentForm', 'WizardSalePayment',
    'WizardSaleReconcile']


class Sale:
    __metaclass__ = PoolMeta
    __name__ = 'sale.sale'
    payments = fields.One2Many('account.statement.line', 'sale', 'Payments')
    paid_amount = fields.Function(fields.Numeric('Paid Amount', readonly=True),
        'get_paid_amount')
    residual_amount = fields.Function(fields.Numeric('Residual Amount'),
        'get_residual_amount', searcher='search_residual_amount')
    sale_device = fields.Many2One('sale.device', 'Sale Device',
            domain=[('shop', '=', Eval('shop'))],
            depends=['shop'], states={
                'readonly': Eval('state') != 'draft',
                }
    )

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls._buttons.update({
                'wizard_sale_payment': {
                    'invisible': Eval('state') == 'done',
                    'readonly': Not(Bool(Eval('lines'))),
                    },
                })
        cls._error_messages.update({
                'not_customer_invoice': ('A customer invoice/refund '
                    'from sale device (%s) has not been created.'),
                })

    @staticmethod
    def default_sale_device():
        User = Pool().get('res.user')
        user = User(Transaction().user)
        return user.sale_device and user.sale_device.id or None

    @classmethod
    def workflow_to_end(cls, sales):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        StatementLine = pool.get('account.statement.line')
        Date = pool.get('ir.date')

        invoices = []
        to_post = set()
        for sale in sales:
            if sale.state == 'draft':
                cls.quote([sale])
            if sale.state == 'quotation':
                cls.confirm([sale])
            if sale.state == 'confirmed':
                cls.process([sale])

            if not sale.invoices and sale.invoice_method == 'order':
                cls.raise_user_error('not_customer_invoice', (sale.reference,))

            grouping = getattr(sale.party, 'sale_invoice_grouping_method',
                False)
            if sale.invoices and not grouping:
                for invoice in sale.invoices:
                    if not invoice.state == 'draft':
                        continue
                    if not getattr(invoice, 'invoice_date', False):
                        invoice.invoice_date = Date.today()
                    if not getattr(invoice, 'accounting_date', False):
                        invoice.accounting_date = Date.today()
                    invoice.description = sale.reference
                    invoices.extend(([invoice], invoice._save_values))
                    to_post.add(invoice)

        if to_post:
            Invoice.write(*invoices)
            Invoice.post(list(to_post))

        to_write = []
        to_do = []
        for sale in sales:
            for payment in sale.payments:
                invoices = [invoice for invoice in sale.invoices
                    if invoice and invoice.state == 'posted']
                if not invoices:
                    continue
                payment.invoice = invoices[0]
                # Because of account_invoice_party_without_vat module
                # could be installed, invoice party may be different of
                # payment party if payment party has not any vat
                # and both parties must be the same
                if payment.party != invoice.party:
                    payment.party = invoice.party
                to_write.extend(([payment], payment._save_values))

            if sale.is_done():
                to_do.append(sale)

        if to_write:
            StatementLine.write(*to_write)

        if to_do:
            cls.do(to_do)

    @classmethod
    def get_paid_amount(cls, sales, names):
        result = {n: {s.id: Decimal(0) for s in sales} for n in names}
        for name in names:
            for sale in sales:
                for payment in sale.payments:
                    result[name][sale.id] += payment.amount
        return result

    @classmethod
    def get_residual_amount(cls, sales, names):
        return {
            n: {s.id: s.total_amount - s.paid_amount for s in sales}
            for n in names
            }

    @classmethod
    def search_residual_amount(cls, name, clause):
        pool = Pool()
        Sale = pool.get('sale.sale')
        SaleLine = pool.get('sale.line')
        Invoice = pool.get('account.invoice')
        InvoiceLine = pool.get('account.invoice.line')
        StatementLine = pool.get('account.statement.line')

        sale = Sale.__table__()
        saleline = SaleLine.__table__()
        invoice = Invoice.__table__()
        invoiceline = InvoiceLine.__table__()
        line = StatementLine.__table__()

        grouped = sale.join(
            line,
            type_='LEFT',
            condition=(sale.id == line.sale)
            ).select(
                sale.id,
                where=((sale.total_amount_cache != None) &
                    (sale.state.in_(['confirmed', 'processing', 'done']))),
                group_by=(sale.id),
                having=(
                    Sum(Coalesce(line.amount, 0)) < sale.total_amount_cache))

        query = grouped.join(
                saleline,
                condition=(saleline.sale == grouped.id)
            ).join(
                invoiceline,
                condition=(Cast(Substring(invoiceline.origin,
                        Position(',', invoiceline.origin) + Literal(1)),
                    SaleLine.id.sql_type().base) == saleline.id)
            ).join(
                invoice,
                condition=(invoice.id == invoiceline.invoice)
            ).select(
                grouped.id,
                where=(invoice.state == 'posted'),
                group_by=(grouped.id)
            )

        return [('id', 'in', query)]

    @classmethod
    @ModelView.button_action('sale_payment.wizard_sale_payment')
    def wizard_sale_payment(cls, sales):
        pass

    @classmethod
    def copy(cls, sales, default=None):
        if default is None:
            default = {}
        default['payments'] = None
        return super(Sale, cls).copy(sales, default)


class SalePaymentForm(ModelView):
    'Sale Payment Form'
    __name__ = 'sale.payment.form'
    journal = fields.Many2One('account.statement.journal', 'Statement Journal',
        domain=[
            ('id', 'in', Eval('journals', [])),
            ],
        depends=['journals'], required=True)
    journals = fields.One2Many('account.statement.journal', None,
        'Allowed Statement Journals')
    payment_amount = fields.Numeric('Payment amount', required=True,
        digits=(16, Eval('currency_digits', 2)),
        depends=['currency_digits'])
    currency_digits = fields.Integer('Currency Digits')
    party = fields.Many2One('party.party', 'Party', readonly=True)


class WizardSalePayment(Wizard):
    'Wizard Sale Payment'
    __name__ = 'sale.payment'
    start = StateView('sale.payment.form',
        'sale_payment.sale_payment_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Pay', 'pay_', 'tryton-ok', default=True),
        ])
    pay_ = StateTransition()

    @classmethod
    def __setup__(cls):
        super(WizardSalePayment, cls).__setup__()
        cls._error_messages.update({
                'not_sale_device': ('You have not defined a sale device for '
                    'your user.'),
                'not_draft_statement': ('A draft statement for "%s" payments '
                    'has not been created.'),
                'party_without_account_receivable': 'Party %s has no any '
                    'account receivable defined. Please, assign one.',
                })

    def default_start(self, fields):
        pool = Pool()
        Sale = pool.get('sale.sale')
        User = pool.get('res.user')
        sale = Sale(Transaction().context['active_id'])
        user = User(Transaction().user)
        sale_device = sale.sale_device or user.sale_device or False
        if user.id != 0 and not sale_device:
            self.raise_user_error('not_sale_device')
        return {
            'journal': sale_device.journal.id
                if sale_device.journal else None,
            'journals': [j.id for j in sale_device.journals],
            'payment_amount': sale.total_amount - sale.paid_amount
                if sale.paid_amount else sale.total_amount,
            'currency_digits': sale.currency_digits,
            'party': sale.party.id,
            }

    def transition_pay_(self):
        pool = Pool()
        Date = pool.get('ir.date')
        Sale = pool.get('sale.sale')
        Statement = pool.get('account.statement')
        StatementLine = pool.get('account.statement.line')

        form = self.start
        statements = Statement.search([
                ('journal', '=', form.journal),
                ('state', '=', 'draft'),
                ], order=[('date', 'DESC')])
        if not statements:
            self.raise_user_error('not_draft_statement', (form.journal.name,))

        active_id = Transaction().context.get('active_id', False)
        sale = Sale(active_id)
        if not sale.number:
            Sale.set_number([sale])

        account = (sale.party.account_receivable
            and sale.party.account_receivable.id
            or self.raise_user_error('party_without_account_receivable',
                error_args=(sale.party.name,)))

        if form.payment_amount:
            payment = StatementLine(
                statement=statements[0].id,
                date=Date.today(),
                amount=form.payment_amount,
                party=sale.party.id,
                account=account,
                description=sale.number,
                sale=active_id
                )
            payment.save()

        if sale.total_amount != sale.paid_amount:
            return 'start'
        if sale.state != 'draft':
            return 'end'

        sale.description = sale.reference
        sale.save()

        Sale.workflow_to_end([sale])

        return 'end'


class WizardSaleReconcile(Wizard):
    'Reconcile Sales'
    __name__ = 'sale.reconcile'
    start = StateTransition()
    reconcile = StateTransition()

    def transition_start(self):
        pool = Pool()
        Sale = pool.get('sale.sale')
        Line = pool.get('account.move.line')
        for sale in Sale.browse(Transaction().context['active_ids']):
            account = sale.party.account_receivable
            lines = []
            amount = Decimal('0.0')
            for invoice in sale.invoices:
                for line in invoice.lines_to_pay:
                    if not line.reconciliation:
                        lines.append(line)
                        amount += line.debit - line.credit
            for payment in sale.payments:
                if not payment.move:
                    continue
                for line in payment.move.lines:
                    if (not line.reconciliation and
                            line.account.id == account.id):
                        lines.append(line)
                        amount += line.debit - line.credit
            if lines and amount == Decimal('0.0'):
                Line.reconcile(lines)
        return 'end'
