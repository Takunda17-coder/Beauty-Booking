import re

from odoo import http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request


class BeautyProfessionalAuth(http.Controller):
    """Authentication and registration controller for beauty professionals."""

    @http.route(
        '/beauty/login',
        type='http',
        auth='public',
        website=True,
        methods=['GET', 'POST'],
        csrf=True,
    )
    def login(self, redirect=None, **post):
        """Professional login page and authentication handler."""
        if not redirect:
            redirect = '/beauty/dashboard'

        # If user is already logged in and linked to a professional profile, redirect
        if request.session.uid:
            prof = request.env['beauty.professional'].sudo().search([
                ('user_id', '=', request.session.uid)
            ], limit=1)
            if prof:
                return request.redirect(redirect)

        values = {
            'error': None,
            'login': '',
            'redirect': redirect,
        }

        if request.httprequest.method == 'POST':
            login_val = post.get('login', '').strip()
            password_val = post.get('password', '')
            values['login'] = login_val

            try:
                # Attempt Odoo session authentication
                uid = request.session.authenticate(
                    request.db,
                    login_val,
                    password_val,
                )
                if uid:
                    # Check if user has a professional profile
                    prof = request.env['beauty.professional'].sudo().search([
                        ('user_id', '=', uid)
                    ], limit=1)
                    if not prof:
                        is_manager = request.env.user.has_group('beauty_booking.group_beauty_manager')
                        if not is_manager:
                            values['error'] = 'Account authenticated, but no Beauty Professional profile is linked. Please contact admin or register.'
                            return request.render('beauty_booking.portal_login', values)

                    return request.redirect(redirect)
                else:
                    values['error'] = 'Invalid email/username or password.'
            except AccessError:
                values['error'] = 'Access denied. Please check your credentials.'
            except Exception as e:
                values['error'] = str(e) or 'Authentication failed.'

        return request.render('beauty_booking.portal_login', values)

    @http.route(
        '/beauty/register',
        type='http',
        auth='public',
        website=True,
        methods=['GET', 'POST'],
        csrf=True,
    )
    def register(self, **post):
        """Professional self-registration page and logic."""
        if request.session.uid:
            prof = request.env['beauty.professional'].sudo().search([
                ('user_id', '=', request.session.uid)
            ], limit=1)
            if prof:
                return request.redirect('/beauty/dashboard')

        values = {
            'error': None,
            'post': post,
        }

        if request.httprequest.method == 'POST':
            name = post.get('name', '').strip()
            email = post.get('email', '').strip().lower()
            password = post.get('password', '')
            confirm_password = post.get('confirm_password', '')
            professional_type = post.get('professional_type', 'barber')
            username = post.get('username', '').strip().lower()
            phone = post.get('phone', '').strip()
            location = post.get('location', '').strip()

            try:
                # Validations
                if not name or not email or not password or not username:
                    raise ValidationError('Please fill in all required fields (Name, Email, Password, Booking URL Username).')
                if password != confirm_password:
                    raise ValidationError('Passwords do not match.')
                if len(password) < 6:
                    raise ValidationError('Password must be at least 6 characters long.')

                # Clean username format (alphanumeric and underscores)
                username_clean = re.sub(r'[^a-z0-9_]', '_', username)
                if not username_clean:
                    raise ValidationError('Invalid booking URL username format.')

                # Check if user already exists
                existing_user = request.env['res.users'].sudo().search([
                    ('login', '=', email)
                ], limit=1)
                if existing_user:
                    raise ValidationError('An account with this email already exists.')

                # Check if username already exists
                existing_prof = request.env['beauty.professional'].sudo().search([
                    ('username', '=', username_clean)
                ], limit=1)
                if existing_prof:
                    raise ValidationError(f'The booking URL username "{username_clean}" is already taken. Please choose another.')

                # Get Beauty Professional group
                group_user = request.env.ref('beauty_booking.group_beauty_user', raise_if_not_found=False)
                group_ids = [(4, group_user.id)] if group_user else []

                # Create Odoo User
                new_user = request.env['res.users'].sudo().create({
                    'name': name,
                    'login': email,
                    'email': email,
                    'password': password,
                    'groups_id': group_ids,
                })

                # Create Beauty Professional Profile
                request.env['beauty.professional'].sudo().create({
                    'name': name,
                    'professional_type': professional_type if professional_type in ('barber', 'hairdresser') else 'barber',
                    'user_id': new_user.id,
                    'username': username_clean,
                    'phone': phone,
                    'email': email,
                    'location': location,
                    'active': True,
                })

                # Auto-authenticate session
                request.session.authenticate(request.db, email, password)
                return request.redirect('/beauty/dashboard')

            except (ValidationError, AccessError) as err:
                values['error'] = str(err)
            except Exception as err:
                values['error'] = f'Registration error: {str(err)}'

        return request.render('beauty_booking.portal_register', values)

    @http.route(
        '/beauty/logout',
        type='http',
        auth='public',
        website=True,
    )
    def logout(self, redirect='/beauty/login'):
        """Professional logout handler."""
        request.session.logout(keep_db=True)
        return request.redirect(redirect)
