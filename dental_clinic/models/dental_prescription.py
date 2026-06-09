from odoo import models, fields


class DentalPrescription(models.Model):
    _name = 'dental.prescription'
    _description = 'Dental Prescription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='Prescription Ref', readonly=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('dental.prescription') or 'New'
    )
    patient_id = fields.Many2one('dental.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('dental.doctor', string='Doctor', required=True, tracking=True)
    treatment_id = fields.Many2one('dental.treatment', string='Treatment')
    date = fields.Date(string='Date', default=fields.Date.today)
    notes = fields.Text(string='General Notes')
    state = fields.Selection([
        ('draft',   'Draft'),
        ('active',  'Active'),
        ('expired', 'Expired'),
    ], default='draft', tracking=True)
    line_ids = fields.One2many('dental.prescription.line', 'prescription_id', string='Medicines')

    def action_activate(self):
        self.state = 'active'

    def action_expire(self):
        self.state = 'expired'


class DentalPrescriptionLine(models.Model):
    _name = 'dental.prescription.line'
    _description = 'Prescription Line'

    prescription_id = fields.Many2one('dental.prescription', ondelete='cascade')
    medicine_name = fields.Char(string='Medicine', required=True)
    dosage = fields.Char(string='Dosage', placeholder='e.g. 500mg')
    frequency = fields.Char(string='Frequency', placeholder='e.g. 3 times a day')
    duration = fields.Char(string='Duration', placeholder='e.g. 5 days')
    instructions = fields.Text(string='Special Instructions')
