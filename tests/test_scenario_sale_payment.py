import unittest
from decimal import Decimal

from proteus import Model, Wizard
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear, create_tax,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.modules.sale_shop.tests.tools import create_shop
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install sale
        config = activate_modules(['party', 'sale_payment'])

        # Create company
        _ = create_company()
        company = get_company()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        receivable = accounts['receivable']
        revenue = accounts['revenue']
        expense = accounts['expense']
        cash = accounts['cash']

        # Create tax
        tax = create_tax(Decimal('.10'))
        tax.save()

        # Create parties
        Party = Model.get('party.party')
        customer = Party(name='Customer')
        customer.account_receivable = receivable
        customer.save()

        # Create category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name='Category')
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.customer_taxes.append(tax)
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        product = Product()
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'service'
        template.salable = True
        template.list_price = Decimal('10')
        template.account_category = account_category
        product, = template.products
        product.cost_price = Decimal('5')
        template.save()
        product, = template.products

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create product price list
        PriceList = Model.get('product.price_list')
        price_list = PriceList(name='Retail', price='list_price')
        price_list_line = price_list.lines.new()
        price_list_line.formula = 'unit_price'
        price_list.save()
        customer.sale_price_list = price_list
        customer.save()

        # Create Sale Shop
        Shop = Model.get('sale.shop')
        shop = create_shop(payment_term, price_list)
        shop.save()

        # Create journals
        StatementJournal = Model.get('account.statement.journal')
        Journal = Model.get('account.journal')
        Sequence = Model.get('ir.sequence')
        SequenceType = Model.get('ir.sequence.type')
        sequence_type, = SequenceType.find([('name', '=', 'Account Journal')])
        sequence = Sequence(
            name='Statement',
            sequence_type=sequence_type,
            company=company,
        )
        sequence.save()
        account_journal = Journal(
            name='Statement',
            type='statement',
            sequence=sequence,
        )
        account_journal.save()
        statement_journal = StatementJournal(
            name='Default',
            journal=account_journal,
            account=cash,
            validation='balance',
        )
        statement_journal.save()

        # Create a device
        Device = Model.get('sale.device')
        device = Device()
        device.shop = shop
        device.name = 'Default'
        device.journals.append(statement_journal)
        device.journal = statement_journal
        device.save()

        # Reload the context
        User = Model.get('res.user')
        Group = Model.get('res.group')
        user, = User.find([('login', '=', 'admin')])
        user.shops.append(shop)
        user.shop = shop
        user.sale_device = device
        user.save()
        config._context = User.get_preferences(True, config.context)

        # Create sale user
        shop = Shop(shop.id)
        sale_user = User()
        sale_user.name = 'Sale'
        sale_user.login = 'sale'
        sale_group, = Group.find([('name', '=', 'Sales')])
        sale_user.groups.append(sale_group)
        sale_user.shops.append(shop)
        sale_user.shop = shop
        sale_user.sale_device = device
        sale_user.save()

        # Create account user
        shop = Shop(shop.id)
        account_user = User()
        account_user.name = 'Account'
        account_user.login = 'account'
        account_group, = Group.find([('name', '=', 'Accounting')])
        account_user.groups.append(account_group)
        account_user.shops.append(shop)
        account_user.shop = shop
        account_user.sale_device = device
        account_user.save()

        # Sale services
        config.user = sale_user.id
        Sale = Model.get('sale.sale')
        sale = Sale()
        sale.party = customer
        sale_line = sale.lines.new()
        sale_line.product = product
        sale_line.quantity = 2.0
        sale.save()
        self.assertEqual(len(sale.shipments), 0)
        self.assertEqual(len(sale.invoices), 0)
        self.assertEqual(len(sale.payments), 0)

        # Open statements for current device
        Statement = Model.get('account.statement')
        self.assertEqual(len(Statement.find([('state', '=', 'draft')])), 0)
        open_statment = Wizard('open.statement')
        open_statment.execute('create_')
        self.assertEqual(open_statment.form.result, 'Statement Default opened.')
        payment_statement, = Statement.find([('state', '=', 'draft')])

        # Partially pay the sale
        pay_sale = Wizard('sale.payment', [sale])
        self.assertEqual(pay_sale.form.journal, statement_journal)
        self.assertEqual(pay_sale.form.payment_amount, Decimal('22.00'))
        pay_sale.form.payment_amount = Decimal('12.00')
        pay_sale.execute('pay_')
        sale.invoice_state = 'waiting'
        sale.save()
        statment_line, = payment_statement.lines
        self.assertEqual(statment_line.amount, Decimal('12.00'))
        self.assertEqual(statment_line.party, customer)
        self.assertEqual(statment_line.sale, sale)
        sale.reload()
        self.assertEqual(sale.paid_amount, Decimal('12.00'))
        self.assertNotEqual(sale.invoice_state, None)
        self.assertEqual(sale.residual_amount, Decimal('10.00'))
        self.assertEqual(len(sale.shipments), 0)
        self.assertEqual(len(sale.invoices), 0)
        self.assertEqual(len(sale.payments), 1)

        # When the sale is paid invoice is generated
        self.assertEqual(pay_sale.form.payment_amount, Decimal('10.00'))
        pay_sale.execute('pay_')
        payment_statement.reload()
        _, statement_line = payment_statement.lines
        self.assertEqual(statement_line.amount, Decimal('10.00'))
        self.assertEqual(statement_line.party, customer)
        self.assertEqual(statement_line.sale, sale)
        sale.reload()
        self.assertEqual(sale.paid_amount, Decimal('22.00'))
        self.assertEqual(sale.residual_amount, Decimal('0.00'))
        self.assertEqual(len(sale.shipments), 0)
        self.assertEqual(len(sale.invoices), 1)
        self.assertEqual(len(sale.payments), 2)

        # An invoice should be created for the sale
        invoice, = sale.invoices
        config.user = account_user.id
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.untaxed_amount, Decimal('20.00'))
        self.assertEqual(invoice.tax_amount, Decimal('2.00'))
        self.assertEqual(invoice.total_amount, Decimal('22.00'))

        # When the statement is closed the invoices are paid and sale is done
        close_statment = Wizard('close.statement')
        close_statment.execute('validate')
        self.assertEqual(close_statment.form.result,
                         'Statement Default - Default closed.')
        payment_statement.reload()
        self.assertEqual(payment_statement.state, 'validated')
        self.assertEqual(
            all(l.related_to == invoice for l in payment_statement.lines), True)
        self.assertEqual(payment_statement.balance, Decimal('22.00'))
        invoice.reload()
        self.assertEqual(invoice.state, 'paid')
        config.user = sale_user.id
        sale.reload()
        self.assertEqual(sale.state, 'done')
