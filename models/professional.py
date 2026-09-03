from odoo import models, fields


class BeautyProfessional(models.Model):
    _name = 'beauty.professional'
    _description = 'Beauty Professional'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True
    )

    professional_type = fields.Selection(
        selection=[
            ('barber', 'Barber'),
            ('hairdresser', 'Hairdresser'),
        ],
        string='Professional Type',
        required=True,
        default='barber'
    )

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        related='user_id.partner_id',
        store=True
    )

    username = fields.Char(
        string='Booking URL',
        required=True,
        copy=False
    )

    booking_url = fields.Char(
        string='Customer Booking Link',
        compute='_compute_booking_url'
    )

    professional_type_display = fields.Char(
        string='Professional Type Display',
        compute='_compute_professional_type_display',
        store=False
    )

    bio = fields.Text(
        string='Biography'
    )

    phone = fields.Char(
        string='Phone'
    )

    email = fields.Char(
        string='Email'
    )

    location = fields.Char(
        string='Location'
    )

    profile_image = fields.Image(
        string='Profile Image'
    )

    active = fields.Boolean(
        default=True
    )

    verified = fields.Boolean(
        string='Verified',
        default=False
    )

    service_ids = fields.One2many(
        'beauty.service',
        'professional_id',
        string='Services'
    )

    subscription_ids = fields.One2many(
        'beauty.subscription',
        'professional_id',
        string='Subscriptions'
    )

    active_subscription_id = fields.Many2one(
        'beauty.subscription',
        string='Active Subscription',
        compute='_compute_active_subscription'
    )

    subscription_plan_id = fields.Many2one(
        'beauty.subscription.plan',
        string='Current Plan',
        related='active_subscription_id.plan_id'
    )

    subscription_status = fields.Selection(
        string='SaaS Status',
        related='active_subscription_id.status'
    )

    def _compute_active_subscription(self):
        for record in self:
            sub = record.subscription_ids.filtered(lambda s: s.status in ('active', 'trialing'))[:1]
            record.active_subscription_id = sub or False

    def _compute_booking_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for professional in self:
            professional.booking_url = '%s/beauty/book/%s' % (
                base_url.rstrip('/'),
                professional.username,
            )

    def _compute_professional_type_display(self):
        """Get the display label for professional_type selection."""
        type_labels = {
            'barber': 'Barber',
            'hairdresser': 'Hairdresser',
        }
        for professional in self:
            professional.professional_type_display = type_labels.get(
                professional.professional_type, 
                professional.professional_type
            )

    def action_open_booking_page(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.booking_url,
            'target': 'new',
        }