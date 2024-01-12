# This file is part of the sale_payment module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond import backend
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval


class User(metaclass=PoolMeta):
    __name__ = "res.user"
    sale_device = fields.Many2One('sale.device', 'Sale Device',
            domain=[('shop', '=', Eval('shop'))])

    @classmethod
    def __setup__(cls):
        super(User, cls).__setup__()
        if 'sale_device' not in cls._context_fields:
            cls._context_fields.insert(0, 'sale_device')

    @classmethod
    def __register__(cls, module_name):
        table = backend.TableHandler(cls, module_name)

        # Migrate from sale_pos 3.0
        old_column = 'pos_device'
        new_column = 'sale_device'
        if table.column_exist(old_column):
            table.drop_fk(old_column)
            table.column_rename(old_column, new_column)

        super(User, cls).__register__(module_name)

    def on_change_company(self):
        super().on_change_company()
        self.sale_device = None

    @classmethod
    def _get_preferences(cls, user, context_only=False):
        res = super(User, cls)._get_preferences(user,
            context_only=context_only)
        if not context_only:
            res['sale_device'] = user.sale_device and user.sale_device.id or None
        return res
