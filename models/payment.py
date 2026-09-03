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

    booking_id = fields.Many2one(
        'beauty.booking',
        string='Booking',
        required=True,
        ondelete='cascade',
    )

    professional_id = fields.Many2one(
        'beauty.professional',
        string='Professional',
        related='booking_id.professional_id',
        store=True,
    )

    service_id = fields.Many2one(
        'beauty.service',
        string='Service',
        related='booking_id.service_id',
        store=True,
    )

    customer_name = fields.Char(
        string='Customer Name',
        related='booking_id.customer_name',
        store=True,
    )

    customer_phone = fields.Char(
        string='Customer Phone',
        related='booking_id.customer_phone',
        store=True,
    )

    customer_email = fields.Char(
        string='Customer Email',
        related='booking_id.customer_email',
        store=True,
    )

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
            booking_name = 'BK'
            if vals.get('booking_id'):
                booking = self.env['beauty.booking'].browse(vals['booking_id'])
                if booking.exists() and booking.name:
                    booking_name = booking.name
            vals['name'] = f"PAY-{booking_name}-{self.env['ir.sequence'].next_by_code('beauty.payment') or fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"
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

        client = self._get_pesepay_client()
        result = client.initiate_payment(
            merchant_reference=self.name,
            amount=self.amount,
            currency_code=self.currency,
            reason=f"Booking for {self.service_id.name or 'Service'} with {self.professional_id.name or 'Professional'}",
            result_url=result_url,
            return_url=return_url,
            customer_name=self.customer_name,
            customer_phone=self.customer_phone,
            customer_email=self.customer_email,
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
            # Fallback for sandbox testing when external internet or test server is simulated
            simulated_url = f"{base_url.rstrip('/')}/beauty/payment/result?ref={self.name}&simulated=1"
            self.write({
                'state': 'pending',
                'pesepay_reference': f"PSP-SIM-{self.name}",
                'redirect_url': simulated_url,
                'response_message': f"Sandbox Simulation Mode: {result.get('error') or 'Awaiting test payment'}",
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
        """Mark payment as completed, confirm the booking, and trigger email."""
        for record in self:
            record.write({
                'state': 'paid',
                'payment_date': fields.Datetime.now(),
                'response_message': 'Payment confirmed successfully via Pesepay.',
            })
            # Confirm booking if in draft or pending
            if record.booking_id and record.booking_id.state == 'draft':
                record.booking_id.action_confirm()
            # Send confirmation email
            if record.booking_id:
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
