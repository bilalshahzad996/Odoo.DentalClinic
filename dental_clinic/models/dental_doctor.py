from odoo import models, fields, api


class DentalDoctor(models.Model):
    _name = 'dental.doctor'
    _description = 'Dental Doctor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Doctor Name', required=True, tracking=True)
    specialization = fields.Selection([
        ('general',        'General Dentist'),
        ('orthodontics',   'Orthodontics'),
        ('endodontics',    'Endodontics (Root Canal)'),
        ('periodontics',   'Periodontics (Gum)'),
        ('pediatric',      'Pediatric Dentistry'),
        ('oral_surgery',   'Oral & Maxillofacial Surgery'),
        ('prosthodontics', 'Prosthodontics'),
        ('cosmetic',       'Cosmetic Dentistry'),
    ], string='Specialization', required=True, default='general', tracking=True)
    license_number = fields.Char(string='License Number')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    degree = fields.Char(string='Degree / Qualification')
    experience_years = fields.Integer(string='Years of Experience')
    user_id = fields.Many2one('res.users', string='Related User')
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one(
        'hr.employee', string='HR Employee', copy=False, ondelete='set null',
        help='Linked Odoo HR Employee record.'
    )
    appointment_ids = fields.One2many('dental.appointment', 'doctor_id', string='Appointments')
    appointment_count = fields.Integer(compute='_compute_appointment_count', store=True)

    @api.depends('appointment_ids')
    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = len(rec.appointment_ids)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.employee_id:
                rec._create_or_sync_employee()
        return records

    def write(self, vals):
        res = super().write(vals)
        if set(vals) & {'name', 'phone', 'email', 'specialization'}:
            for rec in self:
                if rec.employee_id:
                    rec._sync_employee(vals)
        return res

    def _get_dental_department(self):
        dept = self.env['hr.department'].search([('name', '=', 'Dental Clinic')], limit=1)
        if not dept:
            dept = self.env['hr.department'].create({'name': 'Dental Clinic'})
        return dept

    def _create_or_sync_employee(self):
        self.ensure_one()
        dept = self._get_dental_department()
        spec_label = dict(self._fields['specialization'].selection).get(self.specialization, 'Dentist')
        employee = self.env['hr.employee'].create({
            'name': self.name,
            'job_title': spec_label,
            'department_id': dept.id,
            'work_phone': self.phone or False,
            'work_email': self.email or False,
            'user_id': self.user_id.id if self.user_id else False,
        })
        self.with_context(no_hr_sync=True).employee_id = employee

    def _sync_employee(self, vals):
        self.ensure_one()
        sync = {}
        if 'name' in vals:
            sync['name'] = vals['name']
        if 'phone' in vals:
            sync['work_phone'] = vals['phone']
        if 'email' in vals:
            sync['work_email'] = vals['email']
        if 'specialization' in vals:
            spec_label = dict(self._fields['specialization'].selection).get(vals['specialization'], 'Dentist')
            sync['job_title'] = spec_label
        if sync:
            self.employee_id.write(sync)

    def action_view_appointments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'dental.appointment',
            'view_mode': 'list,form',
            'domain': [('doctor_id', '=', self.id)],
        }

    def action_view_employee(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'view_mode': 'form',
        }
