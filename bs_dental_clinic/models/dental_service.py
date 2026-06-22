from odoo import models, fields, api


class DentalService(models.Model):
    _name = 'dental.service'
    _description = 'Dental Service / Procedure'
    _rec_name = 'name'

    name = fields.Char(string='Service Name', required=True)
    category = fields.Selection([
        ('examination',   'Examination & Consultation'),
        ('xray',          'X-Ray / Imaging'),
        ('cleaning',      'Cleaning & Scaling'),
        ('filling',       'Filling / Restoration'),
        ('extraction',    'Extraction'),
        ('root_canal',    'Root Canal Treatment'),
        ('crown',         'Crown & Bridge'),
        ('implant',       'Dental Implant'),
        ('orthodontics',  'Orthodontics / Braces'),
        ('whitening',     'Teeth Whitening'),
        ('denture',       'Denture / Prosthetics'),
        ('pediatric',     'Pediatric Dentistry'),
        ('other',         'Other'),
    ], string='Category', required=True, default='examination')
    price = fields.Float(string='Default Price', required=True)
    duration_mins = fields.Integer(string='Duration (mins)', default=30)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    product_id = fields.Many2one(
        'product.template', string='Linked Product',
        domain=[('type', '=', 'service')],
        help='Used for invoicing. Leave empty to auto-create.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.product_id:
                product = self.env['product.template'].create({
                    'name': rec.name,
                    'type': 'service',
                    'list_price': rec.price,
                    'categ_id': self.env.ref('product.cat_expense', raise_if_not_found=False) and
                                self.env.ref('product.cat_expense').id or False,
                })
                rec.product_id = product
        return records