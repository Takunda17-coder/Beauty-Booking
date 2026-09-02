# Professional Portal - Administrator Setup Guide

## Overview

This guide helps administrators set up professionals in the Beauty Booking system so they can access the professional portal.

## Prerequisites

- Odoo 16.0 running with beauty_booking module installed
- Access to admin panel
- Users already created in the system

## Step-by-Step Setup

### Step 1: Create or Select a User

Navigate to **Settings → Users & Companies → Users**

**Option A: Create a New User**
1. Click **Create**
2. Fill in required fields:
   - **Name**: Professional's name
   - **Email**: Email for login (e.g., john.barber@example.com)
   - **Password**: Set a secure password
3. Click **Save**

**Option B: Use Existing User**
- Select an existing user from the list

### Step 2: Add Beauty Professional Group

With the user selected:

1. Scroll to **Roles** section
2. In the **Roles** field, check the box for **Beauty Professional**
   - This grants permission to view and manage bookings
3. Optionally, check **Beauty Manager** for full admin access
4. Click **Save**

**Permission Levels:**
- **Beauty Professional**: Can view/manage their own bookings and edit their profile
- **Beauty Manager**: Full admin access to all bookings, professionals, and settings

### Step 3: Create Professional Profile

Navigate to **Beauty Booking → Professionals**

1. Click **Create**
2. Fill in required fields:
   - **Name**: Professional's name (required)
   - **Professional Type**: Select "Barber" or "Hairdresser" (required)
   - **User**: Select the user created in Step 1 (required)
   - **Booking URL**: Unique username for public booking (e.g., "john_barber")

3. Scroll to **Profile** tab and add:
   - **Biography**: Professional description
   - **Profile Image**: Upload a photo

4. Add **Services** (in the Services tab):
   - Click **Add a line** to add each service
   - Specify: Service Name, Price, Duration
   - Example:
     - Haircut - $25 - 30 minutes
     - Beard Trim - $15 - 20 minutes
     - Full Service - $40 - 45 minutes

5. Set **Availability** (Working Hours):
   - Go to **Availability** tab in professional form (if using professional form)
   - Or go to **Beauty Booking → Availability** menu
   - For each day of the week, set:
     - **Is Working Day**: Toggle to enable/disable
     - **Time Start**: Start time (e.g., 09:00)
     - **Time End**: End time (e.g., 17:00)

6. Click **Save**

### Step 4: Test Professional Portal Access

1. **Log Out** from admin
2. **Navigate** to `http://localhost:8015/beauty/dashboard`
3. **Login** with the professional's username and password
4. **Verify** you see:
   - Dashboard with statistics
   - Quick action buttons
   - Navigation to profile, bookings, availability

## Setting Up Availability

### Via Professional Form:
1. Open a professional record
2. Go to **Availability** tab
3. Click **Add** to create availability entries
4. For each day:
   - Select **Day of Week** (Monday-Sunday)
   - Check **Is Working Day** (if working)
   - Set **Time Start** (e.g., 9.0 for 9:00 AM)
   - Set **Time End** (e.g., 17.0 for 5:00 PM)

### Via Availability Menu:
1. Go to **Beauty Booking → Availability**
2. Click **Create**
3. Select the **Professional**
4. Set **Day of Week**, working status, and times

**Time Format Examples:**
- 9:00 AM = 9.0
- 12:30 PM = 12.5
- 5:00 PM = 17.0
- 9:30 AM = 9.5

## Bulk Setup for Multiple Professionals

### Quick Script (Admin Only):

If you need to set up multiple professionals quickly:

1. Go to **Beauty Booking → Professionals**
2. Click **Create** multiple times with the setup template
3. For each, link to an existing or new user

### Recommended Structure:
```
Professional "John Barber"
├── User: john_barber (john@example.com)
├── Type: Barber
├── Services:
│   ├── Haircut - $25 - 30 min
│   └── Beard Trim - $15 - 20 min
└── Availability:
    ├── Mon-Fri: 9:00 AM - 5:00 PM
    ├── Sat: 10:00 AM - 2:00 PM
    └── Sun: Off
```

## Sharing Professional Portal Links

After setup, each professional has a unique public booking URL:
- **Format**: `http://localhost:8015/beauty/book/<username>`
- **Example**: `http://localhost:8015/beauty/book/john_barber`

**Share with Customers:**
- Print on business cards
- Add to website
- Share on social media
- Send via email marketing

## Verification Badge

To mark a professional as verified:
1. Open the professional record
2. Check the **Verified** checkbox
3. Click **Save**

Verified professionals display a badge in the public booking interface.

## Troubleshooting Setup

### Professional Can't Login to Portal

**Problem**: "Access Denied" error

**Solution**:
1. Verify user is linked in **User** field
2. Check user has **Beauty Professional** group
3. Confirm professional record exists
4. Try logging in to main Odoo first (`/web`)

### Professional Can't See Their Bookings

**Problem**: Empty bookings list

**Solutions**:
1. Check bookings are assigned to this professional_id
2. Verify permissions in **Settings → Security → Access Control List**
3. Try logging out and back in

### Public Booking Link Returns 404

**Problem**: "Username doesn't exist"

**Solutions**:
1. Verify **Booking URL** field is filled in
2. Ensure professional is **Active** (toggle on)
3. Use exact username from professional record
4. Check URL spelling (case-sensitive)

## Best Practices

### Security:
- Use strong passwords
- Regularly review user permissions
- Don't share professional accounts between people
- Archive inactive professionals

### Organization:
- Use consistent naming for usernames (lowercase, no spaces)
- Include location in professional name if multiple locations
- Document professional types and specialties
- Keep emergency contact info in biography

### Customer Experience:
- Set realistic working hours
- Enable availability check to prevent double-booking
- Prompt confirmation helps manage expectations
- Regular profile updates build trust

## Access Control

### Groups and Permissions:

**Beauty Professional Group:**
- Read/Write: Own professional profile
- Read/Write: Own bookings
- Read: Services
- Limitations: Cannot access admin menu, limited to portal only

**Beauty Manager Group:**
- Full CRUD on professionals, services, bookings
- Access to admin panel menus
- View all statistics and reports
- Can configure system settings

## Additional Resources

- [Professional Portal User Guide](./PROFESSIONAL_PORTAL_GUIDE.md)
- [Architecture Documentation](./ARCHITECTURE_REVIEW.md)
- Odoo Official Documentation: https://docs.odoo.com

## Support

For issues during setup:
1. Check Odoo logs in terminal
2. Verify database connection
3. Ensure beauty_booking module is installed and up-to-date
4. Run `odoo-bin -u beauty_booking` to reload module
