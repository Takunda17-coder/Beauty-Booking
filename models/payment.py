# -*- coding: utf-8 -*-
"""
Beauty Payment Model
Tracks Pesepay transaction lifecycle, states, references, and linkages to customer bookings.
"""

from odoo import models, fields, api
from odoo.exceptions import UserError
from .pesepay_client import (
    PesepayClient,
    DEFAULT_INTEGRATION_KEY,
    DEFAULT_ENCRYPTION_KEY,
    PESEPAY_SANDBOX_BASE_URL,
)


class BeautyPayment(models.Model):
    _name = 'beauty.payment'
    _description = 'Beauty Booking Payment'
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Payment Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
    )

    payment_type = fields.Selection(
        selection=[
            ('booking', 'Customer Booking'),
            ('subscription', 'Professional SaaS Subscription'),
        ],
        string='Payment Type',
        default='booking',
        required=True,
    )

    booking_id = fields.Many2one(
        'beauty.booking',
        string='Booking',
        required=False,
        ondelete='cascade',
    )

    subscription_id = fields.Many2one(
        'beauty.subscription',
        string='Subscription',
        required=False,
        ondelete='set null',
    )

    professional_id = fields.Many2one(
        'beauty.professional',
        string='Professional',
        compute='_compute_party_details',
        store=True,
        readonly=False,
    )

    service_id = fields.Many2one(
        'beauty.service',
        string='Service',
        compute='_compute_party_details',
        store=True,
        readonly=False,
    )

    customer_name = fields.Char(
        string='Customer / Payer Name',
        compute='_compute_party_details',
        store=True,
        readonly=False,
    )

    customer_phone = fields.Char(
        string='Phone',
        compute='_compute_party_details',
        store=True,
        readonly=False,
    )

    customer_email = fields.Char(
        string='Email',
        compute='_compute_party_details',
        store=True,
        readonly=False,
    )

    @api.depends('booking_id', 'subscription_id', 'payment_type')
    def _compute_party_details(self):
        for record in self:
            if record.payment_type == 'subscription' and record.subscription_id:
                prof = record.subscription_id.professional_id
                record.professional_id = prof
                record.service_id = False
                record.customer_name = prof.name if prof else 'Professional'
                record.customer_phone = prof.phone if prof else ''
                record.customer_email = prof.email if prof else ''
            elif record.booking_id:
                record.professional_id = record.booking_id.professional_id
                record.service_id = record.booking_id.service_id
                record.customer_name = record.booking_id.customer_name
                record.customer_phone = record.booking_id.customer_phone
                record.customer_email = record.booking_id.customer_email

    amount = fields.Float(
        string='Amount',
        required=True,
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

    payment_method = fields.Selection(
        selection=[
            ('pesepay', 'Pesepay Gateway'),
            ('ecocash', 'EcoCash'),
            ('onemoney', 'OneMoney'),
            ('card', 'Visa / Mastercard'),
        ],
        string='Payment Method',
        default='pesepay',
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pending', 'Pending Payment'),
            ('paid', 'Paid'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Payment Status',
        default='draft',
        required=True,
    )

    pesepay_reference = fields.Char(
        string='Pesepay Reference',
        readonly=True,
        copy=False,
    )

    redirect_url = fields.Char(
        string='Checkout URL',
        readonly=True,
    )

    poll_url = fields.Char(
        string='Poll URL',
        readonly=True,
    )

    response_message = fields.Text(
        string='Gateway Response / Notes',
        readonly=True,
    )

    payment_date = fields.Datetime(
        string='Payment Date',
        readonly=True,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            prefix = 'BK'
            if vals.get('payment_type') == 'subscription':
                prefix = 'SUB'
            elif vals.get('booking_id'):
                booking = self.env['beauty.booking'].browse(vals['booking_id'])
                if booking.exists() and booking.name:
                    prefix = booking.name
            vals['name'] = f"PAY-{prefix}-{self.env['ir.sequence'].next_by_code('beauty.payment') or fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"
        return super().create(vals)

    def _get_pesepay_client(self):
        """Retrieve Pesepay client configured with system parameters or sandbox defaults."""
        config_obj = self.env['ir.config_parameter'].sudo()
        integration_key = config_obj.get_param('pesepay.integration_key', DEFAULT_INTEGRATION_KEY)
        encryption_key = config_obj.get_param('pesepay.encryption_key', DEFAULT_ENCRYPTION_KEY)
        base_url = config_obj.get_param('pesepay.base_url', PESEPAY_SANDBOX_BASE_URL)
        return PesepayClient(integration_key, encryption_key, base_url)

    def action_initiate_payment(self):
        """Initiate payment with Pesepay sandbox and obtain checkout URL."""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        result_url = f"{base_url.rstrip('/')}/beauty/payment/result?ref={self.name}"
        return_url = result_url

        if self.payment_type == 'subscription':
            plan_name = self.subscription_id.plan_id.name if self.subscription_id else 'SaaS Plan'
            reason = f"Beauty Booking SaaS Subscription - {plan_name}"
            prof = self.professional_id or (self.subscription_id.professional_id if self.subscription_id else None)
            customer_name = self.customer_name or (prof.name if prof else 'Professional')
            customer_phone = self.customer_phone or (prof.phone if prof else '')
            customer_email = self.customer_email or (prof.email if prof else '')
        else:
            reason = f"Booking for {self.service_id.name or 'Service'} with {self.professional_id.name or 'Professional'}"
            customer_name = self.customer_name
            customer_phone = self.customer_phone
            customer_email = self.customer_email

        client = self._get_pesepay_client()
        result = client.initiate_payment(
            merchant_reference=self.name,
            amount=self.amount,
            currency_code=self.currency,
            reason=reason,
            result_url=result_url,
            return_url=return_url,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            payment_method=self.payment_method,
        )

        if result['success']:
            self.write({
                'state': 'pending',
                'pesepay_reference': result['reference_number'],
                'redirect_url': result['redirect_url'],
                'poll_url': result['poll_url'],
                'response_message': 'Pesepay payment initiated successfully. Waiting for customer completion.',
            })
            return {
                'type': 'ir.actions.act_url',
                'url': result['redirect_url'],
                'target': 'new',
            }
        else:
            # Fallback for sandbox testing when external API test key is simulated
            simulated_url = f"{base_url.rstrip('/')}/beauty/payment/result?ref={self.name}&simulated=1"
            self.write({
                'state': 'pending',
                'pesepay_reference': f"PSP-SIM-{self.name}",
                'redirect_url': simulated_url,
                'response_message': f"Sandbox API Request Dispatched to {client.base_url}. Result: {result.get('error') or 'Awaiting test payment'}",
            })
            return {
                'type': 'ir.actions.act_url',
                'url': simulated_url,
                'target': 'self',
            }

    def action_check_status(self):
        """Query Pesepay API to verify payment state."""
        self.ensure_one()
        if not self.pesepay_reference:
            raise UserError('Payment has not been initiated yet with Pesepay.')

        client = self._get_pesepay_client()
        result = client.check_payment_status(self.pesepay_reference)

        if result['success']:
            if result['paid']:
                self.action_mark_paid()
                return {'type': 'ir.actions.client', 'tag': 'reload'}
            else:
                self.write({
                    'response_message': f"Latest Status: {result['status']}",
                })
        else:
            self.write({
                'response_message': f"Status check query note: {result.get('error')}",
            })
        return True

    def action_mark_paid(self):
        """Mark payment as completed, confirm the booking or activate subscription, and trigger email."""
        for record in self:
            record.write({
                'state': 'paid',
                'payment_date': fields.Datetime.now(),
                'response_message': 'Payment confirmed successfully via Pesepay.',
            })
            if record.payment_type == 'subscription' and record.subscription_id:
                record.subscription_id.action_activate_subscription()
            elif record.booking_id:
                if record.booking_id.state == 'draft':
                    record.booking_id.action_confirm()
                try:
                    record.booking_id.action_send_confirmation_email()
                except Exception:
                    pass

    def action_simulate_success(self):
        """Simulate a successful EcoCash / Card payment outcome in Sandbox mode."""
        self.ensure_one()
        self.write({
            'payment_method': 'ecocash',
            'pesepay_reference': self.pesepay_reference or f"PSP-ECOCASH-{self.name}",
        })
        self.action_mark_paid()

    def action_simulate_failure(self):
        """Simulate a failed / cancelled payment outcome in Sandbox mode."""
        self.ensure_one()
        self.write({
            'state': 'failed',
            'response_message': 'Simulated sandbox transaction failure (e.g. EcoCash timeout or insufficient funds).',
        })
