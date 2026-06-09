from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DentalInventoryItem(models.Model):
    _name = 'dental.inventory.item'
    _description = 'Dental Clinic Inventory Item'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'product_id'
    _order = 'product_id'

    product_id = fields.Many2one(
        'product.product', string='Product', required=True, ondelete='restrict',
        domain=[('type', 'in', ['consu', 'product'])],
        tracking=True
    )
    product_tmpl_id = fields.Many2one(
        'product.template', related='product_id.product_tmpl_id', store=True, readonly=True
    )
    category = fields.Selection([
        ('consumable',  'Consumable / Disposable'),
        ('instrument',  'Instrument / Tool'),
        ('material',    'Dental Material'),
        ('medication',  'Medication / Anaesthetic'),
        ('equipment',   'Equipment / Device'),
        ('ppe',         'PPE / Safety'),
        ('lab',         'Lab Supply'),
        ('other',       'Other'),
    ], string='Category', required=True, default='consumable', tracking=True)
    quantity_on_hand = fields.Float(
        string='Qty On Hand', compute='_compute_stock', store=False
    )
    quantity_available = fields.Float(
        string='Qty Available', compute='_compute_stock', store=False
    )
    min_quantity = fields.Float(string='Minimum Stock Level', default=5.0, tracking=True)
    uom_id = fields.Many2one(
        'uom.uom', related='product_id.uom_id', string='Unit', readonly=True
    )
    location_id = fields.Many2one(
        'stock.location', string='Storage Location',
        domain=[('usage', '=', 'internal')]
    )
    notes = fields.Text(string='Notes')
    is_low_stock = fields.Boolean(
        string='Low Stock', compute='_compute_low_stock', store=False
    )
    usage_ids = fields.One2many('dental.inventory.usage', 'item_id', string='Usage History')
    usage_count = fields.Integer(compute='_compute_usage_count', store=True)

    _sql_constraints = [
        ('product_unique', 'unique(product_id)', 'This product is already in the dental inventory.'),
    ]

    @api.depends('usage_ids')
    def _compute_usage_count(self):
        for rec in self:
            rec.usage_count = len(rec.usage_ids)

    def _compute_stock(self):
        for rec in self:
            if rec.product_id:
                rec.quantity_on_hand = rec.product_id.qty_available
                rec.quantity_available = rec.product_id.virtual_available
            else:
                rec.quantity_on_hand = 0.0
                rec.quantity_available = 0.0

    def _compute_low_stock(self):
        for rec in self:
            rec.is_low_stock = rec.quantity_on_hand < rec.min_quantity

    def action_view_stock_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Moves',
            'res_model': 'stock.move.line',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.product_id.id)],
        }

    def action_view_usage(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Usage History',
            'res_model': 'dental.inventory.usage',
            'view_mode': 'list,form',
            'domain': [('item_id', '=', self.id)],
            'context': {'default_item_id': self.id},
        }

    def action_open_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': self.product_tmpl_id.id,
            'view_mode': 'form',
        }


class DentalInventoryUsage(models.Model):
    _name = 'dental.inventory.usage'
    _description = 'Dental Inventory Usage Record'
    _rec_name = 'item_id'
    _order = 'date desc'

    item_id = fields.Many2one(
        'dental.inventory.item', string='Item', required=True, ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', related='item_id.product_id', store=True, readonly=True
    )
    date = fields.Datetime(string='Date Used', required=True, default=fields.Datetime.now)
    quantity = fields.Float(string='Quantity Used', required=True, default=1.0)
    uom_id = fields.Many2one('uom.uom', related='item_id.uom_id', readonly=True)
    used_by = fields.Many2one('res.users', string='Used By', default=lambda self: self.env.user)
    doctor_id = fields.Many2one('dental.doctor', string='Doctor')
    patient_id = fields.Many2one('dental.patient', string='Patient')
    treatment_id = fields.Many2one('dental.treatment', string='Treatment')
    purpose = fields.Char(string='Purpose / Procedure')
    stock_move_id = fields.Many2one(
        'stock.move', string='Stock Move', copy=False, ondelete='set null', readonly=True
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError('Quantity used must be greater than zero.')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._consume_stock()
        return records

    def _consume_stock(self):
        """Create a scrap order to consume the item from Odoo Inventory."""
        self.ensure_one()
        product = self.item_id.product_id
        if not product or product.type == 'service':
            return

        src_location = self.item_id.location_id
        if not src_location:
            src_location = self.env['stock.location'].search(
                [('usage', '=', 'internal'), ('company_id', '=', self.env.company.id)],
                limit=1
            )
        if not src_location:
            return

        scrap = self.env['stock.scrap'].create({
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'scrap_qty': self.quantity,
            'location_id': src_location.id,
            'origin': f'Dental Usage: {self.purpose or product.name}',
        })
        scrap.action_validate()
        if scrap.move_ids:
            self.stock_move_id = scrap.move_ids[0]
