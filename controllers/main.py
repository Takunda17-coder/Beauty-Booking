import base64
from datetime import datetime

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request


class BeautyBookingController(http.Controller):

    @http.route(
        [
            '/beauty/book/<string:username>',
            '/beauty/book/<string:username>/book',
        ],
        type='http',
        auth='public',
        website=True,
        methods=['GET', 'POST'],
        csrf=True,
    )
    def booking_page(self, username, **post):
        professional = request.env['beauty.professional'].sudo().search([
            ('username', '=', username),
            ('active', '=', True),
        ], limit=1)
        if not professional:
            return request.not_found()

        services = professional.service_ids.filtered('active')
        values = {
            'professional': professional,
            'services': services,
            'error': None,
            'submitted': False,
            'post': post,
            'today': fields.Date.today(),
        }

        if request.httprequest.method == 'POST':
            try:
                service = request.env['beauty.service'].sudo().browse(
                    int(post.get('service_id', 0))
                )
                if not service.exists() or service.professional_id != professional:
                    raise ValidationError('Please select a valid service.')

                appointment_date = datetime.strptime(
                    post.get('appointment_date', ''),
                    '%Y-%m-%dT%H:%M',
                )
                if appointment_date < fields.Datetime.now():
                    raise ValidationError('Please choose a future appointment time.')
                if not professional.is_available_at(
                    appointment_date,
                    service.duration,
                ):
                    raise ValidationError(
                        'That time is outside the professional\'s working hours '
                        'or is already booked.'
                    )

                new_booking = request.env['beauty.booking'].sudo().create({
                    'professional_id': professional.id,
                    'service_id': service.id,
                    'customer_name': post.get('customer_name', '').strip(),
                    'customer_phone': post.get('customer_phone', '').strip(),
                    'customer_email': post.get('customer_email', '').strip(),
                    'appointment_date': fields.Datetime.to_string(appointment_date),
                    'notes': post.get('notes', '').strip(),
                })
                values['submitted'] = True
                values['new_booking'] = new_booking
            except (ValueError, TypeError, ValidationError) as error:
                values['error'] = str(error)

        return request.render('beauty_booking.booking_page', values)

    @http.route(
        '/beauty/service/<int:service_id>/image',
        type='http',
        auth='public',
        website=True,
    )
    def service_image(self, service_id):
        """Serve service image binary or placeholder SVG."""
        service = request.env['beauty.service'].sudo().browse(service_id)
        if service.exists() and service.image:
            image_data = base64.b64decode(service.image)
            return request.make_response(
                image_data,
                headers=[
                    ('Content-Type', 'image/png'),
                    ('Cache-Control', 'max-age=3600'),
                ]
            )

        # SVG placeholder generator
        name = service.name if service.exists() else "Beauty Service"
        price_str = f"${service.price:.2f}" if service.exists() else "$0.00"
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
            <defs>
                <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#0f172a;stop-opacity:1" />
                    <stop offset="50%" style="stop-color:#1e1b4b;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#4c1d95;stop-opacity:1" />
                </linearGradient>
            </defs>
            <rect width="600" height="400" fill="url(#grad)" />
            <circle cx="300" cy="160" r="60" fill="#7c3aed" opacity="0.3"/>
            <path d="M 280 140 L 320 180 M 320 140 L 280 180" stroke="#ffffff" stroke-width="8" stroke-linecap="round"/>
            <text x="300" y="260" font-family="'Plus Jakarta Sans', system-ui, sans-serif" font-size="26" font-weight="bold" fill="#ffffff" text-anchor="middle">{name}</text>
            <text x="300" y="300" font-family="'Plus Jakarta Sans', system-ui, sans-serif" font-size="20" font-weight="800" fill="#a7f3d0" text-anchor="middle">{price_str}</text>
        </svg>"""
        return request.make_response(
            svg_content.encode('utf-8'),
            headers=[
                ('Content-Type', 'image/svg+xml'),
                ('Cache-Control', 'max-age=3600'),
            ]
        )
