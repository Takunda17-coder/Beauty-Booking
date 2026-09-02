# Beauty Booking Module - User & Developer Guide

## Quick Start

### Installation
1. Place the `beauty_booking` folder in your Odoo addons directory
2. Install the module via Odoo Apps menu
3. Grant users the "Beauty Professional" or "Beauty Manager" group

### Initial Setup
1. Navigate to Beauty Booking → Professionals
2. Create a professional profile (linked to an Odoo user)
3. Add working hours (Availability tab)
4. Define services (Services tab)
5. Customers can now book appointments

---

## Core Features

### 1. Professionals Module

**What:** Manage barber/hairdresser profiles

**Key Fields:**
- Name
- Professional Type (Barber/Hairdresser)
- Linked Odoo User
- Bio & Contact Info
- Profile Image
- Verified Badge
- Active/Inactive Status

**Availability Tab:**
- Define working hours per day of week
- Support multiple time slots per day (e.g., 9 AM-1 PM and 3 PM-7 PM)
- Toggle working days on/off

**Services Tab:**
- Create multiple services per professional
- Each service has: Name, Price, Duration, Description

---

### 2. Services Module

**What:** Define specific services (Haircut, Shave, Massage, etc.)

**Key Fields:**
- Service Name
- Professional (Owner)
- Price
- Duration (minutes)
- Description
- Active/Inactive

**Usage:**
- Select service when booking to auto-populate professional
- Price and duration automatically copy to booking
- Services can be disabled without deleting

---

### 3. Bookings Module (Most Important)

**What:** Manage customer appointments

**Views Available:**
1. **Tree (List) View** - Tabular listing of all bookings
2. **Form View** - Detailed booking with workflow buttons
3. **Calendar View** - Visual calendar by appointment date
4. **Pivot Table** - Analytics by professional and status
5. **Graph Views** - Revenue trends and status distribution

**Booking Workflow:**
```
[Draft] → [Confirm] → [Complete]
   ↓                      ↑
   └─────[Cancel]────────┘
   
Alternative: [No Show] (from Confirmed state)
```

**Workflow Actions:**
- **Confirm:** Move from Draft to Confirmed (visible when Draft)
- **Complete:** Mark appointment finished (visible when Confirmed)
- **Cancel:** Cancel booking (visible from Draft/Confirmed)
- **No Show:** Customer didn't arrive (visible when Confirmed)
- **Reset:** Return to Draft for corrections

---

## Key Features & Validations

### 1. Automatic Booking Reference
- Auto-generated on creation: "BK-00001", "BK-00002", etc.
- Based on sequence defined in `data/sequence.xml`
- Read-only, cannot be changed

### 2. Professional Auto-Population
- When selecting a service, professional is auto-filled
- Services are linked to specific professionals
- Prevents mismatching service with professional

### 3. Duration-Aware Overlap Detection
**Problem:** Prevents booking conflicts considering service duration

**Example:**
- Professional has 1-hour appointment from 2:00 PM - 3:00 PM
- Cannot book 2:30 PM - 3:30 PM (overlaps by 30 minutes)
- Can book 3:00 PM - 4:00 PM (no overlap)
- Can book 1:00 PM - 2:00 PM (no overlap)

**Algorithm:** `start < other_end AND end > other_start`

### 4. Availability-Based Booking
**Future Enhancement:** System can check working hours

Methods available (in code):
```python
professional.is_available_at(datetime, duration)
professional.get_available_slots(start_date, end_date, duration)
```

---

## Search Filters & Grouping

### Status Filters
- Draft - Unconfirmed bookings
- Confirmed - Ready to proceed
- Completed - Finished appointments
- Cancelled - Customer cancelled
- No Show - Didn't attend

### Date Range Filters
- Today - Current day only
- This Week - Mon-Sun
- Upcoming (7 days) - Upcoming confirmed bookings

### Group By Options
- Professional - See all bookings per professional
- Service - See bookings per service type
- Status - Count by workflow state
- Date - Organize by appointment date

---

## Analytics & Reports

### 1. Pivot Table Analysis
- Bookings by Professional (rows) × Status (columns)
- Revenue metrics: Count and Sum of prices
- Drill-down capability for detailed investigation

### 2. Revenue Chart
- Bar chart: Total revenue per professional
- Identifies top-performing professionals
- Track income trends

### 3. Booking Distribution
- Pie chart: Booking count by status
- Shows completion rates visually
- Identify bottlenecks (too many drafts, high cancellations)

### 4. Programmatic Statistics
Available methods in code:
```python
# Get bookings for today
BookingModel.get_today_bookings()

# Get upcoming appointments (7 days)
BookingModel.get_upcoming_bookings(days=7)

# Get professional's bookings
BookingModel.get_professional_bookings(prof_id, start, end)

# Overall statistics
BookingModel.get_booking_statistics(start_date, end_date)

# Professional-specific statistics
BookingModel.get_professional_statistics(prof_id, start, end)
```

Returns:
- Total bookings
- Completed count
- Cancelled/No-show counts
- Total revenue
- Average booking value
- Completion rate percentage

---

## Access Control

### User Roles

**Beauty Professional (User Group)**
- Read/Write/Create own records
- Cannot Delete
- View others' bookings (no field-level restrictions yet)

**Beauty Manager**
- Full CRUD on all records (Create, Read, Update, Delete)
- Admin-level access

### Models Protected:
- beauty.professional
- beauty.service
- beauty.booking
- beauty.availability

---

## Developer Information

### Model Structure

```
beauty.professional
├── One-to-Many: service_ids → beauty.service
├── One-to-Many: availability_ids → beauty.availability
└── Foreign Key: user_id → res.users

beauty.service
├── Many-to-One: professional_id → beauty.professional
└── One-to-Many: bookings (reverse relation)

beauty.booking
├── Many-to-One: professional_id → beauty.professional
├── Many-to-One: service_id → beauty.service
├── Related fields: duration, price (from service)
└── State: draft → confirmed → completed

beauty.availability
├── Many-to-One: professional_id → beauty.professional
└── Fields: day_of_week, time_start, time_end, is_working_day
```

### Key Methods

**On beauty.professional:**
```python
def get_available_slots(date_start, date_end, service_duration)
def is_available_at(appointment_datetime, service_duration)
```

**On beauty.booking:**
```python
def action_confirm()
def action_complete()
def action_cancel()
def action_no_show()
def action_reset()
def action_send_confirmation_email()
def action_send_reminder_sms()

# Statistics (class methods)
@api.model
def get_today_bookings()
def get_upcoming_bookings(days=7)
def get_professional_bookings(prof_id, start, end)
def get_booking_statistics(start, end)
def get_professional_statistics(prof_id, start, end)
```

### Creating Bookings via Code

```python
Booking = self.env['beauty.booking']
booking = Booking.create({
    'professional_id': prof_id,
    'service_id': service_id,
    'customer_name': 'John Doe',
    'customer_phone': '+1234567890',
    'customer_email': 'john@example.com',
    'appointment_date': '2024-09-15 14:00:00',
    'notes': 'Any special requests?',
})
# Name auto-generated as BK-00001, BK-00002, etc.

# Confirm the booking
booking.action_confirm()
```

### Checking Availability

```python
Professional = self.env['beauty.professional']
prof = Professional.browse(prof_id)
service = self.env['beauty.service'].browse(service_id)

# Check if available at specific time
is_available = prof.is_available_at(
    appointment_datetime=datetime.now(),
    service_duration=service.duration
)

# Get all available slots for date range
slots = prof.get_available_slots(
    date_start=datetime.now(),
    date_end=datetime.now() + timedelta(days=7),
    service_duration=30  # minutes
)
```

---

## Configuration

### Sequence Format
Edit `data/sequence.xml` to customize booking reference:

```xml
<field name="prefix">BK-</field>    <!-- Change to custom prefix -->
<field name="padding">5</field>      <!-- Number of digits -->
```

### Time Format (Availability)
Times are stored as floats:
- 9.0 = 9:00 AM
- 9.5 = 9:30 AM
- 14.0 = 2:00 PM
- 17.75 = 5:45 PM

Convert: `decimal_time = hours + (minutes / 60.0)`

---

## Troubleshooting

### Problem: "Booking already exists at this time"
**Cause:** Overlapping appointment detected
**Solution:** 
- Check calendar view for conflicting bookings
- Check if cancelled bookings are being excluded (they should be)
- Verify service duration is set correctly

### Problem: "This professional already has a booking"
**Cause:** Exact time match for two bookings
**Solution:** Check the time - even 1 minute overlap will conflict

### Problem: Booking reference stays "New"
**Cause:** Sequence not properly linked
**Solution:** 
- Verify `data/sequence.xml` is loaded
- Check module installation logs
- Restart Odoo

### Problem: Availability slots not showing
**Cause:** No availability records created
**Solution:**
- Go to Professional form → Availability tab
- Add working hours for each day
- Set is_working_day = True

---

## Common Use Cases

### Use Case 1: Book an Appointment
1. Go to Beauty Booking → Bookings
2. Click Create
3. Select Professional (or select Service first, then Professional auto-populates)
4. Fill Customer Name, Phone, Email
5. Select Appointment Date/Time
6. Click Save
7. Click Confirm button to confirm

### Use Case 2: View Weekly Schedule
1. Go to Beauty Booking → Bookings
2. Switch to Calendar view
3. Filter by Professional (if needed)
4. Scroll through week/month

### Use Case 3: Generate Revenue Report
1. Go to Beauty Booking → Bookings
2. Switch to Pivot or Graph view
3. Use Group By options to slice data
4. Analyze revenue trends

### Use Case 4: Mark Appointment Completed
1. Open booking in form view
2. Verify state = "Confirmed"
3. Click "Complete" button
4. System marks as "Completed"

### Use Case 5: Handle No-Show
1. Open booking (should be Confirmed)
2. Click "No Show" button
3. System tracks as missed appointment

---

## Best Practices

### For Professionals
1. **Keep availability updated** - Add/remove hours when scheduling changes
2. **Set accurate service durations** - Prevents double-booking issues
3. **Confirm bookings promptly** - Keep customers informed
4. **Use notes field** - Document special requests (allergies, preferences)

### For Managers
1. **Regular backup** - Export booking data weekly
2. **Monitor no-show rate** - High rate indicates issues
3. **Review analytics monthly** - Identify trends and top services
4. **Verify availability** - Ensure working hours are accurate

### For Developers
1. **Extend booking.create()** - Don't override, use super()
2. **Use constraints** - Data validation at database level
3. **Add domain restrictions** - For record-level security
4. **Use related fields** - For denormalization, not raw SQL

---

## Future Enhancements

- [ ] Email notifications on booking confirmation
- [ ] SMS reminders before appointment
- [ ] Customer portal for self-service booking
- [ ] Payment processing integration
- [ ] Customer review/rating system
- [ ] Package/membership support
- [ ] Discount/promotion codes
- [ ] Multi-language support
- [ ] Mobile app

---

## Support & Documentation

- **Architecture Review:** See `ARCHITECTURE_REVIEW.md`
- **Development Notes:** See `DEVELOPMENT_NOTES.md`
- **Code Documentation:** Docstrings in model files
- **Module Manifest:** `__manifest__.py`

---

**Last Updated:** 2026-09-01  
**Odoo Version:** 16.0  
**Module Version:** 1.1.0
