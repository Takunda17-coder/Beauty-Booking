// Supabase Edge Function: pesepay-initiate
// Initiates a Pesepay payment transaction and creates an initial pending booking & payment record.

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";
import { PesepayCrypto } from "../_shared/pesepay-crypto.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get("SUPABASE_URL") ?? "",
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
    );

    const {
      service_id,
      professional_id,
      customer_name,
      customer_phone,
      customer_email,
      appointment_date,
      notes,
    } = await req.json();

    // 1. Fetch service details
    const { data: service, error: serviceErr } = await supabaseClient
      .from("services")
      .select("id, name, price, duration_minutes")
      .eq("id", service_id)
      .single();

    if (serviceErr || !service) {
      return new Response(
        JSON.stringify({ error: "Invalid service selected" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // 2. Create pending booking record
    const { data: booking, error: bookingErr } = await supabaseClient
      .from("bookings")
      .insert({
        professional_id,
        service_id: service.id,
        customer_name,
        customer_phone,
        customer_email,
        appointment_date,
        duration_minutes: service.duration_minutes,
        price: service.price,
        status: "pending_payment",
        notes,
      })
      .select()
      .single();

    if (bookingErr) {
      return new Response(
        JSON.stringify({ error: bookingErr.message }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // 3. Initiate payment with Pesepay
    const merchantReference = `PAY-${booking.reference}-${Date.now()}`;
    const frontendUrl = Deno.env.get("APP_FRONTEND_URL") || "http://localhost:3000";
    const resultUrl = `${frontendUrl}/booking/result?ref=${merchantReference}`;

    const integrationKey = Deno.env.get("PESEPAY_INTEGRATION_KEY") || "";
    const encryptionKey = Deno.env.get("PESEPAY_ENCRYPTION_KEY") || "";
    const pesepayBaseUrl = Deno.env.get("PESEPAY_BASE_URL") || "https://api.pesepay.com";

    const cryptoHelper = new PesepayCrypto(encryptionKey);
    const paymentPayload = {
      amountDetails: {
        amount: Number(service.price),
        currencyCode: "USD",
      },
      merchantReference,
      reasonForPayment: `Appointment for ${service.name}`,
      resultUrl,
      returnUrl: resultUrl,
      customer: {
        name: customer_name,
        phone: customer_phone,
        email: customer_email || "",
      },
    };

    const encryptedPayload = await cryptoHelper.encrypt(paymentPayload);

    const pesepayResp = await fetch(
      `${pesepayBaseUrl}/api/payments-engine/v2/payments/make-payment`,
      {
        method: "POST",
        headers: {
          "Authorization": integrationKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ payload: encryptedPayload }),
      }
    );

    let redirectUrl = `${resultUrl}&simulated=1`;
    let pollUrl = "";
    let pesepayReference = `PSP-${merchantReference}`;

    if (pesepayResp.ok) {
      const respJson = await pesepayResp.json();
      const decrypted = respJson.payload ? await cryptoHelper.decrypt(respJson.payload) : respJson;
      redirectUrl = decrypted.redirectUrl || redirectUrl;
      pollUrl = decrypted.pollUrl || "";
      pesepayReference = decrypted.referenceNumber || pesepayReference;
    }

    // 4. Save payment record
    await supabaseClient.from("payments").insert({
      booking_id: booking.id,
      merchant_reference: merchantReference,
      pesepay_reference: pesepayReference,
      amount: service.price,
      currency: "USD",
      state: "pending",
      redirect_url: redirectUrl,
      poll_url: pollUrl,
    });

    return new Response(
      JSON.stringify({
        success: true,
        redirect_url: redirectUrl,
        merchant_reference: merchantReference,
        booking,
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    return new Response(
      JSON.stringify({ error: err.message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
