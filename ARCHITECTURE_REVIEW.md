# Beauty Booking Module - Architecture Review

## Overview
The **beauty_booking** module is an Odoo 16.0 application designed to provide a booking platform for independent barbers and hairdressers. It enables professionals to manage their profiles, services, and customer bookings with a complete lifecycle management system.

---

## Module Metadata

| Property | Value |
|----------|-------|
| **Name** | Beauty Booking |
| **Version** | 1.0.0 |
| **Category** | Services |
| **Dependencies** | base, web |
| **Installable** | Yes (application=True) |
| **License** | LGPL-3 |

---

## 1. Core Architecture Components

### 1.1 Directory Structure

```
beauty_booking/
├── __init__.py           # Module initialization (imports models)
├── __manifest__.py       # Module metadata & dependencies
├── models/               # Core data models
│   ├── __init__.py
│   ├── professional.py   # BeautyProfessional model
│   ├── service.py        # BeautyService model
│   └── booking.py        # BeautyBooking model
├── views/                # UI layouts (forms, trees, actions, menus)
│   ├── professional_views.xml
│   ├── service_views.xml
│   ├── booking_views.xml
│   └── menus.xml
├── security/             # Access control & permissions
│   ├── security.xml      # Role definitions
│   └── ir.model.access.csv  # Model-level access rules
├── data/                 # Data fixtures
│   └── sequence.xml      # ID sequence generator
├── static/               # Static assets
│   └── description/      # Module description & icon
└── web_views/            # Custom web views (currently empty)
```

---

## 2. Data Models (ORM Layer)

### 2.1 BeautyProfessional Model (`beauty.professional`)

**Purpose:** Represents a professional barber or hairdresser offering services

**Key Fields:**

| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| `name` | Char | Required | Professional's display name |
| `professional_type` | Selection | Required, default='barber' | Type: barber or hairdresser |
| `user_id` | Many2one → res.users | Required, cascade | Links to Odoo user account |
| `partner_id` | Many2one → res.partner | Related/stored | Auto-linked from user |
| `username` | Char | Required, no copy | Unique booking URL identifier |
| `bio` | Text | Optional | Professional biography |
| `phone` | Char | Optional | Contact phone number |
| `email` | Char | Optional | Contact email |
| `location` | Char | Optional | Service location/address |
| `profile_image` | Image | Optional | Avatar image |
| `active` | Boolean | default=True | Soft delete flag |
| `verified` | Boolean | default=False | Verification badge status |
| `service_ids` | One2many → beauty.service | | Services offered (reverse relation) |

**Relationships:**
- **One-to-Many:** Professional → Services (via `service_ids`)
- **One-to-Many:** Professional → Bookings (via cascade through service_id)

**Business Logic:**
- Ordered by name (`_order = 'name'`)
- Linked to Odoo users for authentication
- Profile can be marked as verified or inactive

---

### 2.2 BeautyService Model (`beauty.service`)

**Purpose:** Represents a specific service offered by a professional

**Key Fields:**

| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| `name` | Char | Required | Service name (e.g., "Haircut", "Shave") |
| `professional_id` | Many2one → beauty.professional | Required, cascade | Service owner |
| `description` | Text | Optional | Detailed service description |
| `price` | Float | Required | Service cost |
| `duration` | Integer | Required, default=30 | Appointment length in minutes |
| `active` | Boolean | default=True | Active/inactive flag |

**Validations:**

```python
@api.constrains('price')
def _check_price(self):
    # price >= 0 (not negative)

@api.constrains('duration')
def _check_duration(self):
    # duration > 0 (must be positive)
```

**Relationships:**
- **Many-to-One:** Service → Professional (master table)
- **One-to-Many:** Service → Bookings (cascade)

**Business Logic:**
- Ordered by professional and name
- Enforces positive price and duration constraints
- Cascade delete when professional is removed

---

### 2.3 BeautyBooking Model (`beauty.booking`)

**Purpose:** Records customer appointment bookings

**Key Fields:**

| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| `name` | Char | Required, readonly, default='New' | Auto-generated booking reference (e.g., "BK-00001") |
| `professional_id` | Many2one → beauty.professional | Required, cascade | Assigned professional |
| `service_id` | Many2one → beauty.service | Required, cascade | Booked service |
| `customer_name` | Char | Required | Customer's name |
| `customer_phone` | Char | Required | Customer's phone |
| `customer_email` | Char | Optional | Customer's email |
| `appointment_date` | Datetime | Required | Appointment date/time |
| `duration` | Integer | Related/stored from service | Appointment duration (minutes) |
| `price` | Float | Related/stored from service | Booking cost |
| `notes` | Text | Optional | Customer notes/special requests |
| `state` | Selection | Required, tracking=True | Workflow status |

**State Machine (Selection Values):**

```
draft          → confirmed → completed
    ↘                           ↗
      → cancelled / no_show ←─┘
```

Possible states:
- `draft` - Initial state, not yet confirmed
- `confirmed` - Appointment confirmed
- `completed` - Appointment finished
- `cancelled` - Appointment cancelled
- `no_show` - Customer did not show up

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `action_confirm()` | Transition draft → confirmed |
| `action_complete()` | Transition confirmed → completed |
| `action_cancel()` | Cancel booking from any state |
| `action_reset()` | Return to draft state |
| `action_no_show()` | Mark as no-show |

**Event Handlers:**

```python
@api.onchange('service_id')
def _onchange_service_id(self):
    # Auto-populate professional when service is selected
    # (service is linked to a specific professional)
```

**Validations:**

```python
@api.constrains('appointment_date')
def _check_appointment_date(self):
    # Prevents double-booking:
    # No two bookings for same professional at same datetime
    # Ignores cancelled bookings in check
```

**Relationships:**
- **Many-to-One:** Booking → Professional (required)
- **Many-to-One:** Booking → Service (required)

**Business Logic:**
- Ordered by appointment date (descending, newest first)
- Auto-generates booking reference via sequence
- Related fields auto-sync price/duration from service
- Enforces no-overbooking constraint
- Implements workflow state machine with tracking

---

## 3. Security & Access Control

### 3.1 User Groups (Defined in `security.xml`)

**Two-tier role hierarchy:**

```
group_beauty_user (Base Professional)
    ↑
    └─ (implied by)
    
group_beauty_manager (Manager - has all user permissions)
```

| Group | Category | Permissions | Purpose |
|-------|----------|-----------|---------|
| `group_beauty_user` | Services | Read, Write, Create | Beauty professionals |
| `group_beauty_manager` | Services | Read, Write, Create, Delete | Administrative access |

Manager role implies User role (inheritance via `implied_ids`).

### 3.2 Model-Level Access Control (ir.model.access.csv)

**Access Matrix:**

| Model | Group | Read | Write | Create | Delete |
|-------|-------|------|-------|--------|--------|
| beauty.professional | beauty_user | ✓ | ✓ | ✓ | ✗ |
| beauty.professional | beauty_manager | ✓ | ✓ | ✓ | ✓ |
| beauty.service | beauty_user | ✓ | ✓ | ✓ | ✗ |
| beauty.service | beauty_manager | ✓ | ✓ | ✓ | ✓ |
| beauty.booking | beauty_user | ✓ | ✓ | ✓ | ✗ |
| beauty.booking | beauty_manager | ✓ | ✓ | ✓ | ✓ |

**Key Security Characteristics:**
- Users cannot delete records (prevents accidental data loss)
- Managers have full CRUD permissions
- Base module security, no record-level rules defined yet
- No field-level security (all fields visible to all roles)

---

## 4. User Interface (Views & Actions)

### 4.1 Professional Views (`professional_views.xml`)

#### Tree View (List)
Displays professionals in tabular format with columns:
- Name, Professional Type, Username, Phone, Location, Verified status, Active flag

#### Form View (Detail)
- **Header:** None (no workflow buttons)
- **Ribbon:** Shows "Verified" badge when professional is verified
- **Title:** Professional name (H1)
- **Main Group:**
  - Left section: user_id, professional_type, username, verified
  - Right section: phone, email, location, active
- **Notebook (Tabs):**
  - **Profile tab:** Bio text and profile image widget
  - **Services tab:** Embedded one2many list of services

---

### 4.2 Service Views (`service_views.xml`)

#### Tree View (List)
Columns: Name, Professional (owner), Price, Duration, Active flag

#### Form View (Detail)
- **Title:** Service name
- **Main Group:**
  - Left: professional_id, price, duration
  - Right: active flag
- **Notebook:**
  - **Description tab:** Full text description of service

---

### 4.3 Booking Views (`booking_views.xml`)

#### Tree View (List)
Columns: Booking reference, Customer name, Phone, Professional, Service, Appointment date, Price, State (statusbar)

#### Form View (Detail)
- **Header:** Action buttons with conditional visibility
  - Confirm button (visible when state='draft')
  - Complete button (visible when state='confirmed')
  - Cancel button (visible unless completed/cancelled/no_show)
  - No Show button (visible when state='confirmed')
  - State statusbar (shows: draft → confirmed → completed)

- **Main Sheet:**
  - **Title:** Booking reference
  - **Customer Group:** customer_name, customer_phone, customer_email
  - **Appointment Group:** professional_id, service_id, appointment_date
  - (Additional fields likely in rest of file: duration, price, notes, state)

---

### 4.4 Menu Structure (`menus.xml`)

```
Beauty Booking (root application menu)
├── Professionals (→ Professional List/Form action)
└── Services (→ Service List/Form action)
```

**Window Actions:**
- `action_beauty_professional`: Model=beauty.professional, views=[tree, form]
- `action_beauty_service`: Model=beauty.service, views=[tree, form]
- (Note: No direct booking action visible, likely accessible through professional interface)

---

## 5. Data Fixtures & Configuration

### 5.1 ID Sequence (`data/sequence.xml`)

Generates auto-incrementing booking references:

| Property | Value |
|----------|-------|
| **Code** | beauty.booking |
| **Prefix** | "BK-" |
| **Format** | BK-00001, BK-00002, ... |
| **Padding** | 5 digits |
| **Increment** | +1 |

Used for the `name` field in BeautyBooking model via `default='New'` which is then auto-populated by Odoo's sequence engine.

---

## 6. Data Flow & Relationships

```
┌──────────────────────────┐
│   res.users (Odoo)       │
│                          │
│  - User accounts         │
│  - Authentication        │
└────────────┬─────────────┘
             │ 1:1 (via user_id)
             ↓
┌──────────────────────────────┐
│  beauty.professional         │
│                              │
│  - Name, Type (barber/...)   │
│  - Profile, Bio, Verify flag │
│  - Username (booking URL)    │
└───────────────┬──────────────┘
                │ 1:M (service_ids)
                ↓
        ┌───────────────────────────────┐
        │   beauty.service              │
        │                               │
        │  - Service name & description │
        │  - Price & Duration           │
        │  - Active flag                │
        └──────────┬────────────────────┘
                   │ 1:M (bookings)
                   ↓
        ┌────────────────────────────────────────┐
        │  beauty.booking                        │
        │                                        │
        │  - Customer details                    │
        │  - Appointment datetime                │
        │  - Workflow state (draft→confirmed→...) │
        │  - Price & Duration (from service)     │
        │  - Booking reference (auto-generated)  │
        └────────────────────────────────────────┘
```

**Data Inheritance:**
- Booking.duration and Booking.price are **Related** fields that auto-sync from Service
- Booking.professional_id is auto-populated from Service.professional_id via `@api.onchange`

---

## 7. Key Features & Business Logic

### 7.1 Workflow State Machine
- **Immutable progression:** draft → confirmed → completed
- **Cancellation path:** Can cancel from draft or confirmed states
- **No-show tracking:** Separate state to distinguish cancellations from no-shows
- **Reset capability:** Can return to draft from completed (for corrections)

### 7.2 Booking Validation
- **Double-booking prevention:** Constraint checks no two bookings exist for the same professional at the same datetime
- **Cascade delete:** Deleting a professional or service removes all related bookings
- **Required fields:** Ensures all critical data is present before confirming

### 7.3 Service Pricing & Duration
- **Stored relations:** Price and duration are stored copies from service (denormalization for performance)
- **Immutable after booking:** Service changes don't affect existing bookings

### 7.4 Professional Verification
- **Manual verification:** Admin must explicitly mark professionals as verified
- **Visibility:** Verified badge displays in UI via ribbon widget

---

## 8. Architecture Patterns

### 8.1 Adopted Patterns

1. **Hierarchical Data Model**
   - Professional > Service > Booking (3-level hierarchy)
   - Clear parent-child relationships

2. **State Machine Pattern**
   - Booking state field with constrained transitions
   - Tracking enabled for audit trail

3. **Related Fields for Denormalization**
   - Price and duration stored in Booking for performance
   - Reduces need for joins on read operations

4. **Cascade Delete**
   - Orphaned bookings/services removed with professional
   - Maintains referential integrity

5. **Event-Driven Updates**
   - `@api.onchange` handler auto-populates professional from service selection
   - Improves UX by reducing manual entry

6. **Constraint-Based Validation**
   - Database-level constraints via `@api.constrains`
   - Prevents invalid states (negative price, zero duration, double-booking)

### 8.2 Security Architecture

- **Role-Based Access Control (RBAC):** Two-tier hierarchy (User → Manager)
- **Model-level permissions:** Access granted at model granularity, not field/record
- **Implied roles:** Manager role automatically includes User permissions
- **Deletion restriction:** Users cannot delete to prevent accidental data loss

---

## 9. Current Limitations & Gaps

### 9.1 Security/Access Control
- ❌ No record-level access control (a user could view/edit any professional's bookings)
- ❌ No field-level security (all fields visible to all roles)
- ❌ Professional's own bookings not isolated from others

### 9.2 Business Logic
- ❌ No availability/calendar system (just datetime, no slot management)
- ❌ No conflict detection beyond exact datetime matches (no duration-aware overlap checking)
- ❌ No cancellation policies or penalties
- ❌ No email notifications for booking confirmations
- ❌ No customer payment tracking
- ❌ No review/rating system

### 9.3 User Interface
- ❌ Web portal not implemented (empty `web_views/` folder)
- ❌ No calendar/schedule view for professionals
- ❌ No customer-facing booking interface
- ❌ Booking menu action not defined in menus.xml
- ❌ No reporting/analytics views

### 9.4 Data & Integration
- ❌ No API endpoints for external integrations
- ❌ No SMS/Email notifications
- ❌ No payment gateway integration
- ❌ No inventory/product links (e.g., for products used in services)

---

## 10. Code Quality Assessment

### 10.1 Strengths
✓ Clean separation of concerns (models, views, security)  
✓ Proper use of Odoo conventions (_name, _description, _order)  
✓ Documented field purposes with string labels  
✓ Validations via constrains decorators  
✓ Proper cascade delete policies  
✓ Related fields for denormalization  

### 10.2 Issues

**Critical:**
1. **Duplicate method definitions** in BeautyBooking:
   ```python
   def action_confirm(self):
       self.write({'state': 'confirmed'})
   
   # ... later in same file ...
   
   def action_confirm(self):
       for record in self:
           record.state = 'confirmed'  # Duplicate!
   ```
   **Impact:** Only the last definition is active; first version is overwritten
   **Fix:** Remove duplicate methods, standardize to use `for record in self:` pattern

2. **Incomplete view file** in `professional_views.xml`:
   - File ends mid-tag in `<page string="Services">` 
   - `<field name="service_ids"></page>` tag is missing closing bracket
   **Impact:** View XML is invalid; professional form may fail to load
   **Fix:** Complete the XML properly:
   ```xml
   <field name="service_ids"/>
   ```

**Medium:**
3. **No sequence hook** in model:
   - BeautyBooking.name defaults to 'New' but no `create()` override
   - Sequence reference not linked to model `_name`
   **Impact:** Auto-increment may not work as expected
   **Fix:** Override `create()` or use `ir.sequence` via XML hook

4. **Double-booking check complexity**:
   - Uses exact datetime match, not duration-aware overlap
   - If Professional has booking at 14:00-15:00, can still book at 14:30-15:30
   **Impact:** Can create overlapping appointments
   **Fix:** Compare datetime ranges considering duration

---

## 11. Recommendations

### High Priority (Fix Required)

1. **Fix duplicate method definitions** in `booking.py`
   - Standardize to `for record in self:` pattern
   - Test state transitions after fix

2. **Fix XML syntax errors** in `professional_views.xml`
   - Complete the truncated `<page>` element
   - Validate XML structure

3. **Implement proper sequence auto-generation**
   - Add `@api.model` method `create()` to hook sequence
   - Or use XML `ir.sequence` binding

4. **Implement duration-aware overlap detection**
   - Update `_check_appointment_date()` to consider service duration
   - Calculate appointment end time: `appointment_date + duration (minutes)`

### Medium Priority (Enhancement)

5. **Record-level access control** (RLS)
   - Restrict users to viewing only their own professional profile
   - Implement domain rules on access records

6. **Customer portal** (web portal views)
   - Create public booking interface
   - Implement `website` module integration

7. **Notification system**
   - Email confirmations for new bookings
   - SMS reminders before appointments

8. **Professional availability calendar**
   - Define working hours/days per professional
   - Validate booking times against availability

### Low Priority (Nice-to-Have)

9. **Analytics/Reports**
   - Booking revenue per professional
   - Booking fill rate per service

10. **Customer rating system**
    - Allow customers to rate professionals post-booking

---

## 12. Summary

The **beauty_booking** module provides a solid foundation for a booking platform with:

- **Well-structured data model:** 3-level hierarchy (Professional → Service → Booking)
- **Complete workflow:** State machine with multiple terminal states
- **Basic security:** Role-based access at model level
- **Proper validation:** Price/duration constraints and double-booking prevention

However, it has **critical defects** (duplicate methods, XML syntax errors) that must be fixed before production use, and **significant gaps** in advanced features (calendar views, email notifications, record-level security, customer portal).

The module is suitable for **MVP/proof-of-concept** but requires the high-priority recommendations before scaling to production.

---

**Document Version:** 1.0  
**Analysis Date:** 2026-09-01  
**Odoo Version:** 16.0
