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
        """Auto-generate booking reference using sequence and dispatch confirmation email."""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('beauty.booking') or 'New'
        record = super().create(vals)
        if record.customer_email:
            try:
                record.action_send_confirmation_email()
            except Exception:
                pass
        return record

    @api.onchange('service_id')
    def _onchange_service_id(self):
        """Auto-populate professional when service is selected."""
        if self.service_id:
            self.professional_id = self.service_id.professional_id

    def action_send_confirmation_email(self):
        """Send rich HTML confirmation email to the customer and log in sandbox."""
        template = self.env.ref('beauty_booking.email_template_booking_confirmation', raise_if_not_found=False)
        for record in self:
            if not record.customer_email:
                continue

            email_from = record.professional_id.email or 'noreply@beautybooking.com'
            if template:
                try:
                    template.sudo().send_mail(record.id, force_send=False)
                except Exception:
                    pass

            # Also create a explicit mail.mail sandbox record if not created
            body_html = f"""
            <div style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8fafc; border-radius: 16px; color: #1e293b;">
                <div style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #4c1d95 100%); padding: 30px; border-radius: 12px; text-align: center; color: #ffffff;">
                    <h2 style="margin: 0; font-size: 24px; font-weight: 800;">✨ Booking Confirmed!</h2>
                    <p style="margin: 5px 0 0; opacity: 0.8; font-size: 14px;">Reference: {record.name}</p>
                </div>
                <div style="background: #ffffff; padding: 30px; border-radius: 12px; margin-top: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                    <p style="font-size: 16px; margin-top: 0;">Hello <strong>{record.customer_name}</strong>,</p>
                    <p style="color: #475569; line-height: 1.6;">Your appointment has been successfully scheduled. Here are your booking details:</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Professional:</td>
                            <td style="padding: 10px 0; font-weight: 700; text-align: right; color: #0f172a;">{record.professional_id.name}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Service:</td>
                            <td style="padding: 10px 0; font-weight: 700; text-align: right; color: #0f172a;">{record.service_id.name}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Date &amp; Time:</td>
                            <td style="padding: 10px 0; font-weight: 700; text-align: right; color: #7c3aed;">{record.appointment_date}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Duration:</td>
                            <td style="padding: 10px 0; font-weight: 700; text-align: right; color: #0f172a;">{record.duration} mins</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #64748b; font-weight: 600;">Total Price:</td>
                            <td style="padding: 10px 0; font-weight: 800; text-align: right; color: #16a34a; font-size: 18px;">${record.price:.2f}</td>
                        </tr>
                    </table>
                </div>
            </div>
            """
            self.env['mail.mail'].sudo().create({
                'subject': f'Booking Confirmed: {record.name} with {record.professional_id.name}',
                'email_from': email_from,
                'email_to': record.customer_email,
                'body_html': body_html,
                'auto_delete': False,
                'model': 'beauty.booking',
                'res_id': record.id,
            })

    def _send_customer_notification(self, subject, message):
        """Send an email notification to the customer when the booking status changes."""
        for record in self:
            if not record.customer_email:
                continue

            email_from = record.professional_id.email or 'noreply@beautybooking.com'
            body_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; background: #f8fafc; border-radius: 12px;">
                <div style="background: #1e1b4b; padding: 20px; text-align: center; color: #fff; border-radius: 8px;">
                    <h3>{subject}</h3>
                    <p>Reference: {record.name}</p>
                </div>
                <div style="background: #fff; padding: 20px; margin-top: 15px; border-radius: 8px; color: #334155;">
                    {message}
                </div>
            </div>
            """
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'email_from': email_from,
                'email_to': record.customer_email,
                'body_html': body_html,
                'auto_delete': False,
                'model': 'beauty.booking',
                'res_id': record.id,
            })
            try:
                mail.send()
            except Exception:
                pass

    def action_confirm(self):
        """Transition booking state from draft to confirmed and notify the customer."""
        for record in self:
            record.state = 'confirmed'
            record.action_send_confirmation_email()

    def action_complete(self):
        """Mark booking as completed."""
        for record in self:
            record.state = 'completed'

    def action_cancel(self):
        """Cancel the booking and notify the customer."""
        for record in self:
            record.state = 'cancelled'
            record._send_customer_notification(
                subject=f'Booking Cancelled: {record.name}',
                message=(
                    f"Hello {record.customer_name},<br/><br/>"
                    f"Your appointment with <strong>{record.professional_id.name}</strong> "
                    f"for <strong>{record.service_id.name}</strong> on {record.appointment_date} has been cancelled.<br/><br/>"
                    f"Please contact the professional if you wish to reschedule."
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