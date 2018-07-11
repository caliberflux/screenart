from odoo import api, fields, models, tools, SUPERUSER_ID, _

class size(models.Model):
	_name = "size"
	_rec_name = "size"
	
	size = fields.Char('Size')

class colour(models.Model):
	_name = "colour"
	_rec_name = "colour"
	
	colour = fields.Char('Colour')

class ComboDetails(models.Model):
	_name = "combo.details"
	
	@api.depends('combo_colour')
	def get_combo_name(self):
		for rec in self:
			rec.combo_name = rec.combo_colour.colour

	combo_product_id = fields.Many2one('product.template', string='Product')
	combo_name = fields.Char(compute='get_combo_name',string="Combo Name")
	combo_size = fields.Many2many('size', 'combo_size_rel','combo_id', 'size_id', string='Size')
	combo_colour = fields.Many2one('colour',string='colour')
	combo_placement = fields.Char('color Placement')
	fabric_details = fields.Char('Fabric Details')
	combo_check = fields.Boolean('Select')

class ProductProduct(models.Model):
	_inherit = "product.template"

	combo_details_ids = fields.One2many('combo.details', 'combo_product_id', string='Combo Details')
	prod_type = fields.Selection([
		('boxes', 'Boxes'),
		('commercial_catalogues','Commercial Catalogues'),
		('replacement', 'Replacement'),
		('printed_paper_tag','Printed Paper Tag'),
		('stamping_foil','Stamping Foil'),
		('transfer','Transfer[Decalcomanias]'),
		], string='Type')



