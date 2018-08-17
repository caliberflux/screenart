from odoo import api, fields, models, tools, SUPERUSER_ID,_
from datetime import datetime
import time
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class ProductStockUpdate(models.TransientModel):
    _name= "product.stock.update"
    
    design_id = fields.Many2one('product.product',"Design")
    size = fields.Char("Size")
    stock_update_lines=fields.One2many('product.stock.update.lines', 'product_stock_update_id','Stock Update')
    sale_order_id = fields.Many2one('sale.order')
    factory_member = fields.Char('Factory Member')
    date = fields.Date('Date',default=fields.Date.context_today)
    
    def stock_calculate(self):
        print ("stock_calculate========================",self)
        list1=[]
        total_extra_qty = 0
        for rec in self.stock_update_lines:
            print ("rec===========================================",rec)
            print ("extra=========================================",rec.extra_qty)
            if rec.stock_qty:
                self.env['product.stock.management'].create({
                    'design_id' : self.design_id.id,
                    'design_size' : self.size,
                    'date' : self.date,
                    'sale_order_id' : self.sale_order_id.id,
                    'factory_member' : self.factory_member,
                    'combo_name' : rec.combo_name,
                    'combo_size' : rec.size,
                    'stock_qty' : rec.stock_qty,
                    'defected_qty' : rec.defected_qty,
                    'done_qty' : rec.done_qty,
                    'entry_type' : 'real_stock',
                })
            
            if rec.extra_qty:
                self.env['product.stock.management'].create({
                    'design_id' : self.design_id.id,
                    'design_size' : self.size,
                    'date' : self.date,
                    'sale_order_id' : self.sale_order_id.id,
                    'factory_member' : self.factory_member,
                    'combo_name' : rec.combo_name,
                    'combo_size' : rec.size,
                    'done_qty' : rec.extra_qty * (-1),
                    'entry_type' : 'adjust_stock',
                })
                
                list_val={
                    'combo_name':rec.combo_name,
                    'combo_size': rec.size,
                    'stock_qty': rec.extra_qty,
                    }
                print "list_val===================",list_val
                list1.append((0,0,list_val))
            
            total_extra_qty +=  rec.extra_qty
        
        print ("total exta qty=======================",total_extra_qty)  
        self.env['stock.quant'].create({
            'product_id': self.design_id.id,
            'in_date': self.date,
            'qty' : total_extra_qty,
            'location_id' : 15,
            'stock_quant_combo_ids' : list1,
        })

class ProductStockUpdatelines(models.TransientModel):
    _name= "product.stock.update.lines"
    
    combo_name = fields.Char("Combo Name")
    size = fields.Char("Size")
    order_qty = fields.Integer("Order Qty")
    print_qty = fields.Integer("Print Qty")
    stock_qty = fields.Integer("Stock Qty")
    defected_qty = fields.Integer("Defected Qty")
    done_qty = fields.Integer(compute='compute_done_qty', string='Stock Done')
    extra_qty = fields.Integer(compute='get_extra_stock',string="Extra Qty")
    current_stock_qty = fields.Integer(compute='get_current_stock', string='Stock Available')
    product_stock_update_id = fields.Many2one('product.stock.update')
    
    @api.multi
    @api.depends('stock_qty','defected_qty')
    def compute_done_qty(self):
        for rec in self:
            rec.done_qty = rec.stock_qty - rec.defected_qty
            
    @api.multi
    @api.depends('done_qty')
    def get_current_stock(self):
        print ("get_current_stock===================================",self)
        for rec in self:
            self._cr.execute("select sum(done_qty) from product_stock_management where design_id = %s and combo_name = %s and combo_size = %s \
                             and sale_order_id = %s",(rec.product_stock_update_id.design_id.id,rec.combo_name,rec.size,rec.product_stock_update_id.sale_order_id.id))
            done_qty = self._cr.fetchall()
            print ("done==============qty==================",done_qty)
            if done_qty[0][0]:
                rec.current_stock_qty = done_qty[0][0] + rec.done_qty
            else:
                rec.current_stock_qty = rec.done_qty
    
    @api.multi
    @api.depends('current_stock_qty','print_qty')
    def get_extra_stock(self):
        for rec in self:
            extra_qty = rec.current_stock_qty - rec.print_qty
            if extra_qty > 0:
                rec.extra_qty = extra_qty
                
class ProductStockManagement(models.Model):
    _name= "product.stock.management"
    
    design_id = fields.Many2one('product.product',"Design")
    design_size = fields.Char("Design Size")
    date = fields.Date('Date')
    sale_order_id = fields.Many2one('sale.order')
    factory_member = fields.Char('Factory Member')
    combo_name = fields.Char("Combo Name")
    combo_size = fields.Char("Size")
    stock_qty = fields.Integer("Stock Qty")
    defected_qty = fields.Integer("Defected Qty")
    done_qty = fields.Integer(string='Stock Done')
    entry_type = fields.Selection([('real_stock', 'Real Qty'),('adjust_stock','Adj Stock Qty ')], string='Entry Type')

class StockQuant(models.Model):
    _inherit= "stock.quant"
    
    stock_quant_combo_ids = fields.One2many('stock.quant.combo','stock_quant_id')

class StockQuantCombo(models.Model):
    _name= "stock.quant.combo"
    
    combo_name = fields.Char("Combo Name")
    combo_size = fields.Char("Size")
    stock_qty = fields.Integer("Qty")
    stock_quant_id = fields.Many2one('stock.quant')

class ProductStockDetailsMoveLines(models.Model):
    _name = "product.stock.details.move.lines"
    
    combo_name = fields.Char("Combo Name")
    size = fields.Char("Size")
    qty = fields.Integer("Qty")
    move_line_id = fields.Many2one('stock.move')
    
class StockMove(models.Model):
    _inherit = 'stock.move'
    
    product_stock_details_move_ids = fields.One2many('product.stock.details.move.lines','move_line_id')
    
    @api.multi
    def save(self):
        return True
    
    def split_stock_qty(self):
        print "split_stock_qty===================================="
        context = dict(self.env.context or {})
        
        if self.product_stock_details_move_ids:
            print "iffffffffffffffffffffff1111111"
            return {
            'name': _('Stock Details'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.move',
            'view_id': self.env.ref('screen_art.wizard_stock_move_sart').id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'target': 'new',
            'context': context,
            }
        
        else:
            print "elseeeeeeeeeeeeeeeeeeeeeeeeeee1111111",self.picking_id,self.picking_id.sale_order_id
            for rec in self.picking_id.sale_order_id.order_line:
                if self.product_id != rec.product_id:
                    continue
                
                combo_details = rec.product_stock_details_ids
                list1 = []
                for combo in combo_details:
                    val={
                        'combo_name':combo.combo_name,
                        'size': combo.size,
                        'qty': combo.order_qty
                        }
                    print "val===================",val
                    list1.append((0,0,val))
                print "list=======",list1
            self.product_stock_details_move_ids = list1
                   
            return {
                'name': _('Stock Details'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.move',
                'view_id': self.env.ref('screen_art.wizard_stock_move_sart').id,
                'type': 'ir.actions.act_window',
                'res_id': self.id,
                'target': 'new',
                'context': context,
            }
    
    @api.multi
    def action_done(self):
        print "action_done==========================override===============================",self
        """ Process completely the moves given and if all moves are done, it will finish the picking. """
        self.filtered(lambda move: move.state == 'draft').action_confirm()

        Uom = self.env['product.uom']
        Quant = self.env['stock.quant']

        pickings = self.env['stock.picking']
        procurements = self.env['procurement.order']
        operations = self.env['stock.pack.operation']

        remaining_move_qty = {}

        for move in self:
            if move.picking_id:
                pickings |= move.picking_id
            remaining_move_qty[move.id] = move.product_qty
            for link in move.linked_move_operation_ids:
                operations |= link.operation_id
                pickings |= link.operation_id.picking_id

        # Sort operations according to entire packages first, then package + lot, package only, lot only
        operations = operations.sorted(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))

        for operation in operations:
            print "========operation===========================",operation
            # product given: result put immediately in the result package (if False: without package)
            # but if pack moved entirely, quants should not be written anything for the destination package
            quant_dest_package_id = operation.product_id and operation.result_package_id.id or False
            entire_pack = not operation.product_id and True or False

            # compute quantities for each lot + check quantities match
            lot_quantities = dict((pack_lot.lot_id.id, operation.product_uom_id._compute_quantity(pack_lot.qty, operation.product_id.uom_id)
            ) for pack_lot in operation.pack_lot_ids)

            qty = operation.product_qty
            if operation.product_uom_id and operation.product_uom_id != operation.product_id.uom_id:
                qty = operation.product_uom_id._compute_quantity(qty, operation.product_id.uom_id)
            if operation.pack_lot_ids and float_compare(sum(lot_quantities.values()), qty, precision_rounding=operation.product_id.uom_id.rounding) != 0.0:
                raise UserError(_('You have a difference between the quantity on the operation and the quantities specified for the lots. '))

            quants_taken = []
            false_quants = []
            lot_move_qty = {}

            prout_move_qty = {}
            for link in operation.linked_move_operation_ids:
                prout_move_qty[link.move_id] = prout_move_qty.get(link.move_id, 0.0) + link.qty

            # Process every move only once for every pack operation
            for move in prout_move_qty.keys():
                # TDE FIXME: do in batch ?
                move.check_tracking(operation)

                # TDE FIXME: I bet the message error is wrong
                if not remaining_move_qty.get(move.id):
                    raise UserError(_("The roundings of your unit of measure %s on the move vs. %s on the product don't allow to do these operations or you are not transferring the picking at once. ") % (move.product_uom.name, move.product_id.uom_id.name))
                
                print "pack_lot_ids========================",operation.pack_lot_ids,move
                if not operation.pack_lot_ids:
                    print "ifffffffffffffffffffffffffffffffffffffffff"
                    if move.picking_id.sale_order_id.job_order_type != 'original':
                        print "ifiiiiifffffffffffffffffffffffffffff==== original========================="
                        preferred_domain_list = [[('reservation_id', '=', move.id)], [('reservation_id', '=', False)], ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]]
                        quants = Quant.quants_get_preferred_domain(
                            prout_move_qty[move], move, ops=operation, domain=[('qty', '>', 0)],
                            preferred_domain_list=preferred_domain_list)
                        Quant.quants_move(quants, move, operation.location_dest_id, location_from=operation.location_id,
                                          lot_id=False, owner_id=operation.owner_id.id, src_package_id=operation.package_id.id,
                                          dest_package_id=quant_dest_package_id, entire_pack=entire_pack)
                else:
                    print "elseeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
                    # Check what you can do with reserved quants already
                    qty_on_link = prout_move_qty[move]
                    rounding = operation.product_id.uom_id.rounding
                    for reserved_quant in move.reserved_quant_ids:
                        if (reserved_quant.owner_id.id != operation.owner_id.id) or (reserved_quant.location_id.id != operation.location_id.id) or \
                                (reserved_quant.package_id.id != operation.package_id.id):
                            continue
                        if not reserved_quant.lot_id:
                            false_quants += [reserved_quant]
                        elif float_compare(lot_quantities.get(reserved_quant.lot_id.id, 0), 0, precision_rounding=rounding) > 0:
                            if float_compare(lot_quantities[reserved_quant.lot_id.id], reserved_quant.qty, precision_rounding=rounding) >= 0:
                                lot_quantities[reserved_quant.lot_id.id] -= reserved_quant.qty
                                quants_taken += [(reserved_quant, reserved_quant.qty)]
                                qty_on_link -= reserved_quant.qty
                            else:
                                quants_taken += [(reserved_quant, lot_quantities[reserved_quant.lot_id.id])]
                                lot_quantities[reserved_quant.lot_id.id] = 0
                                qty_on_link -= lot_quantities[reserved_quant.lot_id.id]
                    lot_move_qty[move.id] = qty_on_link

                remaining_move_qty[move.id] -= prout_move_qty[move]
            
            # Handle lots separately
            if operation.pack_lot_ids:
                # TDE FIXME: fix call to move_quants_by_lot to ease understanding
                self._move_quants_by_lot(operation, lot_quantities, quants_taken, false_quants, lot_move_qty, quant_dest_package_id)

            # Handle pack in pack
            if not operation.product_id and operation.package_id and operation.result_package_id.id != operation.package_id.parent_id.id:
                operation.package_id.sudo().write({'parent_id': operation.result_package_id.id})

        # Check for remaining qtys and unreserve/check move_dest_id in
        move_dest_ids = set()
        for move in self:
            if float_compare(remaining_move_qty[move.id], 0, precision_rounding=move.product_id.uom_id.rounding) > 0:  # In case no pack operations in picking
                move.check_tracking(False)  # TDE: do in batch ? redone ? check this

                preferred_domain_list = [[('reservation_id', '=', move.id)], [('reservation_id', '=', False)], ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]]
                quants = Quant.quants_get_preferred_domain(
                    remaining_move_qty[move.id], move, domain=[('qty', '>', 0)],
                    preferred_domain_list=preferred_domain_list)
                Quant.quants_move(
                    quants, move, move.location_dest_id,
                    lot_id=move.restrict_lot_id.id, owner_id=move.restrict_partner_id.id)

            # If the move has a destination, add it to the list to reserve
            if move.move_dest_id and move.move_dest_id.state in ('waiting', 'confirmed'):
                move_dest_ids.add(move.move_dest_id.id)

            if move.procurement_id:
                procurements |= move.procurement_id

            # unreserve the quants and make them available for other operations/moves
            move.quants_unreserve()

        # Check the packages have been placed in the correct locations
        self.mapped('quant_ids').filtered(lambda quant: quant.package_id and quant.qty > 0).mapped('package_id')._check_location_constraint()

        # set the move as done
        self.write({'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        procurements.check()
        # assign destination moves
        if move_dest_ids:
            # TDE FIXME: record setise me
            self.browse(list(move_dest_ids)).action_assign()

        pickings.filtered(lambda picking: picking.state == 'done' and not picking.date_done).write({'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

        return True
    
class Picking(models.Model):
    _inherit = "stock.picking"
    
    @api.multi
    def do_new_transfer(self):
        print "do_new_transfer====================================",self
        for rec in self.pack_operation_product_ids:
            for i in self.move_lines:
                if rec.product_id != i.product_id :
                    continue
                
                self._cr.execute("select sum(qty) from product_stock_details_move_lines where move_line_id = %s",(i.id,))
                move_qty = self._cr.fetchall()[0][0]
                print "move_qty===============================",move_qty
                print "done_qty===============================",rec.qty_done,move_qty
                
                if rec.qty_done != move_qty:
                    print "qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"
                    raise ValidationError(_('combo quantities are not equal to done quantities for product %s') %rec.product_id.name)
                    # raise UserError(_('combo quantities are not equal to done quantities for product %s',(rec.product_id.name,)))
                
        for pick in self:
            if pick.state == 'done':
                raise UserError(_('The pick is already validated'))
            pack_operations_delete = self.env['stock.pack.operation']
            if not pick.move_lines and not pick.pack_operation_ids:
                raise UserError(_('Please create some Initial Demand or Mark as Todo and create some Operations. '))
            # In draft or with no pack operations edited yet, ask if we can just do everything
            if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
                # If no lots when needed, raise error
                picking_type = pick.picking_type_id
                if (picking_type.use_create_lots or picking_type.use_existing_lots):
                    for pack in pick.pack_operation_ids:
                        if pack.product_id and pack.product_id.tracking != 'none':
                            raise UserError(_('Some products require lots/serial numbers, so you need to specify those first!'))
                view = self.env.ref('stock.view_immediate_transfer')
                wiz = self.env['stock.immediate.transfer'].create({'pick_id': pick.id})
                # TDE FIXME: a return in a loop, what a good idea. Really.
                return {
                    'name': _('Immediate Transfer?'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.immediate.transfer',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz.id,
                    'context': self.env.context,
                }

            # Check backorder should check for other barcodes
            if pick.check_backorder():
                view = self.env.ref('stock.view_backorder_confirmation')
                wiz = self.env['stock.backorder.confirmation'].create({'pick_id': pick.id})
                # TDE FIXME: same reamrk as above actually
                return {
                    'name': _('Create Backorder?'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.backorder.confirmation',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': wiz.id,
                    'context': self.env.context,
                }
            for operation in pick.pack_operation_ids:
                if operation.qty_done < 0:
                    raise UserError(_('No negative quantities allowed'))
                if operation.qty_done > 0:
                    operation.write({'product_qty': operation.qty_done})
                else:
                    pack_operations_delete |= operation
            if pack_operations_delete:
                pack_operations_delete.unlink()
        self.do_transfer()
        return
    
    
class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'
    
    @api.multi
    def process(self):
        self._process()
        for i in self.pick_id.sale_order_id.picking_ids:
            if i.sale_order_id:
                continue
            i.sale_order_id = self.pick_id.sale_order_id

                
    
    

    
    
    
            