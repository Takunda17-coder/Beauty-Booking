from odoo import models, fields, api
from datetime import datetime, timedelta


class BeautyReportingMethods(models.Model):
    """Add reporting and analytics methods to booking model."""
    
    _inherit = 'beauty.booking'

    @api.model
    def get_today_bookings(self):
        """Get all bookings for today."""
        today = fields.Date.today()
        return self.search([
            ('appointment_date', '>=', f"{today} 00:00:00"),
            ('appointment_date', '<', f"{today} 23:59:59"),
            ('state', 'in', ('draft', 'confirmed'))
        ])

    @api.model
    def get_upcoming_bookings(self, days=7):
        """Get bookings for the next N days."""
        today = fields.Date.today()
        future_date = today + timedelta(days=days)
        return self.search([
            ('appointment_date', '>=', f"{today} 00:00:00"),
            ('appointment_date', '<', f"{future_date} 23:59:59"),
            ('state', 'in', ('draft', 'confirmed')),
            ('professional_id.active', '=', True)
        ], order='appointment_date asc')

    @api.model
    def get_professional_bookings(self, professional_id, start_date=None, end_date=None):
        """Get bookings for a specific professional within date range."""
        if not start_date:
            start_date = fields.Date.today()
        if not end_date:
            end_date = start_date + timedelta(days=30)
        
        return self.search([
            ('professional_id', '=', professional_id),
            ('appointment_date', '>=', f"{start_date} 00:00:00"),
            ('appointment_date', '<=', f"{end_date} 23:59:59"),
            ('state', '!=', 'cancelled')
        ], order='appointment_date asc')

    @api.model
    def get_booking_statistics(self, start_date=None, end_date=None):
        """Get booking statistics for date range.
        
        Returns dict with:
        - total_bookings: Total number of bookings
        - completed: Number of completed bookings
        - cancelled: Number of cancelled bookings
        - no_show: Number of no-show bookings
        - total_revenue: Sum of all booking prices
        - average_price: Average booking price
        """
        if not start_date:
            start_date = fields.Date.today()
        if not end_date:
            end_date = start_date + timedelta(days=30)
        
        bookings = self.search([
            ('appointment_date', '>=', f"{start_date} 00:00:00"),
            ('appointment_date', '<=', f"{end_date} 23:59:59"),
        ])
        
        if not bookings:
            return {
                'total_bookings': 0,
                'completed': 0,
                'cancelled': 0,
                'no_show': 0,
                'total_revenue': 0.0,
                'average_price': 0.0
            }
        
        return {
            'total_bookings': len(bookings),
            'completed': len(bookings.filtered(lambda b: b.state == 'completed')),
            'cancelled': len(bookings.filtered(lambda b: b.state == 'cancelled')),
            'no_show': len(bookings.filtered(lambda b: b.state == 'no_show')),
            'total_revenue': sum(bookings.mapped('price')),
            'average_price': sum(bookings.mapped('price')) / len(bookings) if bookings else 0.0
        }

    @api.model
    def get_professional_statistics(self, professional_id, start_date=None, end_date=None):
        """Get statistics for a specific professional."""
        if not start_date:
            start_date = fields.Date.today()
        if not end_date:
            end_date = start_date + timedelta(days=30)
        
        bookings = self.get_professional_bookings(professional_id, start_date, end_date)
        
        if not bookings:
            return {
                'professional_id': professional_id,
                'total_bookings': 0,
                'completed': 0,
                'cancelled': 0,
                'no_show': 0,
                'total_revenue': 0.0,
                'average_booking_value': 0.0,
                'completion_rate': 0.0
            }
        
        completed_count = len(bookings.filtered(lambda b: b.state == 'completed'))
        total_revenue = sum(bookings.mapped('price'))
        
        return {
            'professional_id': professional_id,
            'total_bookings': len(bookings),
            'completed': completed_count,
            'cancelled': len(bookings.filtered(lambda b: b.state == 'cancelled')),
            'no_show': len(bookings.filtered(lambda b: b.state == 'no_show')),
            'total_revenue': total_revenue,
            'average_booking_value': total_revenue / len(bookings) if bookings else 0.0,
            'completion_rate': (completed_count / len(bookings) * 100) if bookings else 0.0
        }

    def action_send_confirmation_email(self):
        """Action to send confirmation email to customer.
        
        Note: Requires email module and SMTP configuration.
        This is a placeholder for email notification functionality.
        """
        for booking in self:
            if booking.customer_email:
                # TODO: Implement email sending
                # Can use self.env['mail.mail'].create() or template rendering
                pass
        return True

    def action_send_reminder_sms(self):
        """Action to send SMS reminder before appointment.
        
        Note: Requires SMS gateway integration.
        This is a placeholder for SMS notification functionality.
        """
        for booking in self:
            if booking.customer_phone:
                # TODO: Implement SMS sending
                # Can use third-party SMS API (Twilio, Nexmo, etc.)
                pass
        return True
