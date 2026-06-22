from odoo import models, fields


class DentalXray(models.Model):
    _name = 'dental.xray'
    _description = 'Dental X-Ray'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='X-Ray Ref', readonly=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('dental.xray') or 'New'
    )
    patient_id = fields.Many2one('dental.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('dental.doctor', string='Requested By', tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today)
    xray_type = fields.Selection([
        ('periapical',    'Periapical'),
        ('bitewing',      'Bitewing'),
        ('panoramic',     'Panoramic (OPG)'),
        ('cephalometric', 'Cephalometric'),
        ('cbct',          'CBCT (3D)'),
    ], string='Type', required=True, default='periapical')
    tooth_ids = fields.Many2many('dental.tooth', string='Related Teeth')
    image = fields.Binary(string='X-Ray Image', attachment=True)
    image_filename = fields.Char(string='Filename')
    findings = fields.Text(string='Radiographic Findings')
    notes = fields.Text(string='Notes')
