=====================
Sale Payment Scenario
=====================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install sale::

    >>> Module = Model.get('ir.module.module')
    >>> module, = Module.find([('name', '=', 'sale_payment')])
    >>> module.click('install')
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='U.S. Dollar', symbol='$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point='.', mon_thousands_sep=',')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> FiscalYear = Model.get('account.fiscalyear')
    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> fiscalyear = FiscalYear(name=str(today.year))
    >>> fiscalyear.start_date = today + relativedelta(month=1, day=1)
    >>> fiscalyear.end_date = today + relativedelta(month=12, day=31)
    >>> fiscalyear.company = company
    >>> post_move_seq = Sequence(name=str(today.year), code='account.move',
    ...     company=company)
    >>> post_move_seq.save()
    >>> fiscalyear.post_move_sequence = post_move_seq
    >>> invoice_seq = SequenceStrict(name=str(today.year),
    ...     code='account.invoice', company=company)
    >>> invoice_seq.save()
    >>> fiscalyear.out_invoice_sequence = invoice_seq
    >>> fiscalyear.in_invoice_sequence = invoice_seq
    >>> fiscalyear.out_credit_note_sequence = invoice_seq
    >>> fiscalyear.in_credit_note_sequence = invoice_seq
    >>> fiscalyear.save()
    >>> FiscalYear.create_period([fiscalyear.id], config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> Journal = Model.get('account.journal')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')
    >>> cash, = Account.find([
    ...     ('name', '=', 'Main Cash'),
    ...     ('company', '=', company.id),
    ... ])
    >>> account_tax, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('company', '=', company.id),
    ...         ('name', '=', 'Main Tax'),
    ...         ])

Create tax::

    >>> TaxCode = Model.get('account.tax.code')
    >>> Tax = Model.get('account.tax')
    >>> tax = Tax()
    >>> tax.name = 'Tax'
    >>> tax.description = 'Tax'
    >>> tax.type = 'percentage'
    >>> tax.rate = Decimal('.10')
    >>> tax.invoice_account = account_tax
    >>> tax.credit_note_account = account_tax
    >>> invoice_base_code = TaxCode(name='invoice base')
    >>> invoice_base_code.save()
    >>> tax.invoice_base_code = invoice_base_code
    >>> invoice_tax_code = TaxCode(name='invoice tax')
    >>> invoice_tax_code.save()
    >>> tax.invoice_tax_code = invoice_tax_code
    >>> credit_note_base_code = TaxCode(name='credit note base')
    >>> credit_note_base_code.save()
    >>> tax.credit_note_base_code = credit_note_base_code
    >>> credit_note_tax_code = TaxCode(name='credit note tax')
    >>> credit_note_tax_code.save()
    >>> tax.credit_note_tax_code = credit_note_tax_code
    >>> tax.save()

Create parties::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.category = category
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('10')
    >>> template.cost_price = Decimal('5')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.customer_taxes.append(tax)
    >>> template.save()
    >>> product.template = template
    >>> product.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Direct')
    >>> payment_term_line = PaymentTermLine(type='remainder', days=0)
    >>> payment_term.lines.append(payment_term_line)
    >>> payment_term.save()

Create a shop::

    >>> Shop = Model.get('sale.shop')
    >>> PriceList = Model.get('product.price_list')
    >>> Location = Model.get('stock.location')
    >>> warehouse, = Location.find([
    ...         ('code', '=', 'WH'),
    ...         ])
    >>> price_list = PriceList()
    >>> price_list.name = 'Default price list'
    >>> price_list.save()
    >>> shop = Shop()
    >>> shop.name = 'Local shop'
    >>> shop.warehouse = warehouse
    >>> shop.shipment_method = 'order'
    >>> shop.invoice_method = 'order'
    >>> sequence, = Sequence.find([('code', '=', 'sale.sale')])
    >>> shop.sale_sequence = sequence
    >>> shop.payment_term = payment_term
    >>> shop.price_list = price_list
    >>> shop.save()

Create journals::

    >>> StatementJournal = Model.get('account.statement.journal')
    >>> sequence = Sequence(name='Satement',
    ...     code='account.journal',
    ...     company=company,
    ... )
    >>> sequence.save()
    >>> account_journal = Journal(name='Statement',
    ...     type='statement',
    ...     credit_account=cash,
    ...     debit_account=cash,
    ...     sequence=sequence,
    ... )
    >>> account_journal.save()
    >>> statement_journal = StatementJournal(name='Default',
    ...     journal=account_journal,
    ...     validation='balance',
    ... )
    >>> statement_journal.save()

Create a device::

    >>> Device = Model.get('sale.device')
    >>> device = Device()
    >>> device.shop = shop
    >>> device.name = 'Default'
    >>> device.journals.append(statement_journal)
    >>> device.journal = statement_journal
    >>> device.save()

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> user, = User.find([('login', '=', 'admin')])
    >>> user.shops.append(shop)
    >>> user.shop = shop
    >>> user.sale_device = device
    >>> user.save()
    >>> config._context = User.get_preferences(True, config.context)

Create sale user::

    >>> shop = Shop(shop.id)
    >>> sale_user = User()
    >>> sale_user.name = 'Sale'
    >>> sale_user.login = 'sale'
    >>> sale_user.main_company = company
    >>> sale_group, = Group.find([('name', '=', 'Sales')])
    >>> sale_user.groups.append(sale_group)
    >>> sale_user.shops.append(shop)
    >>> sale_user.shop = shop
    >>> sale_user.sale_device = device
    >>> sale_user.save()

Create account user::

    >>> shop = Shop(shop.id)
    >>> account_user = User()
    >>> account_user.name = 'Account'
    >>> account_user.login = 'account'
    >>> account_user.main_company = company
    >>> account_group, = Group.find([('name', '=', 'Account')])
    >>> account_user.groups.append(account_group)
    >>> account_user.shops.append(shop)
    >>> account_user.shop = shop
    >>> account_user.sale_device = device
    >>> account_user.save()

Sale services::

    >>> config.user = sale_user.id
    >>> Sale = Model.get('sale.sale')
    >>> SaleLine = Model.get('sale.line')
    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product
    >>> sale_line.quantity = 2.0
    >>> sale.save()
    >>> len(sale.shipments), len(sale.invoices), len(sale.payments)
    (0, 0, 0)

Open statements for current device::

    >>> Statement = Model.get('account.statement')
    >>> len(Statement.find([('state', '=', 'draft')]))
    0
    >>> open_statment = Wizard('open.statement')
    >>> open_statment.execute('create_')
    >>> open_statment.form.result
    u'Statement Default opened.\n'
    >>> payment_statement, = Statement.find([('state', '=', 'draft')])

Partially pay the sale::

    >>> pay_sale = Wizard('sale.payment', [sale])
    >>> pay_sale.form.journal == statement_journal
    True
    >>> pay_sale.form.payment_amount
    Decimal('22.00')
    >>> pay_sale.form.payment_amount = Decimal('12.00')
    >>> pay_sale.execute('pay_')
    >>> statment_line, = payment_statement.lines
    >>> statment_line.amount
    Decimal('12.00')
    >>> statment_line.party == customer
    True
    >>> statment_line.sale == sale
    True
    >>> sale.reload()
    >>> sale.paid_amount
    Decimal('12.00')
    >>> sale.residual_amount
    Decimal('10.00')
    >>> len(sale.shipments), len(sale.invoices), len(sale.payments)
    (0, 0, 1)

When the sale is paid invoice is generated::

    >>> pay_sale.form.payment_amount
    Decimal('10.00')
    >>> pay_sale.execute('pay_')
    >>> payment_statement.reload()
    >>> _, statement_line = payment_statement.lines
    >>> statement_line.amount
    Decimal('10.00')
    >>> statement_line.party == customer
    True
    >>> statement_line.sale == sale
    True
    >>> sale.reload()
    >>> sale.paid_amount
    Decimal('22.00')
    >>> sale.residual_amount
    Decimal('0.00')
    >>> len(sale.shipments), len(sale.invoices), len(sale.payments)
    (0, 1, 2)

An invoice should be created for the sale::

    >>> invoice, = sale.invoices
    >>> config.user = account_user.id
    >>> invoice.state
    u'posted'
    >>> invoice.untaxed_amount
    Decimal('20.00')
    >>> invoice.tax_amount
    Decimal('2.00')
    >>> invoice.total_amount
    Decimal('22.00')

When the statement is closed the invoices are paid and sale is done::

    >>> close_statment = Wizard('close.statement')
    >>> close_statment.execute('validate')
    >>> close_statment.form.result
    u'Statement Default - Default closed.\n'
    >>> payment_statement.reload()
    >>> payment_statement.state
    u'validated'
    >>> all(l.invoice == invoice for l in payment_statement.lines)
    True
    >>> payment_statement.balance
    Decimal('22.00')
    >>> invoice.reload()
    >>> invoice.state
    u'paid'
    >>> config.user = sale_user.id
    >>> sale.reload()
    >>> sale.state
    u'done'
