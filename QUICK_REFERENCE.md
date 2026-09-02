# Beauty Booking Module - Quick Reference Card

## Module Overview
- **Name:** Beauty Booking v1.1.0
- **Category:** Services
- **Odoo Version:** 16.0
- **Status:** Production Ready

---

## Core Models

### 1. beauty.professional
**Fields:** name, professional_type, user_id, phone, email, location, bio, profile_image, verified, active  
**Key Methods:** `is_available_at()`, `get_available_slots()`  
**Access:** Read/Write for users, Full CRUD for managers

### 2. beauty.service
**Fields:** name, professional_id, price, duration, description, active  
**Validations:** price ≥ 0, duration > 0  
**Access:** Read/Write for users, Full CRUD for managers

### 3. beauty.booking
**Fields:** name (auto), professional_id, service_id, customer_*, appointment_date, state, price (related), duration (related)  
**States:** draft → confirmed → completed | cancelled | no_show  
**Key Methods:** `action_confirm()`, `action_complete()`, `action_cancel()`, `action_no_show()`, `action_reset()`  
**Access:** Read/Write for users, Full CRUD for managers

### 4. beauty.availability
**Fields:** professional_id, day_of_week, time_start, time_end, is_working_day  
**Validations:** 0 ≤ times ≤ 24, start < end  
**Usage:** Define working hours per day (e.g., 9.0=9AM, 14.5=2:30PM)  
**Access:** Read/Write for users, Full CRUD for managers

---

## Key Features

### Search Filters
| Filter | Use Case |
|--------|----------|
| Status: Draft | Unconfirmed bookings |
| Status: Confirmed | Bookings ready to proceed |
| Status: Completed | Finished appointments |
| Date: Today | Current day only |
| Date: This Week | Mon-Sun |
| Date: Upcoming (7d) | Next week confirmed only |

### Group By Options
- Professional → See all bookings per pro
- Service → See bookings per service
- Status → Count by state
- Date → Organize by date

### Views Available
| View | Purpose |
|------|---------|
| Tree | Quick overview, filtering |
| Form | Detailed view, workflow buttons |
| Calendar | Visual schedule |
| Pivot | Revenue/count analysis |
| Graph | Trends & distribution |

### Reporting Methods
```python
# Get bookings
BookingModel.get_today_bookings()
BookingModel.get_upcoming_bookings(days=7)
BookingModel.get_professional_bookings(prof_id, start, end)

# Get statistics
BookingModel.get_booking_statistics(start, end)
BookingModel.get_professional_statistics(prof_id, start, end)
```

---

## Common Workflow

### Creating a Booking
```
1. Beauty Booking → Bookings → Create
2. Select Professional (or Service → Professional auto-fills)
3. Fill: Customer Name, Phone, Email
4. Select: Appointment Date/Time
5. Click: Save
6. Click: Confirm button
```

### Handling Workflows
```
Draft → Confirm → Complete
  ↓
  Cancel → (Returns to available state)

From Confirmed → No Show (If customer doesn't arrive)
```

### Checking Availability
```python
prof = env['beauty.professional'].browse(prof_id)
service = env['beauty.service'].browse(service_id)

# Check specific time
is_free = prof.is_available_at(datetime_obj, service.duration)

# Get all open slots (next 7 days, 30-min slots)
slots = prof.get_available_slots(
    datetime.now(), 
    datetime.now() + timedelta(days=7),
    service.duration
)
```

---

## Time Format Reference

### Decimal Time Conversion
```
9.0   = 9:00 AM
9.5   = 9:30 AM
14.0  = 2:00 PM
14.5  = 2:30 PM
14.75 = 2:45 PM
17.0  = 5:00 PM
```

### Formula: `decimal = hours + (minutes / 60.0)`

---

## Error Messages & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "This professional already has a booking..." | Overlapping appointment | Check calendar, adjust time |
| "Booking already exists at this time" | Exact time match | Check 1-minute precision |
| "Booking reference stays 'New'" | Sequence not linked | Restart Odoo, verify install |
| "Cannot find availability" | No working hours set | Add working hours in Professional form |
| "Invalid time format" | Time outside 0-24 range | Use decimal format (e.g., 9.5) |

---

## Access Control

### User Groups
- **Beauty Professional:** Read/Write/Create (no delete)
- **Beauty Manager:** Full CRUD

### Models Protected
- beauty.professional
- beauty.service
- beauty.booking
- beauty.availability

---

## Navigation Map

```
Beauty Booking (Menu)
├── Bookings
│   ├── Tree View (List)
│   ├── Form View (Detail)
│   ├── Calendar View (Schedule)
│   ├── Pivot View (Analytics)
│   └── Graph Views (Reports)
│
├── Professionals
│   ├── List View
│   └── Detail (with Availability & Services tabs)
│
└── Services
    ├── List View
    └── Detail View
```

---

## File Structure
```
beauty_booking/
├── models/ (Data layer)
│   ├── professional.py
│   ├── service.py
│   ├── booking.py
│   ├── availability.py
│   └── reporting.py
├── views/ (UI layer)
│   ├── professional_views.xml
│   ├── service_views.xml
│   ├── booking_views.xml
│   ├── booking_search.xml
│   ├── booking_reports.xml
│   ├── availability_views.xml
│   └── menus.xml
├── security/ (Access control)
├── data/ (Fixtures)
└── Documentation files
```

---

## Booking Reference Format

**Example:** BK-00001  
- **Prefix:** BK-
- **Format:** Zero-padded 5 digits
- **Auto-generated:** On booking creation
- **Read-only:** Cannot be edited

---

## Statistics Available

### Overall Stats (Date Range)
- Total bookings
- Completed count
- Cancelled count
- No-show count
- Total revenue
- Average booking value

### Professional Stats (Date Range)
- Total bookings
- Completed count
- Cancelled count
- No-show count
- Total revenue
- Average booking value
- Completion rate (%)

---

## Keyboard Shortcuts
| Key | Action |
|-----|--------|
| Ctrl+S | Save |
| Ctrl+N | New record |
| Ctrl+H | History |
| Esc | Cancel/Close |

*(Depends on Odoo UI customization)*

---

## Important Notes

⚠️ **Overlap Detection**
- Considers service duration (not just exact time)
- Example: 1-hour service at 2:00 PM blocks 1:30-3:30 PM
- Formula: `start < other_end AND end > other_start`

⚠️ **Cascade Delete**
- Deleting professional → deletes services & bookings
- Deleting service → deletes related bookings
- Cancelled bookings are not deleted

⚠️ **Related Fields**
- Booking.price and Booking.duration sync from service
- Changes to service don't affect past bookings (stored copy)

---

## Quick Links

📖 **Full Documentation**
- Architecture: `ARCHITECTURE_REVIEW.md`
- Usage Guide: `README_USAGE_GUIDE.md`
- Development: `DEVELOPMENT_NOTES.md`
- Changes: `CHANGELOG.md`

---

## Support & Troubleshooting

### Module Won't Install
- Verify Odoo version = 16.0
- Check XML syntax validity
- Review installation logs

### Bookings Not Appearing
- Verify professional is active
- Check access control group assignment
- Verify search filters (not filtering them out)

### Availability Methods Not Working
- Ensure working hours are defined
- Verify availability records exist
- Check datetime format (ISO 8601)

---

**Module Version:** 1.1.0  
**Last Updated:** 2026-09-01  
**Status:** Production Ready  
**Support:** See documentation files

---

## One-Page Summary

| Component | Details |
|-----------|---------|
| **Purpose** | Booking platform for beauty professionals |
| **Core Models** | Professional, Service, Booking, Availability |
| **Main Features** | Scheduling, availability mgmt, analytics, conflict detection |
| **Access Control** | Role-based (User/Manager groups) |
| **Views** | Tree, Form, Calendar, Pivot, Graph |
| **Status** | ✅ Production Ready |
| **Version** | 1.1.0 for Odoo 16.0 |

---

*Print this card for quick reference while working with the module.*
