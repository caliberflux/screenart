from odoo import api, fields, models, tools, SUPERUSER_ID,_
from datetime import datetime

class QuotationApprovalWizard(models.Model):
    _name= "quotation.approval.wizard"
    
    name=fields.Char("name")
    
    def quotation_second_approval(self):
        active_id=self._context.get('active_id',False)
        sale_order_id = self.env['sale.order'].browse(active_id)
        sale_order_id.state='quot_approval2'

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'sale.order' and self._context.get('default_res_id') and self._context.get('mark_so_as_sent'):
            order = self.env['sale.order'].browse([self._context['default_res_id']])
            if order.state in ('quot_approval1','quot_approval2','revised_quot'):
                order.with_context(tracking_disable=True).state = 'sent'
            self = self.with_context(mail_post_autofollow=True)
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
     
class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    @api.depends('design_details_ids.price_subtotal')
    def get_quotation_total(self):
        for order in self:
            amount_total = 0.0
            for line in order.design_details_ids:
                amount_total += float(line.price_subtotal)
            order.update({
                'quotation_amount_total': amount_total,
            })
    
    @api.multi
    def _revised_count(self):
        for sale in self:
            revised_count = sale.search([('parent_so_id', '=', sale.id)])
            sale.revised_order_count = len(revised_count)

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('quot_approval1','First Approval'),
        ('quot_approval2','Second Approval'),
        ('sent', 'Quotation Sent'),
        ('revised_quot','Revised Quotation'),
        ('revised', 'Revised'),
        ('sample_order','Sample Order'),
        ('sample_approval','Sample Approval'),
        ('production_order','Production Order'),
        ('job_order','Job Order'),
        ('sale', 'Delivered'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True,track_visibility='onchange', default='draft')
    job_order_type = fields.Selection([
        ('original', 'Original'),
        ('revised','Revised'),
        ('replacement', 'Replacement'),
        ('shortage','Shortage'),
        ('projection','Projection'),
        ('diamond','Diamond'),
        ('merge', 'Merge'),
        ], string='Job Order Type',default='original',required=True)
    mode_of_production = fields.Selection([('sample', 'Need Sample'),('production','Direct Production'),], string='Mode Of Production',states={'sent': [('required', True)]})
    parent_so_id = fields.Many2one('sale.order', 'Parent SO')
    revised_order_count = fields.Integer(string='# of Revised Orders', compute='_revised_count')
    revision_number = fields.Integer(string='Revision', copy=False, default=1)
    org_name = fields.Char(string='Origin', copy=False)
    design_details_ids = fields.One2many('design.details', 'sale_order_id','Design Details Line',copy=True)
    # revised_qoutation_ids = fields.One2many('revised.qoutation', 'sale_order_id', 'Revised Quotation')
    quotation_amount_total = fields.Monetary(string='Total Amount', store=True, readonly=True, compute='get_quotation_total', track_visibility='always')
    unit = fields.Char('UNIT')
    dispatch_date = fields.Date("DISPATCH DATE")
    note = fields.Text('NOTE')
    job_sheet_date = fields.Date('Job Sheet Date')
    approved_by = fields.Many2one('res.users', 'Approved By')
    factory_id = fields.Many2one('factory',string="Factory")
    factory_member = fields.Many2one('hr.employee',string="Factory member")
    factory_distributuion_ids = fields.Many2many('factory','factory_order_rel','factory_id','order_id',string='Factory Distribution')
    mode_of_production = fields.Selection([('sample', 'Need Sample'),('production','Direct Production'),], string='Mode Of Production')
    source = fields.Selection([('screen_art', 'Screen Art'),('out_source','Out Source'),], string='Source')
    
    def quotation_first_approval(self):
        self.state='quot_approval1'
        
    def approve_quotation(self):
        return {
            'name': _('Approval'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'quotation.approval.wizard',
            'type': 'ir.actions.act_window',
            'target' : 'new',
        }
    
    def approve_job_order(self):
        self.state="job_order"
        self.approved_by = self._uid
    
    @api.multi
    def revised_quotation(self):
        for rec in self:
            if not rec.org_name:
                namee = rec.name + '/R' + str(rec.revision_number)
                rec.org_name = rec.name
            else:
                namee = rec.org_name + '/R' + str(rec.revision_number)
            if not rec.org_name:
                names = rec.name
            else:
                names = rec.org_name
            vals = {
                'name': names + "-" + str(rec.revision_number),
                'state': 'revised',
                'parent_so_id': rec.id,
                'date_order': rec.date_order,
            }
            new_so_copy = rec.copy(default=vals)
            rec.state = 'revised_quot'
            rec.name = namee
            rec.date_order = datetime.now()
            rec.revision_number += 1

    def product_creation(self):
        if self.mode_of_production == 'sample':
            self.state = 'sample_order'
        if self.mode_of_production == 'production':
            self.state = 'production_order'
    
    @api.multi
    def js_with_client(self):
        context = self._context
        return self.env['report'].get_action(self, 'screen_art.report_original_job_order_sheet_template')
    
    @api.multi
    def js_without_client(self):
        return self.env['report'].get_action(self, 'screen_art.report_original_job_order_sheet_template_without_client_details')
            
class ProductStockDetailsLines(models.Model):
    _name = "product.stock.details.lines"
    
    combo_name = fields.Char("Combo Name")
    size = fields.Char("Size")
    balance_stock_qty = fields.Integer("Balance Stock Qty")
    allocated_stock_qty = fields.Integer("Allocated Stock Qty")
    order_qty = fields.Integer("Order Qty")
    print_qty = fields.Integer("Print Qty")
    sale_line_id = fields.Many2one('sale.order.line')
            
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    design_sequence = fields.Char("Design Sequence")
    design_size = fields.Char("Design Size")
    product_stock_details_ids = fields.One2many('product.stock.details.lines','sale_line_id')
    
    @api.multi
    def get_combo_name(self):
        combo_name_list = []
        for i in self:
            for j in i.product_stock_details_ids:
                combo_name_list.append(j.combo_name)
        return list(set(combo_name_list))
    
    def stock_details(self):
        
        if self.product_stock_details_ids:
            return {
            'name': _('Stock Details'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.line',
            'view_id': self.env.ref('screen_art.wizard_sale_order_line_sart').id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'target': 'new',
            # 'context':{'default_sale_line_id' : self.id}
            }
        
        else:
            print "inside else=============================",self
            combo_details = self.product_id.combo_details_ids
            print "combo_details==================",combo_details
            list1=[]
            for combo in combo_details:
                print "size=============",combo.combo_size
                for size_id in combo.combo_size:
                    val={
                        'combo_name':combo.combo_name,
                        'size': size_id.size,
                        }
                    print "val===================",val
                    list1.append((0,0,val))
                print "list=======",list1
            self.product_stock_details_ids = list1
                
            return {
                'name': _('Stock Details'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.order.line',
                'view_id': self.env.ref('screen_art.wizard_sale_order_line_sart').id,
                'type': 'ir.actions.act_window',
                'res_id': self.id,
                'target': 'new',
                # 'context':{'default_product_stock_details_ids' : list1}
                }
    @api.multi
    def save(self):
        return True
    
    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id.id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            
            order_id = self._context.get('sale_order_id',False)
            design_id = self.env['design.details'].search([('sale_order_id','=',order_id),('sequence_name','=',self.design_sequence)])
            if design_id:
                self.price_unit = design_id.price
                self.design_size = design_id.size
                self.product_uom_qty = design_id.quantity
           