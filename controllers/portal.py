from datetime import datetime, timedelta

from odoo import fields, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request


class BeautyProfessionalPortal(http.Controller):
    """Professional portal for managing bookings and profile."""

    def _get_professional(self):
        """Get the current logged-in professional or raise AccessError."""
        professional = request.env['beauty.professional'].search([
            ('user_id', '=', request.env.user.id),
        ], limit=1)
        if not professional:
            raise AccessError('You are not registered as a beauty professional.')
        return professional

    @http.route(
        '/beauty/dashboard',
        type='http',
        auth='user',
        website=True,
    )
    def dashboard(self):
        """Professional dashboard with overview of bookings and stats."""
        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        # Get today and upcoming bookings
        today = fields.Date.today()
        today_bookings = request.env['beauty.booking'].search([
            ('professional_id', '=', professional.id),
            ('appointment_date', '>=', f'{today} 00:00:00'),
            ('appointment_date', '<', f'{today} 23:59:59'),
            ('state', 'in', ('draft', 'confirmed')),
        ], order='appointment_date asc')

        upcoming_bookings = request.env['beauty.booking'].search([
            ('professional_id', '=', professional.id),
            ('appointment_date', '>=', f'{today} 00:00:00'),
            ('state', 'in', ('draft', 'confirmed')),
        ], order='appointment_date asc', limit=10)

        # Get basic statistics
        total_bookings = request.env['beauty.booking'].search_count([
            ('professional_id', '=', professional.id),
        ])
        completed_bookings = request.env['beauty.booking'].search_count([
            ('professional_id', '=', professional.id),
            ('state', '=', 'completed'),
        ])

        values = {
            'professional': professional,
            'today_bookings': today_bookings,
            'upcoming_bookings': upcoming_bookings,
            'total_bookings': total_bookings,
            'completed_bookings': completed_bookings,
        }
        return request.render('beauty_booking.portal_dashboard', values)

    @http.route(
        '/beauty/profile',
        type='http',
        auth='user',
        website=True,
        methods=['GET', 'POST'],
        csrf=True,
    )
    def profile(self):
        """Edit professional profile."""
        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        if request.httprequest.method == 'POST':
            try:
                professional.write({
                    'bio': request.httprequest.form.get('bio', ''),
                    'phone': request.httprequest.form.get('phone', ''),
                    'email': request.httprequest.form.get('email', ''),
                    'location': request.httprequest.form.get('location', ''),
                })
                values = {
                    'professional': professional,
                    'message': 'Profile updated successfully!',
                }
            except ValidationError as error:
                values = {
                    'professional': professional,
                    'error': str(error),
                }
        else:
            values = {
                'professional': professional,
            }

        return request.render('beauty_booking.portal_profile', values)

    @http.route(
        '/beauty/bookings',
        type='http',
        auth='user',
        website=True,
    )
    def bookings(self):
        """View and manage bookings."""
        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        # Get all bookings for this professional
        bookings = request.env['beauty.booking'].search([
            ('professional_id', '=', professional.id),
        ], order='appointment_date desc')

        values = {
            'professional': professional,
            'bookings': bookings,
        }
        return request.render('beauty_booking.portal_bookings', values)

    @http.route(
        '/beauty/booking/<int:booking_id>/confirm',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def confirm_booking(self, booking_id):
        """Confirm a booking."""
        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        booking = request.env['beauty.booking'].browse(booking_id)
        if booking.professional_id != professional:
            raise AccessError('You can only manage your own bookings.')

        try:
            booking.action_confirm()
            request.session['success_message'] = f'Booking {booking.name} confirmed!'
        except ValidationError as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/bookings')

    @http.route(
        '/beauty/booking/<int:booking_id>/complete',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def complete_booking(self, booking_id):
        """Mark a booking as completed."""
        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        booking = request.env['beauty.booking'].browse(booking_id)
        if booking.professional_id != professional:
            raise AccessError('You can only manage your own bookings.')

        try:
            booking.action_complete()
            request.session['success_message'] = f'Booking {booking.name} completed!'
        except ValidationError as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/bookings')

    @http.route(
        '/beauty/booking/<int:booking_id>/cancel',
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def cancel_booking(self, booking_id):
        """Cancel a booking."""
        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        booking = request.env['beauty.booking'].browse(booking_id)
        if booking.professional_id != professional:
            raise AccessError('You can only manage your own bookings.')

        try:
            booking.action_cancel()
            request.session['success_message'] = f'Booking {booking.name} cancelled!'
        except ValidationError as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/bookings')

    @http.route(
        '/beauty/availability',
        type='http',
        auth='user',
        website=True,
    )
    def availability(self):
        """View and manage working hours."""
        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        values = {
            'professional': professional,
            'availability_ids': professional.availability_ids,
            'days': [
                ('0', 'Monday'),
                ('1', 'Tuesday'),
                ('2', 'Wednesday'),
                ('3', 'Thursday'),
                ('4', 'Friday'),
                ('5', 'Saturday'),
                ('6', 'Sunday'),
            ],
        }
        return request.render('beauty_booking.portal_availability', values)
