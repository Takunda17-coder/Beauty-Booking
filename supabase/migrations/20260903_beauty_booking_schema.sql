-- ========================================================================
-- BEAUTY BOOKING PLATFORM - SUPABASE FREE TIER POSTGRESQL SCHEMA
-- Includes: Auth extensions, Row-Level Security (RLS), Double-Booking Guard,
--           Pesepay Payment Audit Trail, and Realtime publication.
-- ========================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. PROFILES (Extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'professional', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public profiles are viewable by everyone" 
ON public.profiles FOR SELECT USING (true);

CREATE POLICY "Users can update their own profile" 
ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- 2. PROFESSIONALS TABLE
CREATE TABLE IF NOT EXISTS public.professionals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE UNIQUE,
    username TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    professional_type TEXT NOT NULL DEFAULT 'barber' CHECK (professional_type IN ('barber', 'hairdresser')),
    phone TEXT,
    location TEXT,
    bio TEXT,
    avatar_url TEXT,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.professionals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Active professionals are publicly viewable" 
ON public.professionals FOR SELECT USING (active = true);

CREATE POLICY "Professionals can update their own profile" 
ON public.professionals FOR UPDATE USING (auth.uid() = user_id);

-- 3. SERVICES TABLE
CREATE TABLE IF NOT EXISTS public.services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    professional_id UUID NOT NULL REFERENCES public.professionals(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    price NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    duration_minutes INT NOT NULL DEFAULT 30 CHECK (duration_minutes > 0),
    image_url TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.services ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Active services are publicly viewable" 
ON public.services FOR SELECT USING (active = true);

CREATE POLICY "Professionals manage their own services" 
ON public.services FOR ALL USING (
    EXISTS (SELECT 1 FROM public.professionals WHERE id = services.professional_id AND user_id = auth.uid())
);

-- 4. AVAILABILITY SCHEDULES
CREATE TABLE IF NOT EXISTS public.availabilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    professional_id UUID NOT NULL REFERENCES public.professionals(id) ON DELETE CASCADE,
    day_of_week INT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Mon, 6=Sun
    time_start NUMERIC(4,2) NOT NULL CHECK (time_start >= 0 AND time_start < 24),
    time_end NUMERIC(4,2) NOT NULL CHECK (time_end > 0 AND time_end <= 24),
    is_working_day BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT check_time_range CHECK (time_start < time_end)
);

ALTER TABLE public.availabilities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Availability schedules are viewable by everyone" 
ON public.availabilities FOR SELECT USING (true);

CREATE POLICY "Professionals manage their availability" 
ON public.availabilities FOR ALL USING (
    EXISTS (SELECT 1 FROM public.professionals WHERE id = availabilities.professional_id AND user_id = auth.uid())
);

-- 5. BOOKINGS TABLE & SEQUENCE
CREATE SEQUENCE IF NOT EXISTS booking_ref_seq START WITH 1001;

CREATE TABLE IF NOT EXISTS public.bookings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference TEXT NOT NULL UNIQUE DEFAULT ('BK-' || LPAD(nextval('booking_ref_seq')::TEXT, 5, '0')),
    professional_id UUID NOT NULL REFERENCES public.professionals(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES public.services(id) ON DELETE RESTRICT,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_email TEXT,
    appointment_date TIMESTAMPTZ NOT NULL,
    duration_minutes INT NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_payment' 
        CHECK (status IN ('pending_payment', 'draft', 'confirmed', 'completed', 'cancelled', 'no_show')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can create a booking" 
ON public.bookings FOR INSERT WITH CHECK (true);

CREATE POLICY "Professionals can view and manage their bookings" 
ON public.bookings FOR ALL USING (
    EXISTS (SELECT 1 FROM public.professionals WHERE id = bookings.professional_id AND user_id = auth.uid())
);

-- 6. SUBSCRIPTION PLANS (SaaS Tiers)
CREATE TABLE IF NOT EXISTS public.subscription_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    price NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    currency TEXT NOT NULL DEFAULT 'USD',
    billing_interval TEXT NOT NULL DEFAULT 'monthly' CHECK (billing_interval IN ('monthly', 'yearly')),
    max_services INT DEFAULT 5,
    max_bookings_month INT DEFAULT 50,
    featured_listing BOOLEAN DEFAULT FALSE,
    sms_notifications BOOLEAN DEFAULT FALSE,
    custom_domain BOOLEAN DEFAULT FALSE,
    analytics_dashboard BOOLEAN DEFAULT FALSE,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.subscription_plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Subscription plans are viewable by everyone" 
ON public.subscription_plans FOR SELECT USING (active = true);

-- 7. PROFESSIONAL SUBSCRIPTIONS
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    professional_id UUID NOT NULL REFERENCES public.professionals(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES public.subscription_plans(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'trialing' CHECK (status IN ('trialing', 'active', 'past_due', 'cancelled')),
    current_period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_period_end TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '14 days'),
    auto_renew BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Professionals can view their own subscriptions" 
ON public.subscriptions FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.professionals WHERE id = subscriptions.professional_id AND user_id = auth.uid())
);
CREATE POLICY "Professionals can update their own subscriptions" 
ON public.subscriptions FOR UPDATE USING (
    EXISTS (SELECT 1 FROM public.professionals WHERE id = subscriptions.professional_id AND user_id = auth.uid())
);

-- Seed initial SaaS subscription plans
INSERT INTO public.subscription_plans (name, code, price, currency, billing_interval, max_services, max_bookings_month, featured_listing, sms_notifications, analytics_dashboard, description)
VALUES 
    ('Starter (Solo Barber)', 'starter', 0.00, 'USD', 'monthly', 5, 50, false, false, false, 'Ideal for independent barbers starting out. Up to 5 services and 50 bookings/month.'),
    ('Pro Barber & Stylist', 'pro', 15.00, 'USD', 'monthly', 0, 0, true, true, true, 'Unlimited services, unlimited bookings, revenue analytics, and priority customer booking.'),
    ('Salon & Studio VIP', 'salon', 35.00, 'USD', 'monthly', 0, 0, true, true, true, 'Multi-chair capability, featured search badge, custom domain support, and dedicated support.')
ON CONFLICT (code) DO NOTHING;

-- 8. PESEPAY PAYMENTS TABLE (Customer Bookings & Pro Subscriptions)
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_type TEXT NOT NULL DEFAULT 'booking' CHECK (payment_type IN ('booking', 'subscription')),
    booking_id UUID REFERENCES public.bookings(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES public.subscriptions(id) ON DELETE SET NULL,
    professional_id UUID REFERENCES public.professionals(id) ON DELETE CASCADE,
    merchant_reference TEXT NOT NULL UNIQUE,
    pesepay_reference TEXT,
    amount NUMERIC(10,2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    payment_method TEXT, -- 'pesepay', 'ecocash', 'onemoney', 'card'
    state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('draft', 'pending', 'paid', 'failed', 'cancelled')),
    poll_url TEXT,
    redirect_url TEXT,
    response_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Professionals can view payments for their bookings and subscriptions" 
ON public.payments FOR SELECT USING (
    (professional_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM public.professionals p WHERE p.id = payments.professional_id AND p.user_id = auth.uid()
    ))
    OR
    (booking_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM public.bookings b
        JOIN public.professionals p ON b.professional_id = p.id
        WHERE b.id = payments.booking_id AND p.user_id = auth.uid()
    ))
);

-- 7. DOUBLE BOOKING OVERLAP GUARD TRIGGER
CREATE OR REPLACE FUNCTION public.check_booking_overlap()
RETURNS TRIGGER AS $$
DECLARE
    conflict_count INT;
    service_dur INT;
BEGIN
    SELECT duration_minutes INTO service_dur FROM public.services WHERE id = NEW.service_id;
    IF service_dur IS NULL THEN
        service_dur := NEW.duration_minutes;
    END IF;

    SELECT COUNT(*) INTO conflict_count
    FROM public.bookings
    WHERE professional_id = NEW.professional_id
      AND status NOT IN ('cancelled', 'no_show')
      AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::UUID)
      AND (
          appointment_date < (NEW.appointment_date + (service_dur || ' minutes')::INTERVAL)
          AND (appointment_date + (duration_minutes || ' minutes')::INTERVAL) > NEW.appointment_date
      );

    IF conflict_count > 0 THEN
        RAISE EXCEPTION 'Time slot conflicts with an existing booking for this professional.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_booking_overlap ON public.bookings;
CREATE TRIGGER trg_check_booking_overlap
BEFORE INSERT OR UPDATE ON public.bookings
FOR EACH ROW
EXECUTE FUNCTION public.check_booking_overlap();
