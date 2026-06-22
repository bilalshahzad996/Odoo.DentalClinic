from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta


class DentalAppointment(models.Model):
    _name = 'dental.appointment'
    _description = 'Dental Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='Appointment Ref', readonly=True, copy=False, tracking=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('dental.appointment') or 'New'
    )
    patient_id = fields.Many2one('dental.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('dental.doctor', string='Doctor', required=True, tracking=True)
    appointment_date = fields.Datetime(string='Date & Time', required=True, tracking=True)
    duration = fields.Float(string='Duration (hrs)', default=0.5)
    chief_complaint = fields.Text(string='Chief Complaint')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('scheduled',   'Scheduled'),
        ('confirmed',   'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done',        'Done'),
        ('cancelled',   'Cancelled'),
        ('no_show',     'No Show'),
    ], string='Status', default='scheduled', tracking=True)
    treatment_id = fields.Many2one('dental.treatment', string='Treatment', copy=False)
    calendar_event_id = fields.Many2one('calendar.event', string='Calendar Event', copy=False, ondelete='set null')

    _STATUS_MAP = {
        'scheduled':   'request',
        'confirmed':   'booked',
        'in_progress': 'booked',
        'done':        'attended',
        'cancelled':   'cancelled',
        'no_show':     'no_show',
    }

    @api.constrains('appointment_date', 'doctor_id')
    def _check_double_booking(self):
        for rec in self:
            if not rec.appointment_date or not rec.doctor_id:
                continue
            stop = rec.appointment_date + timedelta(hours=rec.duration or 0.5)
            conflict = self.search([
                ('id', '!=', rec.id),
                ('doctor_id', '=', rec.doctor_id.id),
                ('state', 'not in', ['cancelled', 'no_show']),
                ('appointment_date', '<', stop),
                ('appointment_date', '>=', rec.appointment_date),
            ])
            if conflict:
                raise ValidationError(
                    f'Doctor {rec.doctor_id.name} already has an appointment at this time: {conflict[0].name}'
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._sync_calendar_event()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('no_dental_sync') and set(vals) & {'appointment_date', 'duration', 'patient_id', 'doctor_id', 'state'}:
            for rec in self:
                rec._sync_calendar_event()
        return res

    def unlink(self):
        events = self.mapped('calendar_event_id')
        res = super().unlink()
        events.sudo().unlink()
        return res

    def _sync_calendar_event(self):
        self.ensure_one()
        apt_type = self.env.ref('dental_clinic.dental_appointment_type', raise_if_not_found=False)
        if not apt_type or not self.appointment_date:
            return
        patient = self.patient_id
        partner = patient.partner_id
        stop = self.appointment_date + timedelta(hours=self.duration or 0.5)
        vals = {
            'appointment_type_id': apt_type.id,
            'appointment_booker_id': partner.id,
            'appointment_status': self._STATUS_MAP.get(self.state, 'request'),
            'name': f'{patient.name} - Dental Appointment',
            'start': self.appointment_date,
            'stop': stop,
            'partner_ids': [(4, partner.id)],
        }
        if self.doctor_id.user_id:
            vals['user_id'] = self.doctor_id.user_id.id
        if self.calendar_event_id:
            self.calendar_event_id.with_context(no_mail_to_attendees=True).sudo().write(vals)
        else:
            event = self.env['calendar.event'].with_context(no_mail_to_attendees=True).create(vals)
            self.with_context(no_dental_sync=True).sudo().write({'calendar_event_id': event.id})

    def action_confirm(self):
        self.state = 'confirmed'

    def action_in_progress(self):
        self.state = 'in_progress'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_no_show(self):
        self.state = 'no_show'

    def action_create_treatment(self):
        self.ensure_one()
        treatment = self.env['dental.treatment'].create({
            'patient_id': self.patient_id.id,
            'doctor_id': self.doctor_id.id,
            'appointment_id': self.id,
            'chief_complaint': self.chief_complaint or '',
        })
        self.treatment_id = treatment
        self.state = 'done'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dental.treatment',
            'res_id': treatment.id,
            'view_mode': 'form',
        }

    def action_view_calendar_event(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'res_id': self.calendar_event_id.id,
            'view_mode': 'form',
        }
