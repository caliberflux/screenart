from odoo import api, fields, models, tools, SUPERUSER_ID, _
from datetime import datetime, timedelta

class Design(models.Model):
	_name = 'design'
	_rec_name = 'merchant_name'

	date = fields.Datetime(string="Date")
	merchant_name = fields.Many2one('res.users', 'Merchant Name')
	ref = fields.Char(string='Reference')
	design_name = fields.Char(string='Design Name')
	quality = fields.Char(string='Quality')
	start_time = fields.Datetime(string='Started On', states={'progress': [('readonly', True)]})
	end_time = fields.Datetime(string='End Time')
	started_by = fields.Many2one('res.users', 'Started By', states={'progress': [('readonly', True)]})
	finished_by = fields.Many2one('res.users', 'Finished By', states={'done': [('readonly', True)]})
	completion_datetime = fields.Datetime(string="Finished On")
	merchant_comment = fields.Text(string="Merchant Comment")
	design_dept_comment = fields.Text(string="Design Department Comment")
	design_priority = fields.Selection([('normal','Normal'),('medium','Medium'),('high','High')],readonly=True,string='Design Priority')
	state = fields.Selection([('draft', 'Draft'), ('progress', 'Progress'), ('pending', 'Pending'), ('done', 'Done')], default='draft')

	@api.multi
	def start(self):
		self.state = 'progress'
		self.start_time = datetime.now()
		self.started_by = self.env.user.id
		
	@api.multi
	def done(self):
		self.state = 'done'
		self.finished_by = self.env.user.id
		self.completion_datetime = datetime.now()

	@api.multi
	def _cron_design_exceed_24_hrs(self):
		records = self.env['design'].search([('state', '=', 'progress')])
		current_time = datetime.now()
		for rec in records:
			start_time = fields.Datetime.from_string(rec.start_time)
			time_limit_exceed = ((current_time - start_time).total_seconds())/3600
			if time_limit_exceed == 24 or time_limit_exceed > 24:
				rec.state = 'pending'

class DesignDetails(models.Model):
	_name = "design.details"
	
	@api.depends('quantity', 'price')
	def _compute_amount(self):
		price_amount = 0.0
		for line in self:
			price_amount = (line.price * line.quantity)
			line.update({
				'price_subtotal': price_amount,
			})

	sequence_name = fields.Char('Sequence',readonly=True)
	product_name = fields.Char('Design Name')
	colour = fields.Char('Colour')
	combo = fields.Char('Combo')
	quality = fields.Char('Quality')
	design_image = fields.Binary('Design')
	quantity = fields.Integer('Qty')
	size = fields.Char('Size')
	price = fields.Float('Price/pc')
	price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True)
	sale_order_id = fields.Many2one('sale.order','Sale Order')
	
	@api.model
	def create(self, values):
		if not values.get('sequence_name', False):
			values['sequence_name'] = self.env['ir.sequence'].next_by_code('design.details')
		return super(DesignDetails, self).create(values)
			
