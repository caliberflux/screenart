from odoo import api, fields, models, tools, SUPERUSER_ID,_

class Factory(models.Model):
    _name= "factory"
    
    name = fields.Char("Factory Name",required=True)
    emoloyee_ids = fields.One2many('hr.employee','factory_id')


class Employee(models.Model):
    _inherit = "hr.employee"
    
    factory_id = fields.Many2one('factory',string="Factory")