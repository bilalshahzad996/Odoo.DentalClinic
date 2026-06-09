from odoo import models, fields, api


class DentalTreatment(models.Model):
    _name = 'dental.treatment'
    _description = 'Dental Treatment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='Treatment Ref', readonly=True, copy=False, tracking=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('dental.treatment') or 'New'
    )
    patient_id = fields.Many2one('dental.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('dental.doctor', string='Doctor', required=True, tracking=True)
    appointment_id = fields.Many2one('dental.appointment', string='Appointment')
    date = fields.Date(string='Treatment Date', default=fields.Date.today, tracking=True)
    chief_complaint = fields.Text(string='Chief Complaint')
    diagnosis = fields.Text(string='Diagnosis')
    treatment_notes = fields.Text(string='Treatment Notes')
    next_visit_notes = fields.Text(string='Next Visit Instructions')
    state = fields.Selection([
        ('draft',       'Draft'),
        ('in_progress', 'In Progress'),
        ('completed',   'Completed'),
        ('invoiced',    'Invoiced'),
    ], string='Status', default='draft', tracking=True)
    line_ids = fields.One2many('dental.treatment.line', 'treatment_id', string='Procedures')
    invoice_id = fields.Many2one('account.move', string='Invoice', copy=False)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total', store=True)

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))

    def action_in_progress(self):
        self.state = 'in_progress'

    def action_complete(self):
        self.state = 'completed'

    def action_create_invoice(self):
        self.ensure_one()
        partner = self.patient_id.partner_id
        invoice_lines = []
        for line in self.line_ids:
            product = line.service_id.product_id
            if not product:
                continue
            invoice_lines.append((0, 0, {
                'product_id': product.product_variant_id.id,
                'name': line.service_id.name + (' - Tooth ' + line.tooth_numbers if line.tooth_numbers else ''),
                'quantity': line.quantity,
                'price_unit': line.unit_price,
                'discount': line.discount,
            }))
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_line_ids': invoice_lines,
            'invoice_origin': self.name,
        })
        self.invoice_id = invoice
        self.state = 'invoiced'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }


class DentalTreatmentLine(models.Model):
    _name = 'dental.treatment.line'
    _description = 'Dental Treatment Procedure'

    treatment_id = fields.Many2one('dental.treatment', string='Treatment', ondelete='cascade')
    service_id = fields.Many2one('dental.service', string='Service / Procedure', required=True)
    tooth_ids = fields.Many2many('dental.tooth', string='Teeth')
    tooth_numbers = fields.Char(string='Tooth Numbers', compute='_compute_tooth_numbers', store=True)
    quantity = fields.Float(string='Qty', default=1.0)
    unit_price = fields.Float(string='Unit Price')
    discount = fields.Float(string='Discount (%)')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    notes = fields.Char(string='Notes')

    @api.depends('tooth_ids')
    def _compute_tooth_numbers(self):
        for rec in self:
            rec.tooth_numbers = ', '.join(rec.tooth_ids.mapped('tooth_number')) if rec.tooth_ids else ''

    @api.depends('quantity', 'unit_price', 'discount')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.unit_price * (1 - rec.discount / 100)

    @api.onchange('service_id')
    def _onchange_service(self):
        if self.service_id:
            self.unit_price = self.service_id.price
