from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DentalAttendance(models.Model):
    _name = 'dental.attendance'
    _description = 'Dental Staff Attendance'
    _rec_name = 'staff_id'
    _order = 'check_in desc'

    staff_id = fields.Many2one('dental.staff', string='Staff', required=True, ondelete='cascade')
    check_in = fields.Datetime(string='Check In', required=True, default=fields.Datetime.now)
    check_out = fields.Datetime(string='Check Out')
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True)
    notes = fields.Char(string='Notes')
    hr_attendance_id = fields.Many2one('hr.attendance', string='HR Attendance', copy=False, ondelete='set null')

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.worked_hours = delta.total_seconds() / 3600.0
            else:
                rec.worked_hours = 0.0

    @api.constrains('check_in', 'check_out')
    def _check_times(self):
        for rec in self:
            if rec.check_out and rec.check_in and rec.check_out < rec.check_in:
                raise ValidationError('Check Out cannot be before Check In.')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._sync_hr_attendance()
        return records

    def write(self, vals):
        res = super().write(vals)
        if set(vals) & {'check_in', 'check_out'}:
            for rec in self:
                rec._sync_hr_attendance()
        return res

    def _sync_hr_attendance(self):
        self.ensure_one()
        employee = self.staff_id.employee_id
        if not employee:
            return
        hr_vals = {
            'employee_id': employee.id,
            'check_in': self.check_in,
            'check_out': self.check_out or False,
        }
        if self.hr_attendance_id:
            self.hr_attendance_id.write(hr_vals)
        else:
            hr_att = self.env['hr.attendance'].create(hr_vals)
            self.with_context(no_att_sync=True).hr_attendance_id = hr_att
