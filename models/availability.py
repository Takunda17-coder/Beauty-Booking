from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class BeautyAvailability(models.Model):
    """Working hours and availability for professionals."""
    
    _name = 'beauty.availability'
    _description = 'Professional Availability'
    _order = 'professional_id, day_of_week, time_start'

    professional_id = fields.Many2one(
        'beauty.professional',
        string='Professional',
        required=True,
        ondelete='cascade'
    )

    day_of_week = fields.Selection(
        selection=[
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
            ('5', 'Saturday'),
            ('6', 'Sunday'),
        ],
        string='Day of Week',
        required=True
    )

    time_start = fields.Float(
        string='Start Time',
        required=True,
        help='Time in decimal format (e.g., 09.00 for 9:00 AM, 14.30 for 2:30 PM)'
    )

    time_end = fields.Float(
        string='End Time',
        required=True,
        help='Time in decimal format (e.g., 17.00 for 5:00 PM)'
    )

    is_working_day = fields.Boolean(
        string='Working Day',
        default=True
    )

    @api.constrains('time_start', 'time_end')
    def _check_times(self):
        for record in self:
            if record.time_start >= record.time_end:
                raise ValidationError(
                    'Start time must be earlier than end time.'
                )
            if not (0 <= record.time_start < 24 and 0 <= record.time_end <= 24):
                raise ValidationError(
                    'Times must be between 0 and 24 hours.'
                )


class BeautyProfessionalAvailability(models.Model):
    """Add availability checking methods to professionals."""
    
    _inherit = 'beauty.professional'

    availability_ids = fields.One2many(
        'beauty.availability',
        'professional_id',
        string='Working Hours'
    )

    def get_available_slots(self, date_start, date_end, service_duration):
        """Get available time slots for booking appointments.
        
        Args:
            date_start (datetime): Start date for availability search
            date_end (datetime): End date for availability search
            service_duration (int): Service duration in minutes
            
        Returns:
            list: List of available datetime slots
        """
        self.ensure_one()
        
        available_slots = []
        current_date = date_start.date()
        end_date = date_end.date()
        
        while current_date <= end_date:
            day_of_week = str(current_date.weekday())
            
            # Get working hours for this day
            availability = self.availability_ids.filtered(
                lambda a: a.day_of_week == day_of_week and a.is_working_day
            )
            
            if availability:
                for avail in availability:
                    # Convert decimal time to hours and minutes
                    start_hour = int(avail.time_start)
                    start_minute = int((avail.time_start - start_hour) * 60)
                    end_hour = int(avail.time_end)
                    end_minute = int((avail.time_end - end_hour) * 60)
                    
                    slot_start = datetime.combine(
                        current_date,
                        datetime.min.time().replace(hour=start_hour, minute=start_minute)
                    )
                    slot_end = datetime.combine(
                        current_date,
                        datetime.min.time().replace(hour=end_hour, minute=end_minute)
                    )
                    
                    # Generate slots within the available time
                    current_slot = slot_start
                    while current_slot + timedelta(minutes=service_duration) <= slot_end:
                        # Check if slot is not already booked
                        BookingModel = self.env['beauty.booking']
                        overlapping = BookingModel.search([
                            ('professional_id', '=', self.id),
                            ('state', 'not in', ('cancelled', 'no_show')),
                            ('appointment_date', '<', current_slot + timedelta(minutes=service_duration)),
                            ('appointment_date', '>=', current_slot - timedelta(minutes=service_duration)),
                        ])
                        
                        if not overlapping:
                            available_slots.append(current_slot)
                        
                        current_slot += timedelta(minutes=30)  # Default 30-min slot interval
            
            current_date += timedelta(days=1)
        
        return available_slots

    def is_available_at(self, appointment_datetime, service_duration):
        """Check if professional is available at a specific datetime.
        
        Args:
            appointment_datetime (datetime): Proposed appointment time
            service_duration (int): Service duration in minutes
            
        Returns:
            bool: True if available, False otherwise
        """
        self.ensure_one()
        
        day_of_week = str(appointment_datetime.weekday())
        availability = self.availability_ids.filtered(
            lambda a: a.day_of_week == day_of_week and a.is_working_day
        )
        
        if not availability:
            return False
        
        appointment_hour = appointment_datetime.hour + appointment_datetime.minute / 60.0
        appointment_end = appointment_hour + (service_duration / 60.0)
        
        for avail in availability:
            if avail.time_start <= appointment_hour and appointment_end <= avail.time_end:
                # Check for booking conflicts
                BookingModel = self.env['beauty.booking']
                appointment_end_dt = appointment_datetime + timedelta(minutes=service_duration)
                
                conflicting = BookingModel.search([
                    ('professional_id', '=', self.id),
                    ('state', 'not in', ('cancelled', 'no_show')),
                    ('appointment_date', '<', appointment_end_dt),
                    ('appointment_date', '>=', appointment_datetime - timedelta(minutes=service_duration)),
                ])
                
                return not conflicting
        
        return False
