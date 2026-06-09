from odoo import models, fields, api
from datetime import datetime


class DentalStaff(models.Model):
    _name = 'dental.staff'
    _description = 'Dental Clinic Staff'
    _inherits = {'hr.employee': 'employee_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='cascade',
        string='HR Employee', auto_join=True
    )
    role = fields.Selection([
        ('receptionist',    'Receptionist'),
        ('dental_assistant','Dental Assistant'),
        ('hygienist',       'Dental Hygienist'),
        ('nurse',           'Nurse'),
        ('lab_technician',  'Lab Technician'),
        ('admin',           'Admin / Manager'),
        ('other',           'Other'),
    ], string='Role', required=True, default='receptionist', tracking=True)
    staff_ref = fields.Char(
        string='Staff ID', readonly=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('dental.staff') or 'New'
    )
    attendance_ids = fields.One2many('dental.attendance', 'staff_id', string='Attendance')
    attendance_count = fields.Integer(compute='_compute_attendance_count', store=True)

    @api.depends('attendance_ids')
    def _compute_attendance_count(self):
        for rec in self:
            rec.attendance_count = len(rec.attendance_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'department_id' not in vals:
                dept = self.env['hr.department'].search([('name', '=', 'Dental Clinic')], limit=1)
                if not dept:
                    dept = self.env['hr.department'].create({'name': 'Dental Clinic'})
                vals['department_id'] = dept.id
            role = vals.get('role', '')
            role_labels = dict(self._fields['role'].selection) if hasattr(self._fields.get('role', None), 'selection') else {}
            if 'job_title' not in vals and role:
                roles = {
                    'receptionist': 'Receptionist',
                    'dental_assistant': 'Dental Assistant',
                    'hygienist': 'Dental Hygienist',
                    'nurse': 'Nurse',
                    'lab_technician': 'Lab Technician',
                    'admin': 'Admin / Manager',
                    'other': 'Staff',
                }
                vals['job_title'] = roles.get(role, 'Staff')
        return super().create(vals_list)

    def action_check_in(self):
        self.ensure_one()
        existing = self.env['dental.attendance'].search([
            ('staff_id', '=', self.id),
            ('check_out', '=', False),
        ], limit=1)
        if existing:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'message': 'Already checked in!', 'type': 'warning'}}
        self.env['dental.attendance'].create({
            'staff_id': self.id,
            'check_in': datetime.now(),
        })
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'message': f'{self.name} checked in.', 'type': 'success'}}

    def action_check_out(self):
        self.ensure_one()
        attendance = self.env['dental.attendance'].search([
            ('staff_id', '=', self.id),
            ('check_out', '=', False),
        ], limit=1)
        if not attendance:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'message': 'No active check-in found.', 'type': 'warning'}}
        attendance.check_out = datetime.now()
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'message': f'{self.name} checked out.', 'type': 'success'}}

    def action_view_attendance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attendance',
            'res_model': 'dental.attendance',
            'view_mode': 'list,form',
            'domain': [('staff_id', '=', self.id)],
            'context': {'default_staff_id': self.id},
        }

    def action_view_employee(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'view_mode': 'form',
        }
