# This file is part of the sale_payment module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.wizard import Button, StateTransition, StateView, Wizard
from decimal import Decimal
from trytond.i18n import gettext


__all__ = ['Journal', 'Statement', 'Line', 'OpenStatementStart',
    'OpenStatementDone', 'OpenStatement', 'CloseStatementStart',
    'CloseStatementDone', 'CloseStatement']


class Journal(metaclass=PoolMeta):
    __name__ = 'account.statement.journal'
    devices = fields.One2Many('sale.device', 'journal', 'Devices')


class Statement(metaclass=PoolMeta):
    __name__ = 'account.statement'
    users = fields.Function(fields.One2Many('res.user', None, 'Users'),
        'get_users', searcher='search_users')

    @classmethod
    def get_users(cls, statements, names):
        return {'users': {s.id: [u.id
                    for j in s.journal
                    for d in j.devices
                    for u in d.users
                    ]
                } for s in statements}

    @classmethod
    def search_users(cls, name, clause):
        pool = Pool()
        Journal = pool.get('account.statement.journal')
        Device = pool.get('sale.device')
        DeviceJournal = pool.get('sale.device.account.statement.journal')
        User = pool.get('res.user')

        statement = cls.__table__()
        journal = Journal.__table__()
        device = Device.__table__()
        device_journal = DeviceJournal.__table__()
        user = User.__table__()

        query = statement.join(
                journal, condition=statement.journal == journal.id).join(
                device_journal,
                    condition=journal.id == device_journal.journal).join(
                device, condition=device_journal.device == device.id).join(
                user, condition=device.id == user.sale_device).select(
                statement.id,
                where=user.id == clause[2])
        return [('id', 'in', query)]


class Line(metaclass=PoolMeta):
    __name__ = 'account.statement.line'
    sale = fields.Many2One('sale.sale', 'Sale', ondelete='RESTRICT')

    def create_move(self):
        '''
        Create move for the statement line and return move if created.
        Redefined method to allow amounts in statement lines greater than the
        invoice amount.
        '''
        pool = Pool()
        Move = pool.get('account.move')
        Period = pool.get('account.period')
        Invoice = pool.get('account.invoice')
        Currency = pool.get('currency.currency')
        MoveLine = pool.get('account.move.line')

        if self.move:
            return

        period_id = Period.find(self.statement.company.id, date=self.date)

        move_lines = self._get_move_lines()
        move = Move(
            period=period_id,
            journal=self.statement.journal.journal,
            date=self.date,
            origin=self,
            lines=move_lines,
            )
        move.save()

        self.write([self], {
                'move': move.id,
                })

        if self.invoice:
            with Transaction().set_context(date=self.invoice.currency_date):
                amount = Currency.compute(self.statement.journal.currency,
                    self.amount, self.statement.company.currency)

            reconcile_lines = self.invoice.get_reconcile_lines_for_amount(
                abs(amount))

            for move_line in move.lines:
                if move_line.account == self.invoice.account:
                    Invoice.write([self.invoice], {
                            'payment_lines': [('add', [move_line.id])],
                            })
                    break
            if reconcile_lines[1] == Decimal('0.0'):
                lines = reconcile_lines[0] + [move_line]
                MoveLine.reconcile(lines)
        return move


class OpenStatementStart(ModelView):
    'Open Statement'
    __name__ = 'open.statement.start'


class OpenStatementDone(ModelView):
    'Open Statement'
    __name__ = 'open.statement.done'
    result = fields.Text('Result', readonly=True)


class OpenStatement(Wizard):
    'Open Statement'
    __name__ = 'open.statement'
    start = StateView('open.statement.start',
        'sale_payment.open_statement_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'create_', 'tryton-ok', default=True),
            ])
    create_ = StateTransition()
    done = StateView('open.statement.done',
        'sale_payment.open_statement_done', [
            Button('Done', 'end', 'tryton-ok', default=True),
            ])

    def default_done(self, fields):
        return {
            'result': self.result,
            }

    def transition_create_(self):
        pool = Pool()
        User = pool.get('res.user')
        Statement = pool.get('account.statement')

        user = Transaction().user
        user = User(user)
        device = user.sale_device
        if device:
            journals = [j.id for j in device.journals]
            statements = Statement.search([
                    ('journal', 'in', journals),
                    ], order=[
                    ('date', 'ASC'),
                    ])
            journals_of_draft_statements = [s.journal for s in statements
                if s.state == 'draft']
            start_balances = {
                s.journal.id: s.end_balance or Decimal('0.0')
                for s in statements
                }
            vlist = []
            result = ''
            for journal in device.journals:
                if journal not in journals_of_draft_statements:
                    values = {
                        'name': '%s - %s' % (device.rec_name, journal.rec_name),
                        'journal': journal.id,
                        'company': user.company.id,
                        'start_balance': start_balances.get(journal.id,
                            Decimal('0.0')),
                        'end_balance': Decimal('0.0'),
                        }
                    vlist.append(values)
                    result += gettext('sale_payment.open_statement',
                        journal=journal.rec_name)
                else:
                    result += gettext('sale_payment.statement_already_opened',
                        journal=journal.rec_name)
            statements.extend(Statement.create(vlist))
            self.result = result
        else:
            self.result = gettext('sale_payment.user_without_device',
                user=user.rec_name)
        return 'done'


class CloseStatementStart(ModelView):
    'Close Statement'
    __name__ = 'close.statement.start'


class CloseStatementDone(ModelView):
    'Close Statement'
    __name__ = 'close.statement.done'
    result = fields.Text('Result', readonly=True)


class CloseStatement(Wizard):
    'Close Statement'
    __name__ = 'close.statement'
    start = StateView('close.statement.start',
        'sale_payment.close_statement_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'validate', 'tryton-ok', default=True),
            ])
    validate = StateTransition()
    done = StateView('close.statement.done',
        'sale_payment.close_statement_done', [
            Button('Done', 'end', 'tryton-ok', default=True),
            ])

    def default_done(self, fields):
        return {
            'result': self.result,
            }

    def transition_validate(self):
        pool = Pool()
        User = pool.get('res.user')
        Statement = pool.get('account.statement')

        user = Transaction().user
        user = User(user)
        device = user.sale_device
        if device:
            journals = [j.id for j in device.journals]
            draft_statements = {
                s.journal: s for s in Statement.search([
                        ('journal', 'in', journals),
                        ], order=[
                        ('create_date', 'ASC'),
                        ])}

            result = ''
            statements = []
            for journal in device.journals:
                statement = draft_statements.get(journal)
                if statement and statement.state == 'draft':
                    end_balance = statement.start_balance
                    for line in statement.lines:
                        end_balance += line.amount
                    statement.end_balance = end_balance
                    statement.save()
                    statements.append(statement)
                    result += gettext('sale_payment.close_statement',
                            statement=statement.rec_name)
                elif statement:
                    result += gettext('sale_payment.statement_already_closed',
                        statement=statement.rec_name)
                else:
                    result += gettext('sale_payment.not_statement_found',
                        journal=journal.rec_name)
            if statements:
                Statement.validate_statement(statements)
            self.result = result
        else:
            self.result = gettext('sale_payment.user_without_device',
                user=user.rec_name)
        return 'done'
