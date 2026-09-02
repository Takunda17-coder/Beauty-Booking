from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BeautyService(models.Model):
    _name = 'beauty.service'
    _description = 'Beauty Service'
    _order = 'professional_id, name'

    name = fields.Char(
        string='Service Name',
        required=True
    )

    professional_id = fields.Many2one(
        'beauty.professional',
        string='Professional',
        required=True,
        ondelete='cascade'
    )

    description = fields.Text(
        string='Description'
    )

    price = fields.Float(
        string='Price',
        required=True
    )

    duration = fields.Integer(
        string='Duration (minutes)',
        required=True,
        default=30
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price < 0:
                raise ValidationError(
                    'Service price cannot be negative.'
                )

    @api.constrains('duration')
    def _check_duration(self):
        for record in self:
            if record.duration <= 0:
                raise ValidationError(
                    'Service duration must be greater than zero.'
                )