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
    patient_id  = fields.Many2one('dental.patient', string='Patient', required=True, tracking=True)
    doctor_id   = fields.Many2one('dental.doctor',  string='Doctor',  required=True, tracking=True)
    appointment_id = fields.Many2one('dental.appointment', string='Appointment')
    date = fields.Date(string='Treatment Date', default=fields.Date.today, tracking=True)
    chief_complaint  = fields.Text(string='Chief Complaint')
    diagnosis        = fields.Text(string='Diagnosis')
    treatment_notes  = fields.Text(string='Treatment Notes')
    next_visit_notes = fields.Text(string='Next Visit Instructions')

    # New flow: Draft → Sale Order → Invoiced → In Progress → Completed
    state = fields.Selection([
        ('draft',       'Draft'),
        ('sale_order',  'Sale Order'),
        ('invoiced',    'Invoiced'),
        ('in_progress', 'In Progress'),
        ('completed',   'Completed'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many('dental.treatment.line', 'treatment_id', string='Procedures')

    sale_order_id = fields.Many2one('sale.order',    string='Sale Order', copy=False, readonly=True)
    invoice_id    = fields.Many2one('account.move',  string='Invoice',    copy=False, readonly=True)

    sale_order_count = fields.Integer(compute='_compute_counts')
    invoice_count    = fields.Integer(compute='_compute_counts')

    amount_untaxed = fields.Float(string='Untaxed Amount', compute='_compute_totals', store=True)
    amount_tax     = fields.Float(string='Tax',            compute='_compute_totals', store=True)
    total_amount   = fields.Float(string='Total Amount',   compute='_compute_totals', store=True)

    @api.depends('line_ids.subtotal', 'line_ids.tax_amount')
    def _compute_totals(self):
        for rec in self:
            rec.amount_untaxed = sum(rec.line_ids.mapped('subtotal'))
            rec.amount_tax     = sum(rec.line_ids.mapped('tax_amount'))
            rec.total_amount   = rec.amount_untaxed + rec.amount_tax

    def _compute_counts(self):
        for rec in self:
            rec.sale_order_count = 1 if rec.sale_order_id else 0
            rec.invoice_count    = 1 if rec.invoice_id    else 0

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_create_sale_order(self):
        self.ensure_one()
        partner = self.patient_id.partner_id
        order_lines = []
        for line in self.line_ids:
            product = line.service_id.product_id
            if not product:
                continue
            order_lines.append((0, 0, {
                'product_id':      product.product_variant_id.id,
                'name':            line.service_id.name + (' - Tooth ' + line.tooth_numbers if line.tooth_numbers else ''),
                'product_uom_qty': line.quantity,
                'price_unit':      line.unit_price,
                'discount':        line.discount,
                'tax_ids':         [(6, 0, line.tax_ids.ids)],
            }))
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': order_lines,
            'origin':     self.name,
            'note':       self.treatment_notes or '',
        })
        self.sale_order_id = sale_order
        self.state = 'sale_order'
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id':    sale_order.id,
            'view_mode': 'form',
        }

    def action_create_invoice(self):
        self.ensure_one()
        # Preferred: create invoice from confirmed sale order
        if self.sale_order_id:
            so = self.sale_order_id
            if so.state == 'draft':
                so.action_confirm()
            so._create_invoices()
            invoices = so.invoice_ids
            if invoices:
                self.invoice_id = invoices[0]
                self.state = 'invoiced'
                return {
                    'type':      'ir.actions.act_window',
                    'res_model': 'account.move',
                    'res_id':    self.invoice_id.id,
                    'view_mode': 'form',
                }

        # Fallback: direct invoice without sale order
        partner = self.patient_id.partner_id
        invoice_lines = []
        for line in self.line_ids:
            product = line.service_id.product_id
            if not product:
                continue
            invoice_lines.append((0, 0, {
                'product_id': product.product_variant_id.id,
                'name':       line.service_id.name + (' - Tooth ' + line.tooth_numbers if line.tooth_numbers else ''),
                'quantity':   line.quantity,
                'price_unit': line.unit_price,
                'discount':   line.discount,
                'tax_ids':    [(6, 0, line.tax_ids.ids)],
            }))
        invoice = self.env['account.move'].create({
            'move_type':        'out_invoice',
            'partner_id':       partner.id,
            'invoice_line_ids': invoice_lines,
            'invoice_origin':   self.name,
        })
        self.invoice_id = invoice
        self.state = 'invoiced'
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id':    invoice.id,
            'view_mode': 'form',
        }

    def action_in_progress(self):
        self.state = 'in_progress'

    def action_complete(self):
        self.state = 'completed'

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id':    self.sale_order_id.id,
            'view_mode': 'form',
        }

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id':    self.invoice_id.id,
            'view_mode': 'form',
        }

    def action_print_treatment_invoice(self):
        return self.env.ref('dental_clinic.action_report_dental_treatment_invoice').report_action(self)


class DentalTreatmentLine(models.Model):
    _name = 'dental.treatment.line'
    _description = 'Dental Treatment Procedure'

    treatment_id = fields.Many2one('dental.treatment', string='Treatment', ondelete='cascade')
    service_id   = fields.Many2one('dental.service',   string='Service / Procedure', required=True)
    tooth_ids    = fields.Many2many('dental.tooth',    string='Teeth')
    tooth_numbers = fields.Char(string='Tooth Numbers', compute='_compute_tooth_numbers', store=True)
    quantity   = fields.Float(string='Qty',           default=1.0)
    unit_price = fields.Float(string='Unit Price')
    discount   = fields.Float(string='Disc (%)')
    tax_ids    = fields.Many2many('account.tax', string='Taxes',
                                  domain=[('type_tax_use', '=', 'sale')])
    subtotal   = fields.Float(string='Subtotal',    compute='_compute_subtotal',   store=True)
    tax_amount = fields.Float(string='Tax Amount',  compute='_compute_subtotal',   store=True)
    notes      = fields.Char(string='Notes')

    @api.depends('tooth_ids')
    def _compute_tooth_numbers(self):
        for rec in self:
            rec.tooth_numbers = ', '.join(rec.tooth_ids.mapped('tooth_number')) if rec.tooth_ids else ''

    @api.depends('quantity', 'unit_price', 'discount', 'tax_ids')
    def _compute_subtotal(self):
        for rec in self:
            base = rec.quantity * rec.unit_price * (1 - rec.discount / 100)
            rec.subtotal = base
            tax_res = rec.tax_ids.compute_all(base, quantity=1)
            rec.tax_amount = tax_res['total_included'] - tax_res['total_excluded']

    @api.onchange('service_id')
    def _onchange_service(self):
        if self.service_id:
            self.unit_price = self.service_id.price
            product = self.service_id.product_id
            if product and product.product_variant_id:
                self.tax_ids = product.product_variant_id.taxes_id.filtered(
                    lambda t: t.type_tax_use == 'sale'
                )
