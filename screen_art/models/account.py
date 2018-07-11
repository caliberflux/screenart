from odoo import api, fields, models, tools, SUPERUSER_ID, _
from datetime import datetime
from odoo.tools import amount_to_text_en
from odoo.tools import float_is_zero, float_compare

class InvoiceTerms(models.Model):
    _name='invoice.terms'
    
    condition = fields.Char('Condition')
    invoice_id = fields.Many2one('account.invoice')

class DeliveryTerms(models.Model):
    _name='delivery.terms'
    
    name = fields.Char('Condition')
    invoice_id = fields.Many2one('account.invoice')

class Charges(models.Model):
    _name='charges'
    
    name = fields.Char('name')
    charge_type = fields.Selection([('add', 'ADD'),('minus','MINUS'),], string='Type')

class DispatchMedium(models.Model):
    _name ='dispatch.medium'
    
    name = fields.Char('Name')
    
class InvoicePrintType(models.Model):
    _name ='invoice.print.type'
    
    name = fields.Char('Name')
    
class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice', 'type','charges_ids.amount','charges_ids.tax_ids')
    def _compute_amount(self):
        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = sum(round_curr(line.amount) for line in self.tax_line_ids) + sum(round_curr(line.tax_amount) for line in self.charges_ids)
        charges_amount_add = sum(round_curr(line.amount) for line in self.charges_ids if line.charge.charge_type == 'add')
        charges_amount_minus = sum(round_curr(line.amount) for line in self.charges_ids if line.charge.charge_type == 'minus')
        self.amount_total = self.amount_untaxed + self.amount_tax + charges_amount_add - charges_amount_minus
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign
        
    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id','charges_ids.total_amount')
    def _compute_residual(self):
        residual = 0.0
        residual_company_signed = 0.0
        round_curr = self.currency_id.round
        add_tax_amount = sum(round_curr(line.tax_amount) for line in self.charges_ids)
        charges_amount_add = sum(round_curr(line.amount) for line in self.charges_ids if line.charge.charge_type == 'add')
        charges_amount_minus = sum(round_curr(line.amount) for line in self.charges_ids if line.charge.charge_type == 'minus')
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        for line in self.sudo().move_id.line_ids:
            print ("line===============================",line,self.sudo().move_id.line_ids)
            if line.account_id.internal_type in ('receivable', 'payable'):
                residual_company_signed += line.amount_residual + add_tax_amount + charges_amount_add - charges_amount_minus
                if line.currency_id == self.currency_id:
                    residual_1 += line.amount_residual_currency if line.currency_id else line.amount_residual
                    print ("iffffffffffffff",residual)
                    residual = residual_1 + add_tax_amount + charges_amount_add - charges_amount_minus
                    print ("ifffffffff after==============",residual)
                else:
                    from_currency = (line.currency_id and line.currency_id.with_context(date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
                    print ("check residue else=========================",residual,line.amount_residual)
                    amount = line.amount_residual + add_tax_amount + charges_amount_add - charges_amount_minus
                    print ("amount else======================",amount)
                    residual += from_currency.compute(amount, self.currency_id)
                    print ('elseeeeeeeeeee',residual)
        print ("_compute_residual===============================",residual,residual_company_signed)
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
        self.residual = abs(residual)
        print ("result====================================",self.residual,self.residual_signed,self.residual_company_signed)
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.reconciled = True
        else:
            self.reconciled = False
        print ("final==========================",self.residual)
    
    sale_order_id = fields.Many2one('sale.order', compute='get_sale_order_id', store=True, string='Sale Order')
    invoice_terms_conditions = fields.One2many('invoice.terms', 'invoice_id')
    cmp_street = fields.Char(string='street')
    cmp_street2 = fields.Char(string="street2")
    cmp_zip = fields.Char(string='zip')
    cmp_city = fields.Char(string='city')
    cmp_state_id = fields.Many2one('res.country.state',string="state")
    cmp_country_id = fields.Many2one('res.country',string="Country")
    charges_ids = fields.One2many('invoice.charges', 'invoice_id')
    dispatch_medium_id = fields.Many2one('dispatch.medium',string="Dispatch Through")
    lr_rr_no = fields.Char('LR-RR-NO')
    vehical_no = fields.Char('Motor Vehicle No')
    delivery_term_ids = fields.One2many('delivery.terms', 'invoice_id')
    invoice_print_type = fields.Many2many('invoice.print.type','invoice_type_rel','invoice_id','type',string='Print Type',required=True)
    
    @api.depends('origin')
    def get_sale_order_id(self):
        for i in self:
            if i.origin:
                srch_so = self.env['sale.order'].search([('name','=',i.origin)])
                i.sale_order_id = srch_so.id
                
    @api.multi
    def get_dispatch_doc(self):
        for i in self:
            if i.origin:
                srch_sp = self.env['stock.picking'].search([('origin','=',i.origin)])[0]
                if srch_sp:
                    return srch_sp.name
                
    @api.multi    
    def amount_to_text(self, amount, currency):
        convert_amount_in_words = amount_to_text_en.amount_to_text(amount, lang='en', currency='')        
        convert_amount_in_words = convert_amount_in_words.replace(' and Zero Cent', ' Only ')         
        return convert_amount_in_words
        
    @api.multi
    def print_pi_tax_invoice(self):
        print ("wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww",self,self.state)
        if self.state in ('proforma','proforma2'):
            print ("11111111111111111111111111111111111")
            return self.env['report'].get_action(self, 'screen_art.report_proforma_invoice_1')
        elif self.state == 'open':
            print ("222222222222222222222222222222222222")
            return self.env['report'].get_action(self, 'screen_art.report_tax_invoice_1')
    
    @api.multi
    def action_invoice_proforma2(self):
        if self.filtered(lambda inv: inv.state != 'draft'):
            raise UserError(_("Invoice must be a draft in order to set it to Pro-forma."))
        return self.write({'state': 'proforma2','number': self.env['ir.sequence'].next_by_code('sequence_pi')})
    
class InvoiceCharges(models.Model):
    _name='invoice.charges'
    
    @api.one
    @api.depends('amount', 'tax_ids')
    def compute_totol_amount(self):
        tax_amt = 0.0
        for line in self:
            print ("compute_totol_amount==========================",line,self)
            if line.tax_ids:
                tax_amt = (self.amount * self.tax_ids[0].amount/100)
            line.total_amount = self.amount + tax_amt
    
    @api.depends('amount', 'total_amount')
    def compute_tax_amount(self):
        for line in self:
            print ("compute_tax_amount==========================",line,self)
            line.tax_amount = line.total_amount - line.amount
    
    charge = fields.Many2one('charges',string="Charge")
    amount = fields.Float('Amount')
    tax_ids = fields.Many2many('account.tax','account_tax_charges_rel','tax_id','charge_id',string="Taxes")
    total_amount = fields.Float(compute='compute_totol_amount',string='Total Amount')
    tax_amount = fields.Float(compute='compute_tax_amount',string='Tax Amount')
    invoice_id = fields.Many2one('account.invoice')
                       
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    sale_order_id = fields.Many2one('sale.order', compute='get_sale_order_id', store=True, string='Sale Order')
    
    @api.depends('origin')
    def get_sale_order_id(self):
        for i in self:
            if i.origin:
                srch_so = self.env['sale.order'].search([('name','=',i.origin)])
                if srch_so:
                    i.sale_order_id = srch_so.id

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    
    branch = fields.Char('Branch')
    ifs_code = fields.Char('IFS Code')
    