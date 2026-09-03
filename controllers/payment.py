# -*- coding: utf-8 -*-
"""
Pesepay Payment Controller
Handles payment initiation, gateway redirection, return callbacks, and sandbox simulations.
"""

import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BeautyPaymentController(http.Controller):

    @http.route(
        '/beauty/payment/pay/<int:booking_id>',
        type='http',
        auth='public',
        website=True,
        methods=['GET', 'POST'],
        csrf=False,
    )
    def pay_booking(self, booking_id, **kw):
        """Initiate Pesepay payment for a given booking and redirect to checkout."""
        booking = request.env['beauty.booking'].sudo().browse(booking_id)
        if not booking.exists():
            return request.not_found()

        # Find existing pending payment or create new
        payment = booking.payment_ids.filtered(lambda p: p.state in ('draft', 'pending'))[:1]
        
        vals = {
            'amount': booking.price,
            'currency': 'USD',
            'state': 'draft',
        }
        if kw.get('payment_method'):
            vals['payment_method'] = kw.get('payment_method')
        if kw.get('payer_phone'):
            vals['customer_phone'] = kw.get('payer_phone')
        if kw.get('payer_email'):
            vals['customer_email'] = kw.get('payer_email')
        if kw.get('payer_name'):
            vals['customer_name'] = kw.get('payer_name')

        if not payment:
            vals['booking_id'] = booking.id
            payment = request.env['beauty.payment'].sudo().create(vals)
        else:
            payment.sudo().write(vals)

        action = payment.sudo().action_initiate_payment()
        redirect_url = action.get('url') if isinstance(action, dict) else payment.redirect_url

        if redirect_url:
            return request.redirect(redirect_url)

        # Fallback to local result view if URL generation failed
        return request.redirect(f"/beauty/payment/result?ref={payment.name}&error=init_failed")

    @http.route(
        '/beauty/payment/result',
        type='http',
        auth='public',
        website=True,
        methods=['GET', 'POST'],
        csrf=False,
    )
    def payment_result(self, ref=None, simulated=None, **kw):
        """Callback landing page when customer returns from Pesepay gateway."""
        if not ref:
            return request.redirect('/')

        payment = request.env['beauty.payment'].sudo().search([
            ('name', '=', ref)
        ], limit=1)

        if not payment:
            return request.render('beauty_booking.payment_result', {
                'payment': None,
                'error': f'Payment reference {ref} not found.',
                'booking': None,
            })

        # If simulated query param is passed, or if sandbox fallback is triggered
        if simulated:
            payment.action_simulate_success()

        # Check latest status from Pesepay API if not already marked paid
        if payment.state != 'paid':
            try:
                payment.action_check_status()
            except Exception as e:
                _logger.warning("Error checking status during result callback: %s", str(e))

        # When a transaction is made by the professional, redirect to the dashboard
        if payment.payment_type == 'subscription':
            if simulated and payment.state != 'paid':
                payment.action_mark_paid()
            plan_name = payment.subscription_id.plan_id.name if payment.subscription_id and payment.subscription_id.plan_id else 'Membership'
            if payment.state == 'paid':
                msg = f"Subscription to {plan_name} has been successfully activated and paid via Pesepay Sandbox!"
            else:
                msg = f"Subscription transaction initiated with Pesepay (Status: {payment.state.title()})."
            status = 'success' if payment.state == 'paid' else 'pending'
            return request.redirect(f"/beauty/dashboard?message={msg}&txn_ref={payment.name}&txn_status={status}")

        values = {
            'payment': payment,
            'booking': payment.booking_id,
            'professional': payment.professional_id,
            'service': payment.service_id,
            'error': None,
        }
        return request.render('beauty_booking.payment_result', values)

    @http.route(
        '/beauty/payment/ipn',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=False,
    )
    def payment_ipn(self, **post):
        """Asynchronous Instant Payment Notification (IPN) webhook from Pesepay."""
        raw_body = request.httprequest.data.decode('utf-8')
        _logger.info("Pesepay IPN received: %s", raw_body)

        try:
            payload_json = json.loads(raw_body)
            encrypted_payload = payload_json.get('payload')
            client = request.env['beauty.payment'].sudo()._get_pesepay_client()

            if encrypted_payload:
                decrypted = client.decrypt_payload(encrypted_payload)
            else:
                decrypted = payload_json

            ref = decrypted.get('merchantReference') or decrypted.get('reference')
            transaction_status = decrypted.get('transactionStatus', '').upper()

            if ref:
                payment = request.env['beauty.payment'].sudo().search([
                    ('name', '=', ref)
                ], limit=1)
                if payment:
                    if transaction_status in ('SUCCESS', 'PAID', 'COMPLETED'):
                        payment.action_mark_paid()
                    elif transaction_status in ('FAILED', 'CANCELLED'):
                        payment.write({
                            'state': 'failed',
                            'response_message': f"IPN indicated status: {transaction_status}",
                        })
            return request.make_response(
                json.dumps({'status': 'SUCCESS'}),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as exc:
            _logger.error("Failed to process Pesepay IPN: %s", str(exc))
            return request.make_response(
                json.dumps({'status': 'ERROR', 'message': str(exc)}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )

    @http.route(
        '/beauty/payment/simulate/<int:payment_id>',
        type='http',
        auth='public',
        website=True,
        methods=['GET', 'POST'],
        csrf=False,
    )
    def simulate_sandbox_payment(self, payment_id, channel='ecocash', outcome='success', **kw):
        """Sandbox helper route to simulate instant EcoCash, OneMoney, or Card transaction."""
        payment = request.env['beauty.payment'].sudo().browse(payment_id)
        if not payment.exists():
            return request.not_found()

        payment.write({'payment_method': channel})
        if outcome == 'success':
            payment.action_simulate_success()
        else:
            payment.action_simulate_failure()

        return request.redirect(f"/beauty/payment/result?ref={payment.name}")
