from odoo import models, fields


class DentalTooth(models.Model):
    _name = 'dental.tooth'
    _description = 'Dental Tooth Record'
    _rec_name = 'tooth_number'

    patient_id = fields.Many2one('dental.patient', string='Patient', required=True, ondelete='cascade')
    tooth_number = fields.Selection([
        ('11','11 - Upper Right Central Incisor'), ('12','12 - Upper Right Lateral Incisor'),
        ('13','13 - Upper Right Canine'),           ('14','14 - Upper Right 1st Premolar'),
        ('15','15 - Upper Right 2nd Premolar'),     ('16','16 - Upper Right 1st Molar'),
        ('17','17 - Upper Right 2nd Molar'),        ('18','18 - Upper Right Wisdom'),
        ('21','21 - Upper Left Central Incisor'),   ('22','22 - Upper Left Lateral Incisor'),
        ('23','23 - Upper Left Canine'),             ('24','24 - Upper Left 1st Premolar'),
        ('25','25 - Upper Left 2nd Premolar'),       ('26','26 - Upper Left 1st Molar'),
        ('27','27 - Upper Left 2nd Molar'),          ('28','28 - Upper Left Wisdom'),
        ('31','31 - Lower Left Central Incisor'),   ('32','32 - Lower Left Lateral Incisor'),
        ('33','33 - Lower Left Canine'),             ('34','34 - Lower Left 1st Premolar'),
        ('35','35 - Lower Left 2nd Premolar'),       ('36','36 - Lower Left 1st Molar'),
        ('37','37 - Lower Left 2nd Molar'),          ('38','38 - Lower Left Wisdom'),
        ('41','41 - Lower Right Central Incisor'),  ('42','42 - Lower Right Lateral Incisor'),
        ('43','43 - Lower Right Canine'),            ('44','44 - Lower Right 1st Premolar'),
        ('45','45 - Lower Right 2nd Premolar'),      ('46','46 - Lower Right 1st Molar'),
        ('47','47 - Lower Right 2nd Molar'),         ('48','48 - Lower Right Wisdom'),
    ], string='Tooth (FDI)', required=True)
    condition = fields.Selection([
        ('healthy',          'Healthy'),
        ('cavity',           'Cavity / Caries'),
        ('filled',           'Filled'),
        ('crown',            'Crown'),
        ('missing',          'Missing'),
        ('implant',          'Implant'),
        ('root_canal',       'Root Canal Treated'),
        ('needs_rct',        'Needs Root Canal'),
        ('needs_extraction', 'Needs Extraction'),
        ('fractured',        'Fractured / Broken'),
        ('sensitive',        'Sensitive'),
        ('bridge',           'Bridge'),
    ], string='Condition', default='healthy')
    surfaces = fields.Many2many('dental.tooth.surface', string='Affected Surfaces')
    notes = fields.Text(string='Clinical Notes')
    date_recorded = fields.Date(string='Date Recorded', default=fields.Date.today)
    doctor_id = fields.Many2one('dental.doctor', string='Recorded By')


class DentalToothSurface(models.Model):
    _name = 'dental.tooth.surface'
    _description = 'Tooth Surface'
    _rec_name = 'name'

    name = fields.Char(required=True)
    code = fields.Char()
