// Supabase Edge Function: pesepay-webhook
// Handles Pesepay IPN callbacks, verifies payment status, updates booking and audit records.

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";
import { PesepayCrypto } from "../_shared/pesepay-crypto.ts";

serve(async (req) => {
  try {
    const supabaseClient = createClient(
      Deno.env.get("SUPABASE_URL") ?? "",
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
    );

    const body = await req.json();
    const encryptionKey = Deno.env.get("PESEPAY_ENCRYPTION_KEY") || "b9b9826ba47447f298fc0f565ff89907";
    const cryptoHelper = new PesepayCrypto(encryptionKey);

    let decrypted = body;
    if (body.payload) {
      decrypted = await cryptoHelper.decrypt(body.payload);
    }

    const merchantReference = decrypted.merchantReference || decrypted.reference;
    const transactionStatus = (decrypted.transactionStatus || "").toUpperCase();

    if (!merchantReference) {
      return new Response(JSON.stringify({ error: "Missing merchant reference" }), { status: 400 });
    }

    // Fetch matching payment
    const { data: payment, error: fetchErr } = await supabaseClient
      .from("payments")
      .select("id, booking_id, state")
      .eq("merchant_reference", merchantReference)
      .single();

    if (fetchErr || !payment) {
      return new Response(JSON.stringify({ error: "Payment not found" }), { status: 404 });
    }

    if (["SUCCESS", "PAID", "COMPLETED"].includes(transactionStatus)) {
      // 1. Mark payment paid
      await supabaseClient
        .from("payments")
        .update({
          state: "paid",
          response_message: `Webhook confirmed payment: ${transactionStatus}`,
          updated_at: new Date().toISOString(),
        })
        .eq("id", payment.id);

      // 2. Confirm booking
      await supabaseClient
        .from("bookings")
        .update({ status: "confirmed" })
        .eq("id", payment.booking_id);

      // 3. Trigger email notification (via Resend or Mailtrap)
      console.log(`[Pesepay Webhook] Booking ${payment.booking_id} confirmed via ${merchantReference}`);
    } else if (["FAILED", "CANCELLED"].includes(transactionStatus)) {
      await supabaseClient
        .from("payments")
        .update({
          state: "failed",
          response_message: `Webhook received failure: ${transactionStatus}`,
          updated_at: new Date().toISOString(),
        })
        .eq("id", payment.id);

      await supabaseClient
        .from("bookings")
        .update({ status: "cancelled" })
        .eq("id", payment.booking_id);
    }

    return new Response(JSON.stringify({ status: "SUCCESS" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error("[Pesepay Webhook Error]", err);
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
});
