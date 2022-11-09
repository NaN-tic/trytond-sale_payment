# This file is part of the sale_payment module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond import backend
from trytond.model import ModelSQL, ModelView, fields
from trytond.pyson import Eval


__all__ = ['SaleDevice', 'SaleDeviceStatementJournal']


class SaleDevice(ModelSQL, ModelView):
    'Sale Device Configuration'
    __name__ = 'sale.device'
    name = fields.Char('Device Name', required=True)
    shop = fields.Many2One('sale.shop', 'Shop', required=True)
    company = fields.Function(fields.Many2One('company.company', 'Company',),
        'get_company', searcher='search_company')
    journals = fields.Many2Many('sale.device.account.statement.journal',
        'device', 'journal', 'Journals', depends=['company'],
        domain=[
            ('company', '=', Eval('company')),
            ]
        )
    journal = fields.Many2One('account.statement.journal', "Default Journal",
        ondelete='RESTRICT', depends=['journals'],
        domain=[('id', 'in', Eval('journals', []))],
        )
    users = fields.One2Many('res.user', 'sale_device', 'Users')

    @classmethod
    def __register__(cls, module_name):

        old_table = 'sale_pos_device'
        if backend.TableHandler.table_exist(old_table):
            backend.TableHandler.table_rename(old_table, cls._table)

        super(SaleDevice, cls).__register__(module_name)

    @fields.depends('shop')
    def on_change_shop(self):
        self.company = self.shop.company.id if self.shop else None

    def get_company(self, name):
        return self.shop.company.id

    @classmethod
    def search_company(cls, name, clause):
        return [('shop.%s' % name,) + tuple(clause[1:])]


class SaleDeviceStatementJournal(ModelSQL):
    'Sale Device - Statement Journal'
    __name__ = 'sale.device.account.statement.journal'
    _table = 'sale_device_account_statement_journal'
    device = fields.Many2One('sale.device', 'Sale Device',
            ondelete='CASCADE', required=True)
    journal = fields.Many2One('account.statement.journal', 'Statement Journal',
            ondelete='RESTRICT', required=True)

    @classmethod
    def __register__(cls, module_name):
        table = backend.TableHandler(cls, module_name)

        old_table = 'sale_pos_device_account_statement_journal'
        if backend.TableHandler.table_exist(old_table):
            backend.TableHandler.table_rename(old_table, cls._table)

        old_column = 'pos_device'
        new_column = 'device'
        if table.column_exist(old_column):
            table.drop_fk(old_column)
            table.column_rename(old_column, new_column)

        super(SaleDeviceStatementJournal, cls).__register__(module_name)
