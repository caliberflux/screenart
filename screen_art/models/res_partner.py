from odoo import api, fields, models, tools, SUPERUSER_ID, _


class ResPartner(models.Model):
    _inherit = "res.partner"
    
    gstin_no = fields.Char("GSTIN")
    company_name = fields.Char('Company Name')
    customer_code = fields.Char('Customer Code')