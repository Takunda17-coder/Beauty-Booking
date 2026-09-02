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

                request.env['beauty.booking'].sudo().create({
                    'professional_id': professional.id,
                    'service_id': service.id,
                    'customer_name': post.get('customer_name', '').strip(),
                    'customer_phone': post.get('customer_phone', '').strip(),
                    'customer_email': post.get('customer_email', '').strip(),
                    'appointment_date': fields.Datetime.to_string(appointment_date),
                    'notes': post.get('notes', '').strip(),
                })
                values['submitted'] = True
            except (ValueError, TypeError, ValidationError) as error:
                values['error'] = str(error)

        return request.render('beauty_booking.booking_page', values)
