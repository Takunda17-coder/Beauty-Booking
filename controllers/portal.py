from datetime import datetime, timedelta

from odoo import fields, http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request

from ..models.mailtrap_client import (
    MAILTRAP_HOST,
    MAILTRAP_PORT,
    MAILTRAP_USER,
    send_mailtrap_email,
    test_mailtrap_connection,
)


class BeautyProfessionalPortal(http.Controller):
    """Professional portal for managing bookings, services, availability, and profile."""

    def _get_professional(self):
        """Get the current logged-in professional or raise AccessError."""
        if not request.session.uid or request.env.user._is_public():
            return None
        professional = request.env['beauty.professional'].sudo().search([
            ('user_id', '=', request.session.uid),
        ], limit=1)
        if not professional:
            raise AccessError('You are not registered as a beauty professional.')
        return professional

    def _check_auth_or_redirect(self):
        """Redirect to custom /beauty/login if user is not authenticated."""
        if not request.session.uid or request.env.user._is_public():
            path = request.httprequest.path
            return request.redirect(f'/beauty/login?redirect={path}')
        return None

    @http.route(
        '/beauty/dashboard',
        type='http',
        auth='public',
        website=True,
    )
    def dashboard(self):
        """Professional dashboard with overview of bookings and stats."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        # Get today and upcoming bookings
        today = fields.Date.today()
        today_bookings = request.env['beauty.booking'].sudo().search([
            ('professional_id', '=', professional.id),
            ('appointment_date', '>=', f'{today} 00:00:00'),
            ('appointment_date', '<', f'{today} 23:59:59'),
            ('state', 'in', ('draft', 'confirmed')),
        ], order='appointment_date asc')

        upcoming_bookings = request.env['beauty.booking'].sudo().search([
            ('professional_id', '=', professional.id),
            ('appointment_date', '>=', f'{today} 00:00:00'),
            ('state', 'in', ('draft', 'confirmed')),
        ], order='appointment_date asc', limit=10)

        # Get basic statistics
        total_bookings = request.env['beauty.booking'].sudo().search_count([
            ('professional_id', '=', professional.id),
        ])
        completed_bookings = request.env['beauty.booking'].sudo().search_count([
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
        auth='public',
        website=True,
        methods=['GET', 'POST'],
        csrf=True,
    )
    def profile(self):
        """Edit professional profile."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        values = {'professional': professional}

        if request.httprequest.method == 'POST':
            try:
                bio = request.httprequest.form.get('bio', '').strip()
                phone = request.httprequest.form.get('phone', '').strip()
                email = request.httprequest.form.get('email', '').strip()
                location = request.httprequest.form.get('location', '').strip()
                new_username = request.httprequest.form.get('username', '').strip().lower()

                # 1. Username validation & update
                if new_username and new_username != professional.username:
                    import re
                    if not re.match(r'^[a-z0-9_-]+$', new_username):
                        raise ValidationError('Username handle can only contain lowercase letters, numbers, underscores, and hyphens.')

                    existing_prof = request.env['beauty.professional'].sudo().search([
                        ('username', '=', new_username),
                        ('id', '!=', professional.id),
                    ], limit=1)
                    if existing_prof:
                        raise ValidationError(f'The username "{new_username}" is already taken by another professional.')

                    professional.sudo().write({'username': new_username})

                professional.sudo().write({
                    'bio': bio,
                    'phone': phone,
                    'email': email,
                    'location': location,
                })

                if email and professional.user_id:
                    professional.user_id.sudo().write({'email': email})

                # 2. Password Change Logic
                current_password = request.httprequest.form.get('current_password', '').strip()
                new_password = request.httprequest.form.get('new_password', '').strip()
                confirm_password = request.httprequest.form.get('confirm_password', '').strip()

                if current_password or new_password or confirm_password:
                    if not current_password:
                        raise ValidationError('Please enter your current password to authorize a password change.')
                    if not new_password:
                        raise ValidationError('Please enter your new password.')
                    if len(new_password) < 6:
                        raise ValidationError('New password must be at least 6 characters long.')
                    if new_password != confirm_password:
                        raise ValidationError('New password and confirmation password do not match.')

                    user = professional.user_id or request.env.user
                    try:
                        request.session.authenticate(request.session.db, user.login, current_password)
                    except Exception:
                        raise ValidationError('Current password entered is incorrect.')

                    user.sudo().write({'password': new_password})
                    values['message'] = 'Profile, username, and password updated successfully!'
                else:
                    values['message'] = 'Profile updated successfully!'

            except Exception as error:
                values['error'] = str(error)

        return request.render('beauty_booking.portal_profile', values)

    # ==================== BOOKINGS MANAGEMENT ====================

    @http.route(
        '/beauty/bookings',
        type='http',
        auth='public',
        website=True,
    )
    def bookings(self, state=None):
        """View and manage bookings."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        domain = [('professional_id', '=', professional.id)]
        if state in ('draft', 'confirmed', 'completed', 'cancelled', 'no_show'):
            domain.append(('state', '=', state))

        bookings = request.env['beauty.booking'].sudo().search(domain, order='appointment_date desc')
        services = professional.service_ids.filtered('active')

        values = {
            'professional': professional,
            'bookings': bookings,
            'services': services,
            'current_state': state or 'all',
            'today': fields.Date.today(),
            'message': request.session.pop('success_message', None),
            'error': request.session.pop('error_message', None),
        }
        return request.render('beauty_booking.portal_bookings', values)

    @http.route(
        '/beauty/booking/create',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def create_booking(self, **post):
        """Create a new booking manually from the portal."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        try:
            service_id = int(post.get('service_id', 0))
            service = request.env['beauty.service'].sudo().browse(service_id)
            if not service.exists() or service.professional_id != professional:
                raise ValidationError('Please select a valid service.')

            appointment_date_str = post.get('appointment_date', '')
            appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%dT%H:%M')

            if appointment_date < datetime.now():
                raise ValidationError('Appointment date must be in the future.')

            if not professional.is_available_at(appointment_date, service.duration):
                raise ValidationError('The selected time slot conflicts with existing appointments or working hours.')

            new_booking = request.env['beauty.booking'].sudo().create({
                'professional_id': professional.id,
                'service_id': service.id,
                'customer_name': post.get('customer_name', '').strip(),
                'customer_phone': post.get('customer_phone', '').strip(),
                'customer_email': post.get('customer_email', '').strip(),
                'appointment_date': fields.Datetime.to_string(appointment_date),
                'notes': post.get('notes', '').strip(),
                'state': 'confirmed' if post.get('auto_confirm') == '1' else 'draft',
            })
            request.session['success_message'] = f'Booking {new_booking.name} created successfully!'
        except Exception as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/bookings')

    @http.route('/beauty/booking/<int:booking_id>/confirm', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def confirm_booking(self, booking_id):
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect
        try:
            professional = self._get_professional()
            booking = request.env['beauty.booking'].sudo().browse(booking_id)
            if booking.professional_id != professional:
                raise AccessError('You can only manage your own bookings.')
            booking.action_confirm()
            request.session['success_message'] = f'Booking {booking.name} confirmed!'
        except Exception as error:
            request.session['error_message'] = str(error)
        return request.redirect('/beauty/bookings')

    @http.route('/beauty/booking/<int:booking_id>/complete', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def complete_booking(self, booking_id):
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect
        try:
            professional = self._get_professional()
            booking = request.env['beauty.booking'].sudo().browse(booking_id)
            if booking.professional_id != professional:
                raise AccessError('You can only manage your own bookings.')
            booking.action_complete()
            request.session['success_message'] = f'Booking {booking.name} completed!'
        except Exception as error:
            request.session['error_message'] = str(error)
        return request.redirect('/beauty/bookings')

    @http.route('/beauty/booking/<int:booking_id>/cancel', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def cancel_booking(self, booking_id):
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect
        try:
            professional = self._get_professional()
            booking = request.env['beauty.booking'].sudo().browse(booking_id)
            if booking.professional_id != professional:
                raise AccessError('You can only manage your own bookings.')
            booking.action_cancel()
            request.session['success_message'] = f'Booking {booking.name} cancelled!'
        except Exception as error:
            request.session['error_message'] = str(error)
        return request.redirect('/beauty/bookings')

    # ==================== SERVICES MANAGEMENT ====================

    @http.route(
        '/beauty/services',
        type='http',
        auth='public',
        website=True,
    )
    def services(self):
        """View and manage professional services."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        services_list = request.env['beauty.service'].sudo().search([
            ('professional_id', '=', professional.id),
        ], order='name asc')

        values = {
            'professional': professional,
            'services': services_list,
            'message': request.session.pop('success_message', None),
            'error': request.session.pop('error_message', None),
        }
        return request.render('beauty_booking.portal_services', values)

    @http.route(
        '/beauty/services/add',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def add_service(self, **post):
        """Add a new service directly from the portal."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        try:
            name = post.get('name', '').strip()
            price = float(post.get('price', 0))
            duration = int(post.get('duration', 30))
            description = post.get('description', '').strip()

            if not name:
                raise ValidationError('Service name is required.')
            if price < 0:
                raise ValidationError('Price cannot be negative.')
            if duration <= 0:
                raise ValidationError('Duration must be greater than 0 minutes.')

            image_file = request.httprequest.files.get('image')
            image_binary = False
            if image_file and image_file.filename:
                import base64
                image_binary = base64.b64encode(image_file.read())

            vals = {
                'name': name,
                'professional_id': professional.id,
                'price': price,
                'duration': duration,
                'description': description,
                'active': True,
            }
            if image_binary:
                vals['image'] = image_binary

            new_service = request.env['beauty.service'].sudo().create(vals)
            request.session['success_message'] = f'Service "{new_service.name}" added successfully!'
        except Exception as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/services')

    @http.route(
        '/beauty/service/<int:service_id>/update',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def update_service(self, service_id, **post):
        """Update an existing service directly from the portal."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        try:
            service = request.env['beauty.service'].sudo().browse(service_id)
            if service.professional_id != professional:
                raise AccessError('You can only edit your own services.')

            name = post.get('name', '').strip()
            price = float(post.get('price', service.price))
            duration = int(post.get('duration', service.duration))
            description = post.get('description', '').strip()

            if not name:
                raise ValidationError('Service name cannot be empty.')
            if price < 0:
                raise ValidationError('Price cannot be negative.')
            if duration <= 0:
                raise ValidationError('Duration must be positive.')

            image_file = request.httprequest.files.get('image')
            vals = {
                'name': name,
                'price': price,
                'duration': duration,
                'description': description,
            }
            if image_file and image_file.filename:
                import base64
                vals['image'] = base64.b64encode(image_file.read())

            service.sudo().write(vals)
            request.session['success_message'] = f'Service "{service.name}" updated successfully!'
        except Exception as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/services')

    @http.route(
        '/beauty/service/<int:service_id>/delete',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def delete_service(self, service_id):
        """Delete a service directly from the portal."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        try:
            service = request.env['beauty.service'].sudo().browse(service_id)
            if service.professional_id != professional:
                raise AccessError('You can only delete your own services.')

            name = service.name
            service.sudo().unlink()
            request.session['success_message'] = f'Service "{name}" deleted successfully!'
        except Exception as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/services')

    # ==================== AVAILABILITY MANAGEMENT ====================

    @http.route(
        '/beauty/availability',
        type='http',
        auth='public',
        website=True,
    )
    def availability(self):
        """View and manage working hours directly from the portal."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        availabilities = request.env['beauty.availability'].sudo().search([
            ('professional_id', '=', professional.id),
        ], order='day_of_week asc, time_start asc')

        values = {
            'professional': professional,
            'availability_ids': availabilities,
            'days': [
                ('0', 'Monday'),
                ('1', 'Tuesday'),
                ('2', 'Wednesday'),
                ('3', 'Thursday'),
                ('4', 'Friday'),
                ('5', 'Saturday'),
                ('6', 'Sunday'),
            ],
            'message': request.session.pop('success_message', None),
            'error': request.session.pop('error_message', None),
        }
        return request.render('beauty_booking.portal_availability', values)

    @http.route(
        '/beauty/availability/add',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def add_availability(self, **post):
        """Add working hours slot directly from the portal."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        try:
            day_of_week = post.get('day_of_week', '0')
            time_start = float(post.get('time_start', 9.0))
            time_end = float(post.get('time_end', 17.0))
            is_working_day = post.get('is_working_day') == '1'

            if time_start < 0 or time_end > 24 or time_start >= time_end:
                raise ValidationError('Start time must be before end time and within 00:00 - 24:00.')

            new_avail = request.env['beauty.availability'].sudo().create({
                'professional_id': professional.id,
                'day_of_week': day_of_week,
                'time_start': time_start,
                'time_end': time_end,
                'is_working_day': is_working_day,
            })
            request.session['success_message'] = 'Working hours updated successfully!'
        except Exception as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/availability')

    @http.route(
        '/beauty/availability/<int:avail_id>/delete',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def delete_availability(self, avail_id):
        """Delete working hours slot directly from the portal."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        try:
            avail = request.env['beauty.availability'].sudo().browse(avail_id)
            if avail.professional_id != professional:
                raise AccessError('You can only manage your own schedule.')

            avail.sudo().unlink()
            request.session['success_message'] = 'Schedule entry deleted.'
        except Exception as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/availability')

    # ==================== EMAIL SANDBOX MANAGEMENT ====================

    @http.route(
        '/beauty/email_sandbox',
        type='http',
        auth='public',
        website=True,
    )
    def email_sandbox(self):
        """View captured booking confirmation emails in the local sandbox."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        # Fetch captured emails from mail.mail
        emails = request.env['mail.mail'].sudo().search([
            '|',
            ('model', '=', 'beauty.booking'),
            ('subject', 'ilike', 'Booking'),
        ], order='create_date desc', limit=50)

        # Active mail server status
        mail_servers = request.env['ir.mail_server'].sudo().search([('active', '=', True)])
        sandbox_server = mail_servers.filtered(
            lambda s: 'mailtrap' in (s.name or '').lower()
            or 'mailtrap' in (s.smtp_host or '').lower()
            or s.smtp_port in (2525, 1025)
            or 'sandbox' in (s.name or '').lower()
        )

        conn_ok, conn_msg = test_mailtrap_connection()

        values = {
            'professional': professional,
            'emails': emails,
            'mail_servers': mail_servers,
            'sandbox_server': sandbox_server[0] if sandbox_server else None,
            'mailtrap_host': MAILTRAP_HOST,
            'mailtrap_port': MAILTRAP_PORT,
            'mailtrap_user': MAILTRAP_USER,
            'mailtrap_connected': conn_ok,
            'mailtrap_status_msg': conn_msg,
            'message': request.session.pop('success_message', None),
            'error': request.session.pop('error_message', None),
        }
        return request.render('beauty_booking.portal_email_sandbox', values)

    @http.route(
        '/beauty/email_sandbox/test',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def test_email_sandbox(self, **post):
        """Trigger a test confirmation email for sandbox inspection."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        try:
            booking = request.env['beauty.booking'].sudo().search([
                ('professional_id', '=', professional.id),
            ], limit=1, order='create_date desc')

            if not booking:
                # Create a sample test booking
                service = professional.service_ids[0] if professional.service_ids else request.env['beauty.service'].sudo().create({
                    'name': 'Sample Styling Service',
                    'professional_id': professional.id,
                    'price': 45.0,
                    'duration': 45,
                })
                booking = request.env['beauty.booking'].sudo().create({
                    'professional_id': professional.id,
                    'service_id': service.id,
                    'customer_name': 'Test Client',
                    'customer_email': 'test.client@example.com',
                    'customer_phone': '(555) 123-4567',
                    'appointment_date': fields.Datetime.now() + timedelta(days=1),
                    'state': 'confirmed',
                })

            # Trigger standard booking confirmation dispatch
            booking.action_send_confirmation_email()

            # Also send explicit test email via smtplib to verify the raw sandbox pipeline
            sender = f"{professional.name} <from@example.com>" if professional.name else "Private Person <from@example.com>"
            receiver = f"{booking.customer_name} <{booking.customer_email}>"
            test_msg = (
                f"Subject: Hi Mailtrap - Booking Test\n"
                f"To: {receiver}\n"
                f"From: {sender}\n\n"
                f"This is a test e-mail message for Beauty Booking appointment {booking.name}."
            )
            smtp_success, smtp_info = send_mailtrap_email(
                sender=sender,
                receiver=receiver,
                subject=f"Hi Mailtrap - Booking {booking.name}",
                message_text=test_msg,
            )

            if smtp_success:
                request.session['success_message'] = (
                    f'Test email sent to Mailtrap Sandbox ({MAILTRAP_HOST}:{MAILTRAP_PORT}) '
                    f'for booking reference {booking.name}! Check your Mailtrap inbox.'
                )
            else:
                request.session['error_message'] = f'Mailtrap send notice: {smtp_info}'
        except Exception as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/email_sandbox')

    @http.route(
        '/beauty/email_sandbox/clear',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def clear_email_sandbox(self):
        """Clear captured sandbox emails."""
        redirect = self._check_auth_or_redirect()
        if redirect:
            return redirect

        try:
            professional = self._get_professional()
        except AccessError:
            return request.render('beauty_booking.portal_access_denied')

        try:
            emails = request.env['mail.mail'].sudo().search([
                '|',
                ('model', '=', 'beauty.booking'),
                ('subject', 'ilike', 'Booking'),
            ])
            emails.sudo().unlink()
            request.session['success_message'] = 'Sandbox email inbox cleared!'
        except Exception as error:
            request.session['error_message'] = str(error)

        return request.redirect('/beauty/email_sandbox')

