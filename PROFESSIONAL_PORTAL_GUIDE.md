# Professional Portal - User Guide

## Overview

The Professional Portal is a secure web interface where beauty professionals (barbers and hairdressers) can:
- View and manage their bookings
- Edit their professional profile
- Manage their working hours/availability
- View statistics and performance metrics
- Share their public booking link with customers

## How to Access the Professional Portal

### Prerequisites
1. You must be registered as a beauty professional in the system
2. Your account must be linked to an Odoo user account
3. You must have the "Beauty Professional" group assigned to your user

### Login Steps

1. **Visit the Portal**
   - Navigate to `http://localhost:8015/beauty/dashboard`
   - Or click the login link in the professional portal navigation menu

2. **Authenticate**
   - Use your Odoo username and password
   - The system will verify you are a registered professional

3. **Access Dashboard**
   - You'll see your professional dashboard with key metrics and quick actions

## Features

### 1. Dashboard (`/beauty/dashboard`)

The main dashboard provides an overview of your business:

**Statistics Cards:**
- **Total Bookings**: All-time booking count
- **Completed**: Number of completed appointments
- **Services**: Count of services you offer
- **Verified**: Your verification status

**Today's Bookings:**
- Shows all appointments for today
- Displays time, customer name, service, and status
- Quick access to view full details

**Quick Actions:**
- Manage Bookings - Go to your full booking list
- Working Hours - Configure your availability
- My Profile - Edit your professional profile

### 2. Manage Bookings (`/beauty/bookings`)

View and manage all your customer bookings:

**Features:**
- **Booking Card Display**: Each booking shows:
  - Booking reference (BK-00001)
  - Customer name and status
  - Service, date, time, and duration
  - Price and customer notes
  - Action buttons

**Available Actions:**
- **Confirm**: Change a Draft booking to Confirmed
- **Complete**: Mark a Confirmed booking as Completed
- **Cancel**: Cancel a booking in Draft or Confirmed state

**Booking States:**
- **Draft**: Customer submitted but not confirmed by professional
- **Confirmed**: Professional confirmed the appointment
- **Completed**: Appointment was completed
- **Cancelled**: Appointment was cancelled
- **No Show**: Customer didn't appear

### 3. Edit Profile (`/beauty/profile`)

Manage your professional information:

**Editable Fields:**
- **Email**: Contact email for customers
- **Phone**: Phone number for inquiries
- **Location**: Your shop or working location
- **Biography**: Tell customers about yourself

**Read-Only Information:**
- Name
- Professional type (Barber/Hairdresser)
- Services list
- Public booking link

**Public Booking Link:**
- Your unique URL for customer bookings
- Format: `http://localhost:8015/beauty/book/<your_username>`
- Use the "Copy" button to copy and share with customers
- Share on social media, business cards, website, etc.

### 4. Working Hours (`/beauty/availability`)

Manage when you're available for bookings:

**Availability Grid:**
- Shows each day of the week (Monday-Sunday)
- Displays working status (Working/Off)
- Shows working hours (HH:MM format)
- Indicates when customers can book

**Note:** Working hours are configured in the admin panel. Contact an administrator to update your availability schedule.

## Booking Workflow

### For Customer Bookings:
1. Customer visits your public booking link
2. Customer selects a service and available time
3. Booking is created in **Draft** state

### For Professional Management:
1. **Confirm**: Review booking details and confirm the appointment
2. **Complete**: After the appointment, mark it as completed
3. **Cancel**: If needed, cancel the appointment (notify customer separately)

## Tips & Best Practices

### Profile Optimization:
- Keep your biography updated and professional
- Include your location and contact information
- Add a professional profile picture (in admin panel)

### Booking Management:
- Check your dashboard daily for new bookings
- Confirm or decline bookings promptly
- Mark completed appointments to maintain accurate records

### Availability:
- Ensure your working hours are correctly set
- Update availability during holidays or special days
- Set realistic time slots to avoid double-booking

## Security

- Your portal login is secure and encrypted
- You can only see and manage your own bookings
- Your professional data is protected
- Passwords are stored securely

## Support

If you encounter any issues:
1. Check that you're logged in with a professional account
2. Verify your user has the "Beauty Professional" group
3. Contact the administrator for permission issues

## Troubleshooting

### "Access Denied" Error
- **Solution**: Ensure your Odoo user is linked to a beauty professional profile

### Can't See My Bookings
- **Solution**: Check that you have the "Beauty Professional" group assigned

### Forgot Password
- Go to `http://localhost:8015/web` and click "Forgot Password"
- Follow the password reset instructions

### Share Booking Link
- In your profile page, find your "Public Booking Link"
- Click the "Copy" button to copy the URL
- Share via email, social media, or print on business cards
