# This file is part of the sale_payment module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond import backend
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval


__all__ = ['User']


class User(metaclass=PoolMeta):
    __name__ = "res.user"
    sale_device = fields.Many2One('sale.device', 'Sale Device',
            domain=[('shop', '=', Eval('shop'))],
            depends=['shop']
    )

    @classmethod
    def __setup__(cls):
        super(User, cls).__setup__()
        if 'sale_device' not in cls._preferences_fields:
            cls._preferences_fields.extend([
                    'sale_device',
                    ])

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        table = TableHandler(cls, module_name)

        # Migrate from sale_pos 3.0
        old_column = 'pos_device'
        new_column = 'sale_device'
        if table.column_exist(old_column):
            table.drop_fk(old_column)
            table.column_rename(old_column, new_column)

        super(User, cls).__register__(module_name)
