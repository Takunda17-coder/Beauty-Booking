# -*- coding: utf-8 -*-
"""
Professional SaaS Subscription Architecture
Defines subscription tiers, limits, active billing cycles, and automated Pesepay renewal integration.
"""

from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError


class BeautySubscriptionPlan(models.Model):
    _name = 'beauty.subscription.plan'
    _description = 'Professional Subscription Plan'
    _order = 'price asc, id asc'

    name = fields.Char(
        string='Plan Name',
        required=True,
    )

    code = fields.Char(
        string='Plan Code',
        required=True,
        help='Unique identifier (e.g. starter, pro, salon)',
    )

    price = fields.Float(
        string='Price',
        required=True,
        default=0.0,
    )

    currency = fields.Selection(
        selection=[
            ('USD', 'USD ($)'),
            ('ZWL', 'ZWL / ZiG'),
        ],
        string='Currency',
        default='USD',
        required=True,
    )

    billing_interval = fields.Selection(
        selection=[
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        string='Billing Cycle',
        default='monthly',
        required=True,
    )

    max_services = fields.Integer(
        string='Max Services',
        default=5,
        help='Maximum number of services allowed (0 for unlimited)',
    )

    max_bookings_month = fields.Integer(
        string='Max Monthly Bookings',
        default=50,
        help='Maximum bookings allowed per month (0 for unlimited)',
    )

    featured_listing = fields.Boolean(
        string='Featured in Search',
        default=False,
    )

    sms_notifications = fields.Boolean(
        string='SMS Appointment Reminders',
        default=False,
    )

    custom_domain = fields.Boolean(
        string='Custom Domain Support',
        default=False,
    )

    analytics_dashboard = fields.Boolean(
        string='Advanced Analytics',
        default=False,
    )

    description = fields.Text(
        string='Plan Description',
    )

    active = fields.Boolean(
        default=True,
    )


class BeautySubscription(models.Model):
    _name = 'beauty.subscription'
    _description = 'Professional SaaS Subscription'
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Subscription Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
    )

    professional_id = fields.Many2one(
        'beauty.professional',
        string='Professional',
        required=True,
        ondelete='cascade',
    )

    plan_id = fields.Many2one(
        'beauty.subscription.plan',
        string='Subscription Plan',
        required=True,
        ondelete='restrict',
    )

    status = fields.Selection(
        selection=[
            ('trialing', 'Trialing (14-Day Free)'),
            ('active', 'Active'),
            ('past_due', 'Past Due'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='trialing',
        required=True,
        tracking=True,
    )

    current_period_start = fields.Datetime(
        string='Period Start',
        default=fields.Datetime.now,
        required=True,
    )

    current_period_end = fields.Datetime(
        string='Period End',
        required=True,
    )

    auto_renew = fields.Boolean(
        string='Auto Renew',
        default=True,
    )

    payment_ids = fields.One2many(
        'beauty.payment',
        'subscription_id',
        string='Billing History',
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('beauty.subscription') or f"SUB-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not vals.get('current_period_end'):
            # Default 14-day trial
            start = fields.Datetime.from_string(vals.get('current_period_start', fields.Datetime.now()))
            vals['current_period_end'] = start + timedelta(days=14)
        return super().create(vals)

    def action_renew_subscription(self):
        """Initiates a Pesepay payment for the subscription renewal."""
        self.ensure_one()
        if self.plan_id.price <= 0:
            self.action_activate_subscription()
            return True

        payment = self.env['beauty.payment'].sudo().create({
            'payment_type': 'subscription',
            'subscription_id': self.id,
            'professional_id': self.professional_id.id,
            'amount': self.plan_id.price,
            'currency': self.plan_id.currency or 'USD',
            'state': 'draft',
        })
        return payment.action_initiate_payment()

    def action_activate_subscription(self):
        """Activates or extends subscription period upon successful Pesepay payment."""
        for record in self:
            days = 365 if record.plan_id.billing_interval == 'yearly' else 30
            start = fields.Datetime.now()
            # If current period is still in future, extend from current_period_end
            if record.current_period_end and record.current_period_end > start:
                start = record.current_period_end

            record.write({
                'status': 'active',
                'current_period_start': fields.Datetime.now(),
                'current_period_end': start + timedelta(days=days),
            })

    def action_cancel_subscription(self):
        """Cancel subscription at end of period."""
        self.write({
            'status': 'cancelled',
            'auto_renew': False,
        })
