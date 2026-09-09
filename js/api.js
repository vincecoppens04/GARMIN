/**
 * AUGUR API & Authentication Client
 * Handles communication with Supabase and Modal.com serverless functions.
 */

import { state } from "./state.js";

export const SUPABASE_URL = "https://txtbsurmejrwtiapjmni.supabase.co";
export const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR4dGJzdXJtZWpyd3RpYXBqbW5pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgzNjM1NjYsImV4cCI6MjEwMzkzOTU2Nn0.g_4RbFZmfUPcXXdazzeHtPKvisfBwwsPf15x-gYhVU8";

export const MODAL_READ_URL = "https://vincecoppens04--augur-backend-get-telemetry.modal.run";
export const MODAL_SYNC_URL = "https://vincecoppens04--augur-backend-sync-now.modal.run";
export const MODAL_HABITS_URL = "https://vincecoppens04--augur-backend-log-habits.modal.run";
export const MODAL_TEST_NOTIF_URL = "https://vincecoppens04--augur-backend-send-test-notification.modal.run";
export const MODAL_SETTINGS_URL = "https://vincecoppens04--augur-backend-save-settings.modal.run";

export const supabaseClient = (typeof window !== "undefined" && window.supabase)
  ? window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
  : null;

export function getSupabaseClient() {
  return supabaseClient || (typeof window !== "undefined" && window.supabase ? window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY) : null);
}

export async function initAuth(onAuthSuccess, onAuthRequired) {
  if (!supabaseClient) {
    console.warn("Supabase client not loaded, opening app directly");
    onAuthSuccess({ email: "vincecoppens04" });
    return;
  }

  try {
    const { data: { session } } = await supabaseClient.auth.getSession();
    if (session && session.user) {
      state.user = session.user;
      onAuthSuccess(session.user);
    } else {
      onAuthRequired();
    }
  } catch (err) {
    console.warn("Session retrieval exception:", err);
    onAuthRequired();
  }

  supabaseClient.auth.onAuthStateChange((event, session) => {
    if (event === "SIGNED_OUT") {
      state.user = null;
      onAuthRequired();
    } else if (event === "SIGNED_IN" && session && session.user) {
      state.user = session.user;
      onAuthSuccess(session.user);
    }
  });
}

export async function loginWithPassword(email, password) {
  if (!supabaseClient) throw new Error("Supabase auth engine not initialized");
  const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
  if (error) throw error;
  state.user = data.user;
  return data.user;
}

export async function signOutUser() {
  if (supabaseClient) {
    await supabaseClient.auth.signOut();
  }
  state.user = null;
}

export async function fetchTelemetryFromCloud() {
  try {
    const res = await fetch(MODAL_READ_URL);
    if (res.ok) {
      const row = await res.json();
      if (row && (row.recovery_score != null || row.recovery != null)) {
        return row;
      }
    }
  } catch (err) {
    console.warn("Modal read error, checking Supabase:", err);
  }

  if (supabaseClient) {
    try {
      const { data } = await supabaseClient
        .from("daily_summaries")
        .select("*")
        .order("date", { ascending: false })
        .limit(90);

      if (data && data.length > 0) {
        return {
          ...data[0],
          history_records: data,
        };
      }
    } catch (err) {
      console.error("Supabase load error:", err);
    }
  }
  return null;
}

export async function triggerCloudSync() {
  const res = await fetch(MODAL_SYNC_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function saveHabitLog(habitPayload) {
  const res = await fetch(MODAL_HABITS_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(habitPayload)
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function saveSettingsToCloud(settingsPayload) {
  const res = await fetch(MODAL_SETTINGS_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settingsPayload)
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function sendTestPush() {
  const res = await fetch(MODAL_TEST_NOTIF_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
