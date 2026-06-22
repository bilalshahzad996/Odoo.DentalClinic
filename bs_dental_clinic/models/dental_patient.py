from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class DentalPatient(models.Model):
    _name = 'dental.patient'
    _description = 'Dental Patient'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    partner_id = fields.Many2one(
        'res.partner', required=True, ondelete='cascade',
        auto_join=True, string='Related Contact'
    )
    patient_ref = fields.Char(
        string='Patient ID', readonly=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('dental.patient') or 'New'
    )
    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other')
    ], string='Gender', tracking=True)
    blood_group = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')
    ], string='Blood Group')
    allergies = fields.Text(string='Allergies / Medications')
    medical_history = fields.Text(string='Medical History')
    emergency_contact = fields.Char(string='Emergency Contact Name')
    emergency_phone = fields.Char(string='Emergency Contact Phone')

    appointment_ids = fields.One2many('dental.appointment', 'patient_id', string='Appointments')
    treatment_ids = fields.One2many('dental.treatment', 'patient_id', string='Treatments')
    tooth_ids = fields.One2many('dental.tooth', 'patient_id', string='Tooth Chart')
    prescription_ids = fields.One2many('dental.prescription', 'patient_id', string='Prescriptions')
    xray_ids = fields.One2many('dental.xray', 'patient_id', string='X-Rays')

    appointment_count = fields.Integer(string='Appointments', compute='_compute_counts', store=True)
    treatment_count = fields.Integer(string='Treatments', compute='_compute_counts', store=True)

    @api.depends('date_of_birth')
    def _compute_age(self):
        for rec in self:
            if rec.date_of_birth:
                today = date.today()
                rec.age = today.year - rec.date_of_birth.year - (
                    (today.month, today.day) < (rec.date_of_birth.month, rec.date_of_birth.day)
                )
            else:
                rec.age = 0

    @api.depends('appointment_ids', 'treatment_ids')
    def _compute_counts(self):
        for rec in self:
            rec.appointment_count = len(rec.appointment_ids)
            rec.treatment_count = len(rec.treatment_ids)

    @api.constrains('date_of_birth')
    def _check_dob(self):
        for rec in self:
            if rec.date_of_birth and rec.date_of_birth > date.today():
                raise ValidationError('Date of Birth cannot be a future date.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('customer_rank', 1)
            vals.setdefault('is_company', False)
        return super().create(vals_list)

    def action_view_appointments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'dental.appointment',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def action_view_treatments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Treatments',
            'res_model': 'dental.treatment',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }
