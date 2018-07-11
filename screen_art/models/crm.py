from odoo import api, fields, models, tools, SUPERUSER_ID, _
from datetime import datetime


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    email_domain = fields.Char("Email Domain")
    design_name = fields.Char("Design Name")
    original_artwork = fields.Char('Original Artwork')
    design_size = fields.Char('Design Size')
    print_quality = fields.Char("Print Quality")
    # design_material = fields.Selection([('pvc_free','PVC Free'),('pathalate_free','PTHALATE FREE'),('with_pvc','With PVC')],string='Design Material')
    pantone_no = fields.Integer('Pantone No')
    fabric_gr_colour = fields.Char('Fabric/Ground Colour')
    fabric_quality = fields.Char('Fabric Quality')
    order_quantity = fields.Integer('Order Quantity(Tentative)')
    need_sample = fields.Selection([('yes','Yes'),('no','No')],string='Need Samples')
    sample_qty = fields.Integer('Sample Qty')
    sample_size = fields.Char('Sample Size')
    sample_colour = fields.Char('Sample Colour')
    courier_mode = fields.Char('Mode Of Courier')
    road_permit = fields.Char('Road Permit')
    destination = fields.Char('Destination')
    account_details = fields.Char('Account Details')
    reference = fields.Char('Reference')
    comment = fields.Text('Comment')
    design_priority = fields.Selection([('normal','Normal'),('medium','Medium'),('high','High')],required=True,string='Design Priority')

    
    @api.model
    def create(self, vals):
        print "inside create================="
        res = super(CrmLead, self).create(vals)
        email= vals.get('email_from')
        if email:
            domain = email.split('@')
            res.email_domain = domain[1].strip('>')
        print "email_domain===============",res.email_domain
        return res
    
    def send_requirement_mail(self):
        print "send requirement mail============"
        stage_id = self.env['crm.stage'].search([('probability','=','30')])
        print "stage_id=============",stage_id
        self.write({'stage_id':stage_id.id})
    
    def send_followup_mail(self):
        print "send followup mail======================="
        
    def make_art_work(self):
        print "make art work===============",self,datetime.now()
        design_obj = self.env['design']
        design_id = design_obj.create({
                                'date' : datetime.now(),
                                'merchant_name': self.user_id.id,
                                'ref' : self.reference,
                                'design_name' : self.design_name,
                                'quality' : self.fabric_quality,
                                'design_priority' : self.design_priority,
                                'merchant_comment' :self.comment,
                                       })
        print "design_id=========================",design_id
        stage_id = self.env['crm.stage'].search([('probability','=','50')])
        print "stage_id=============",stage_id
        self.write({'stage_id':stage_id.id})
        
    def procced_for_approval(self):
        print "procced_for_approval==============",self
        stage_id = self.env['crm.stage'].search([('probability','=','100')])
        print "stage_id=============",stage_id
        self.write({'stage_id':stage_id.id})
        
        
    
    
    
    