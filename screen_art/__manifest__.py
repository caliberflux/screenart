# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Screen Art',
    'version': '1.0',
    'category': 'Hidden',
    'description': """Screen Art Design System""",
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['crm','sale','purchase','stock','hr','india_gst','mrp'],
    'data': [
        'data/design_exceed_time_data.xml',
        'views/product_view.xml',
        'views/res_partner_view.xml',
        'views/design_view.xml',
        'views/crm_view.xml',
        'views/sale_view.xml',
        'views/hr_view.xml',
        'report/report_sale_order.xml',
        'report/report_register.xml',
        'report/original_job_order.xml',
        'report/proforma_invoice.xml',
        'report/tax_invoice.xml',
        'views/account_view.xml',
        ],  
    'installable': True, 
    'application': False,
    'auto_install': False,
}
