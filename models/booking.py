from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BeautyBooking(models.Model):
    _name = 'beauty.booking'
    _description = 'Beauty Booking'
    _order = 'appointment_date desc'

    name = fields.Char(
        string='Booking Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    professional_id = fields.Many2one(
        'beauty.professional',
        string='Professional',
        required=True,
        ondelete='cascade'
    )

    service_id = fields.Many2one(
        'beauty.service',
        string='Service',
        required=True,
        ondelete='cascade'
    )

    customer_name = fields.Char(
        string='Customer Name',
        required=True
    )

    customer_phone = fields.Char(
        string='Phone',
        required=True
    )

    customer_email = fields.Char(
        string='Email'
    )

    appointment_date = fields.Datetime(
        string='Appointment Date',
        required=True
    )

    duration = fields.Integer(
        string='Duration (minutes)',
        related='service_id.duration',
        store=True
    )

    price = fields.Float(
        string='Price',
        related='service_id.price',
        store=True
    )

    notes = fields.Text(
        string='Customer Notes'
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
            ('no_show', 'No Show'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True
    )

    @api.model
    def create(self, vals):
        """Auto-generate booking reference using sequence."""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('beauty.booking') or 'New'
        return super().create(vals)

    @api.onchange('service_id')
    def _onchange_service_id(self):
        """Auto-populate professional when service is selected."""
        if self.service_id:
            self.professional_id = self.service_id.professional_id

    def _send_customer_notification(self, subject, message):
        """Send a simple email notification to the customer when the booking status changes."""
        for record in self:
            if not record.customer_email:
                continue

            email_from = self.env.user.email or 'noreply@example.com'
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'email_from': email_from,
                'email_to': record.customer_email,
                'body_html': f'<p>{message}</p>',
                'auto_delete': True,
            })
            mail.send()

    def action_confirm(self):
        """Transition booking state from draft to confirmed and notify the customer."""
        for record in self:
            record.state = 'confirmed'
            record._send_customer_notification(
                subject=f'Booking confirmed: {record.name}',
                message=(
                    f"Hello {record.customer_name},<br/><br/>"
                    f"Your appointment with {record.professional_id.name} has been scheduled successfully. "
                    f"Date: {record.appointment_date.strftime('%Y-%m-%d %H:%M')}<br/>"
                    f"Service: {record.service_id.name}<br/>"
                    f"Thank you for choosing our service."
                ),
            )

    def action_complete(self):
        """Mark booking as completed."""
        for record in self:
            record.state = 'completed'

    def action_cancel(self):
        """Cancel the booking and notify the customer."""
        for record in self:
            record.state = 'cancelled'
            record._send_customer_notification(
                subject=f'Booking update: {record.name}',
                message=(
                    f"Hello {record.customer_name},<br/><br/>"
                    f"We are sorry to inform you that your appointment with {record.professional_id.name} "
                    f"for {record.service_id.name} on {record.appointment_date.strftime('%Y-%m-%d %H:%M')} has been declined or cancelled. "
                    f"Please contact the professional for another available slot."
                ),
            )

    def action_no_show(self):
        """Mark booking as no-show."""
        for record in self:
            record.state = 'no_show'

    def action_reset(self):
        """Reset booking to draft state."""
        for record in self:
            record.state = 'draft'

    @api.constrains('appointment_date', 'service_id', 'professional_id', 'state')
    def _check_appointment_date(self):
        """Prevent overlapping bookings for the same professional.
        
        Considers the service duration to detect conflicts, not just exact datetime matches.
        Ignores cancelled and no_show bookings in the check.
        """
        from datetime import timedelta
        
        for record in self:
            if not record.appointment_date or record.state in ('cancelled', 'no_show'):
                continue
                
            if not record.professional_id or not record.service_id:
                continue
            
            # Calculate appointment end time
            appointment_start = record.appointment_date
            appointment_end = appointment_start + timedelta(minutes=record.duration)
            
            # Find overlapping bookings for the same professional
            overlapping = self.search([
                ('id', '!=', record.id),
                ('professional_id', '=', record.professional_id.id),
                ('state', 'not in', ('cancelled', 'no_show')),
            ])
            
            for booking in overlapping:
                other_start = booking.appointment_date
                other_end = other_start + timedelta(minutes=booking.duration)
                
                # Check for overlap: start < other_end AND end > other_start
                if appointment_start < other_end and appointment_end > other_start:
                    raise ValidationError(
                        f"This professional already has a booking from {other_start.strftime('%Y-%m-%d %H:%M')} "
                        f"to {other_end.strftime('%Y-%m-%d %H:%M')}. "
                        f"The requested appointment from {appointment_start.strftime('%Y-%m-%d %H:%M')} "
                        f"to {appointment_end.strftime('%Y-%m-%d %H:%M')} overlaps."
                    )