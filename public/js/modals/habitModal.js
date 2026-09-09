/**
 * Habit Logging Modal Controller
 * Handles recording daily behavioral interventions (alcohol, late dinner,
 * screens in bed, caffeine, travel) to calibrate overnight recovery correlation matrix.
 */

import { state, getCurrentRecord } from '../state.js';
import { saveHabitLog as saveHabitLogToCloud } from '../api.js';

export function checkHabitBannerStatus(dateStr) {
  const banner = document.getElementById("habit-logging-banner");
  if (!banner) return;
  const loggedDates = JSON.parse(localStorage.getItem("augur_logged_habits") || "[]");
  if (loggedDates.includes(dateStr)) {
    banner.style.display = "none";
  } else {
    banner.style.display = "flex";
  }
}

export function openHabitModal() {
  const modal = document.getElementById("habit-modal");
  if (!modal) return;
  modal.classList.remove("hidden");

  const dateSub = document.getElementById("habit-modal-date");
  const btn = document.getElementById("btn-save-habits");

  const curr = getCurrentRecord();
  const targetDate = (curr && curr.date) || new Date().toISOString().split('T')[0];
  const todayObj = new Date(targetDate + 'T12:00:00');
  const yesterdayObj = new Date(todayObj);
  yesterdayObj.setDate(yesterdayObj.getDate() - 1);

  const yStr = yesterdayObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  const tStr = todayObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

  if (dateSub) {
    dateSub.innerHTML = `Behaviors from <strong class="text-augur-cyan font-mono">${yStr}</strong> (affects <strong class="text-augur-green font-mono">${tStr}</strong> score)`;
  }
  if (btn) {
    btn.innerText = `Save Habits for ${yStr}`;
  }
}

export function closeHabitModal() {
  const modal = document.getElementById("habit-modal");
  if (modal) modal.classList.add("hidden");
}

export async function saveHabitLog() {
  const btn = document.getElementById("btn-save-habits");
  if (btn) {
    btn.innerText = "Saving to Engine...";
    btn.disabled = true;
  }

  const curr = getCurrentRecord();
  const targetDate = (curr && curr.date) || new Date().toISOString().split('T')[0];

  const payload = {
    date: targetDate,
    alcohol: document.getElementById("habit-alcohol") ? document.getElementById("habit-alcohol").checked : false,
    party: document.getElementById("habit-party") ? document.getElementById("habit-party").checked : false,
    late_meal: document.getElementById("habit-late-meal") ? document.getElementById("habit-late-meal").checked : false,
    late_caffeine: document.getElementById("habit-late-caffeine") ? document.getElementById("habit-late-caffeine").checked : false,
    any_caffeine: document.getElementById("habit-any-caffeine") ? document.getElementById("habit-any-caffeine").checked : false,
    screen_in_bed: document.getElementById("habit-screen") ? document.getElementById("habit-screen").checked : false,
    travel_day: document.getElementById("habit-travel") ? document.getElementById("habit-travel").checked : false,
  };

  // 1. Immediately record in local storage so banner vanishes instantly
  const loggedDates = JSON.parse(localStorage.getItem("augur_logged_habits") || "[]");
  if (!loggedDates.includes(payload.date)) {
    loggedDates.push(payload.date);
    localStorage.setItem("augur_logged_habits", JSON.stringify(loggedDates));
  }

  closeHabitModal();
  checkHabitBannerStatus(payload.date);

  // 2. Dispatch to cloud backend
  try {
    await saveHabitLogToCloud(payload);
  } catch (err) {
    console.warn("Cloud habit sync warning:", err);
  } finally {
    if (btn) {
      btn.innerText = "Save Yesterday's Habits";
      btn.disabled = false;
    }
  }
}
