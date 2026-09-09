/**
 * Sports Science & Autonomic Explanation Knowledge Matrix
 */

export const FEATURE_EXPLANATIONS = {
  recovery_score: {
    category: "Autonomic Recovery",
    title: "Morning Recovery Score (0–100%)",
    what_it_is: "A dynamically weighted composite score evaluating overnight parasympathetic reactivation. AUGUR benchmarks your overnight HRV (rMSSD, 50% weight), Resting Heart Rate (30% weight), and sleep debt satisfaction (20% weight) against your rolling 30-day statistical envelope (μ ± 1.5σ).",
    what_is_good: [
      { label: "Green (≥67%)", desc: "Primed. High vagal tone and parasympathetic dominance. Cardiovascular system can absorb heavy strain.", color: "green" },
      { label: "Yellow (34–66%)", desc: "Equilibrium. Normal physiological adaptability. Optimal for aerobic base maintenance.", color: "yellow" },
      { label: "Red (<34%)", desc: "Compromised. Autonomic stress, CNS fatigue, or immune challenge. Suspend heavy load.", color: "red" }
    ],
    directive: "Align training volume to your score: load up on Green days, maintain on Yellow, and prioritize restorative sleep and hydration on Red days."
  },
  hrv: {
    category: "Autonomic Nervous System",
    title: "HRV — Heart Rate Variability (rMSSD)",
    what_it_is: "Root Mean Square of Successive Differences (rMSSD) between consecutive heartbeats during sleep. Directly reflects vagal nerve stimulation and parasympathetic control. Higher variability indicates resilient, adaptable recovery.",
    what_is_good: [
      { label: "Within / Above Baseline (μ ± 1.5σ)", desc: "Optimal parasympathetic modulation.", color: "green" },
      { label: "Mild Suppression (0.5σ to 1.5σ below μ)", desc: "Acute muscular or cardiovascular fatigue from recent strain.", color: "yellow" },
      { label: "Severe Suppression (>1.5σ below μ)", desc: "Systemic inflammation, illness onset, alcohol, or chronic overtraining.", color: "red" }
    ],
    directive: "Compare against your personal baseline envelope, not other athletes. HRV is highly individual."
  },
  rhr: {
    category: "Cardiovascular Baselines",
    title: "Resting Heart Rate (RHR)",
    what_it_is: "The lowest sustained heart rate captured during deep, undisturbed rest. Reflects stroke volume and basic myocardial workload.",
    what_is_good: [
      { label: "At or Below Baseline (μ ± 1.5σ)", desc: "Strong cardiac stroke volume and rested vascular tone.", color: "green" },
      { label: "2–4 bpm Above Baseline", desc: "Delayed autonomic deceleration from late meals, heat, or mild stress.", color: "yellow" },
      { label: "≥5 bpm Above Baseline", desc: "Clear indicator of immune challenge, fever, dehydration, or alcohol intoxication.", color: "red" }
    ],
    directive: "Elevated RHR coinciding with suppressed HRV is the gold-standard alert for systemic physiological stress."
  },
  resp_rate: {
    category: "Respiratory Physiology",
    title: "Overnight Respiration Rate",
    what_it_is: "Breaths taken per minute during sleep. Respiration rate is extraordinarily stable night-to-night (typically variance < 1 breath/min).",
    what_is_good: [
      { label: "Within Baseline (μ ± 1.0 brpm)", desc: "Normal pulmonary airway resistance and metabolic gas exchange.", color: "green" },
      { label: "Elevated (>1.5 brpm above baseline)", desc: "One of the earliest pre-symptomatic flags for respiratory infection, allergy, or fever.", color: "red" }
    ],
    directive: "If respiration jumps while HRV drops, suspend hard training immediately to let your immune system fight off impending illness."
  },
  spo2: {
    category: "Pulmonary & Blood Oxygen",
    title: "Pulse Oximetry (SpO2)",
    what_it_is: "Estimated percentage of oxygen-saturated hemoglobin circulating through peripheral capillaries during sleep.",
    what_is_good: [
      { label: "95% – 100%", desc: "Optimal arterial oxygenation and airway patency.", color: "green" },
      { label: "90% – 94%", desc: "Mild hypoxemia, altitude exposure, or nasal airway restriction.", color: "yellow" },
      { label: "<90%", desc: "Significant desaturation. May indicate sleep apnea, high altitude, or severe congestion.", color: "red" }
    ],
    directive: "SpO2 dips during sleep can fragment deep REM stages and trigger daytime brain fog."
  },
  workout_prescriber: {
    category: "Exercise Physiology",
    title: "Daily Workout Prescriber",
    what_it_is: "Translates your daily autonomic recovery into a concrete training stimulus directive, preventing under-training on peak days and overtraining on depleted days.",
    what_is_good: [
      { label: "Green Zone", desc: "High CNS capacity: High-intensity intervals (HIIT), max strength, tempo runs, VO2 max.", color: "green" },
      { label: "Yellow Zone", desc: "Aerobic maintenance: Zone 2 base building (<LT1), steady cycling, tempo lifting.", color: "yellow" },
      { label: "Red Zone", desc: "Restorative flow: Zone 1 active recovery, mobility, gentle walking, light stretching.", color: "red" }
    ],
    directive: "Match your workout intensity to your autonomic readiness rather than rigid calendar programming."
  },
  immune_strain: {
    category: "Clinical Diagnostics",
    title: "Immune Strain Severity Index (0–100)",
    what_it_is: "A weighted multi-signal Z-score algorithm combining respiration elevation (35%), RHR spike (30%), HRV suppression (25%), and SpO2 drop (10%) to detect pre-symptomatic viral infection or systemic inflammation.",
    what_is_good: [
      { label: "Normal (0–25)", desc: "Autonomic and respiratory vitals resting stably in baseline envelope.", color: "green" },
      { label: "Watch (26–55)", desc: "Mild autonomic deviation. Monitor symptoms, hydrate, and avoid maximal efforts.", color: "yellow" },
      { label: "High Infection Risk (56–100)", desc: "Multiple vital anomalies detected. Strong pre-symptomatic signature. Suspend training.", color: "red" }
    ],
    directive: "Early detection allows you to rest 24 hours earlier, often reducing illness duration by half."
  },
  day_strain: {
    category: "Cardiovascular Load",
    title: "Day Strain (0–21.0 Scale)",
    what_it_is: "Cumulative cardiovascular workload computed continuously using Banister's TRIMP equation across 15-minute heart rate buckets. Scaled logarithmically from 0 to 21.0, accounting for sex-specific cardiac reserve thresholds.",
    what_is_good: [
      { label: "Rest / Light (<10.0)", desc: "Promotes parasympathetic recovery; minimal cardiac strain.", color: "cyan" },
      { label: "Maintenance (10.0 – 14.0)", desc: "Maintains aerobic fitness without accumulating excessive chronic debt.", color: "green" },
      { label: "Overload (14.0 – 18.0)", desc: "Stimulates cardiovascular remodeling, mitochondrial density, and VO2 max.", color: "yellow" },
      { label: "All-Out (>18.0)", desc: "Extreme exertion (race, marathon, ultra). Requires 24–48h deliberate recovery.", color: "red" }
    ],
    directive: "Stay within your prescribed daily target strain window to optimize progressive overload without risking burnout."
  },
  sleep_score: {
    category: "Sleep Architecture",
    title: "Sleep Performance Score",
    what_it_is: "Percentage of tonight's physiological sleep need actually achieved, incorporating duration, sleep debt satisfaction, and sleep efficiency.",
    what_is_good: [
      { label: "Optimal (≥85%)", desc: "Full sleep need satisfied. Adenosine fully cleared from brain tissue.", color: "green" },
      { label: "Adequate (70–84%)", desc: "Mild deficit. Manageable for 1–2 days without severe cognitive degradation.", color: "yellow" },
      { label: "Insufficient (<70%)", desc: "Accumulates acute sleep debt, blunts growth hormone release, and impairs reaction time.", color: "red" }
    ],
    directive: "Target 85%+ sleep satisfaction on the nights preceding high-strain training days."
  },
  sleep_debt: {
    category: "Sleep Ledger",
    title: "Smart Sleep Debt Ledger",
    what_it_is: "A cumulative ledger tracking sleep deficits below your baseline need (with a 30m biological tolerance deadband). Carried-over debt decays daily and is repaid incrementally (+33% per night) so bedtime targets remain realistic.",
    what_is_good: [
      { label: "Balanced (0 – 15m)", desc: "Zero accumulated sleep debt; wake feeling completely refreshed.", color: "green" },
      { label: "Moderate Debt (16 – 45m)", desc: "Manageable deficit; requires 15–30 min earlier bedtime tonight.", color: "yellow" },
      { label: "High Debt (>45m)", desc: "Severe sleep deficit. Suppresses immune function, blunts VO2 max, and spikes cortisol.", color: "red" }
    ],
    directive: "Repay sleep debt with earlier bedtimes rather than late morning wakeups to protect circadian alignment."
  },
  nocturnal_dip: {
    category: "Autonomic Sleep Profile",
    title: "Nocturnal Dipping & Curve Shape",
    what_it_is: "The percentage drop in heart rate during sleep compared to daytime resting levels, and the trajectory curve (Hammock, Slope, or Plateau) across the night.",
    what_is_good: [
      { label: "Normal Dipper (10–20% Dip)", desc: "Healthy cardiovascular decompression and parasympathetic dominance.", color: "green" },
      { label: "Hammock Curve Shape", desc: "Heart rate reaches its nadir around mid-sleep and rises smoothly toward wake. Ideal.", color: "green" },
      { label: "Slope Curve Shape", desc: "Heart rate elevated early in sleep due to late eating, alcohol, or evening workouts.", color: "yellow" },
      { label: "Non-Dipper (<10% Dip) / Plateau", desc: "Continuous sympathetic overdrive, sleep apnea, or severe systemic stress.", color: "red" }
    ],
    directive: "Finish meals at least 3 hours before lights out to achieve a healthy Hammock dipping curve."
  },
  hrv_slope: {
    category: "Autonomic Trajectory",
    title: "Overnight HRV Trend Slope",
    what_it_is: "Ordinary least squares (OLS) linear regression across 5-minute overnight HRV readings, measuring whether nervous system recovery deepened or degraded across the night.",
    what_is_good: [
      { label: "Ascending / Regenerative (+Slope)", desc: "Vagal tone progressively strengthened toward morning. Prime readiness.", color: "green" },
      { label: "Flat (-0.05 to +0.05)", desc: "Steady equilibrium sustained throughout sleep stages.", color: "cyan" },
      { label: "Descending / Depleting (-Slope)", desc: "Autonomic recovery deteriorated toward morning; body struggled with homeostasis.", color: "red" }
    ],
    directive: "An ascending slope confirms your nervous system successfully neutralized yesterday's stress."
  },
  sleep_restoration: {
    category: "Sleep Architecture",
    title: "Sleep Restoration & Restlessness",
    what_it_is: "The ratio of Deep (slow-wave) + REM sleep to total sleep duration, alongside movement events and wakefulness per hour.",
    what_is_good: [
      { label: "Restoration 40% – 55%", desc: "Optimal balance between physical cellular repair (Deep) and cognitive consolidation (REM).", color: "green" },
      { label: "Restlessness < 1.5 events/hr", desc: "Calm, uninterrupted sleep with minimal micro-arousals.", color: "green" },
      { label: "Restlessness > 3.0 events/hr", desc: "Fragmented sleep often caused by elevated bedroom temperature, noise, or alcohol.", color: "red" }
    ],
    directive: "Keep your bedroom cool (17–19°C) and completely dark to maximize deep restorative sleep."
  },
  social_jetlag: {
    category: "Circadian Rhythm",
    title: "Social Jetlag (Midpoint Shift)",
    what_it_is: "The absolute difference in sleep midpoint (halfway between falling asleep and waking up) between workdays and free/weekend days (Wittmann & Roenneberg chronobiology model). Quantifies circadian phase disruption caused by social schedules.",
    what_is_good: [
      { label: "Synchronized (≤30 min)", desc: "Circadian clock stays aligned throughout the week. Peak energy, metabolism, and mood.", color: "green" },
      { label: "Moderate Shift (31 – 60 min)", desc: "Mild circadian drag; may cause Monday morning brain fog.", color: "yellow" },
      { label: "Circadian Jetlag (>60 min)", desc: "Equivalent to traveling across multiple time zones every weekend. Disrupts metabolic hormones.", color: "red" }
    ],
    directive: "Keep weekend wake-up times within 45–60 minutes of your weekday routine to eliminate Monday fatigue."
  },
  circadian_windows: {
    category: "Chronobiology",
    title: "Circadian Performance Windows",
    what_it_is: "Personalized biological windows anchored to your wake time, pinpointing when cortisol, prefrontal alertness, core body temperature, and melatonin peak during the 24-hour cycle.",
    what_is_good: [
      { label: "Sunlight Window (+0 to 45m)", desc: "Direct natural light anchors the central circadian pacemaker in the SCN.", color: "cyan" },
      { label: "Deep Work Window (+2 to 4.5h)", desc: "Prefrontal cortex alertness peak for demanding cognitive tasks.", color: "green" },
      { label: "Strength & VO2 Peak (+9 to 11.5h)", desc: "Highest core temperature, neuromuscular speed, and pain tolerance.", color: "yellow" },
      { label: "Caffeine Cutoff (~10h before bed)", desc: "Prevents residual caffeine from blocking adenosine receptors.", color: "red" }
    ],
    directive: "Schedule your hardest workout during your physical window (late afternoon) for maximum strength and endurance output."
  },
  chronic_strain_debt: {
    category: "Overtraining Prevention",
    title: "Chronic Strain Debt Runway",
    what_it_is: "Tracks cumulative strain accumulated above your prescribed target ceilings over the trailing 7 days. Measures how close you are to overreaching or functional overtraining.",
    what_is_good: [
      { label: "Optimal Runway (0.0 – 3.0)", desc: "Strain closely matches capacity. Adaptations are absorbing well.", color: "green" },
      { label: "Accumulating (3.1 – 6.0)", desc: "Cardiovascular load is outpacing recovery. High fatigue developing.", color: "yellow" },
      { label: "Deload Required (>6.0 with 4+ overreach days)", desc: "Mandatory active recovery/rest day needed to avoid non-functional overtraining.", color: "red" }
    ],
    directive: "When chronic debt exceeds 5.0, insert a dedicated Zone 1 active recovery or rest day."
  },
  hrr: {
    category: "Autonomic Reactivation",
    title: "Heart Rate Recovery (HRR 60s / 120s)",
    what_it_is: "How many beats per minute your heart rate drops in the first 60 and 120 seconds immediately following cessation of hard exercise. Gold standard marker of vagal reactivation.",
    what_is_good: [
      { label: "Optimal (≥25 bpm drop in 60s)", desc: "High vagal tone, excellent cardiovascular fitness, and fast autonomic recovery.", color: "green" },
      { label: "Moderate (15–24 bpm drop)", desc: "Normal parasympathetic reactivation.", color: "yellow" },
      { label: "Suppressed (<15 bpm drop)", desc: "Delayed vagal rebound due to severe CNS exhaustion, dehydration, or heat stress.", color: "red" }
    ],
    directive: "Record your HRR after hard workouts. An improving HRR is one of the clearest signs of increased aerobic fitness."
  },
  glycogen_refuel: {
    category: "Metabolic Nutrition",
    title: "Glycogen Depletion & Refueling Target",
    what_it_is: "Estimates carbohydrate and glycogen oxidation based on duration spent in high-intensity zones (Zone 3–5) where glycolysis dominates over fat oxidation.",
    what_is_good: [
      { label: "Target: 1.0–1.2g Carbs / kg", desc: "Replenishes liver and muscle glycogen within the 2–4 hour post-workout window.", color: "green" },
      { label: "Endurance & Speed", desc: "Prevents catabolic cortisol spikes and protects next-day training capacity.", color: "cyan" }
    ],
    directive: "Consume fast-digesting carbohydrates with 20–30g of protein within 60 minutes after high-glycolytic sessions."
  },
  stress_recovery_index: {
    category: "Stress Resistance",
    title: "Stress Resistance / Recovery Time",
    what_it_is: "The number of minutes elapsed after a workout until your Garmin stress score falls below 25 (indicating return to parasympathetic equilibrium).",
    what_is_good: [
      { label: "Fast Recovery (≤30 min)", desc: "Rapid systemic clearance of epinephrine and cortisol; resilient autonomic response.", color: "green" },
      { label: "Moderate (30 – 60 min)", desc: "Standard post-workout autonomic recovery.", color: "yellow" },
      { label: "Prolonged (>90 min)", desc: "Sustained post-workout sympathetic drive, often exacerbated by dehydration or lack of post-workout nutrition.", color: "red" }
    ],
    directive: "Perform 5 minutes of slow diaphragmatic box breathing post-workout to accelerate parasympathetic reactivation."
  },
  habit_correlations: {
    category: "Lifestyle Intelligence",
    title: "Habit Correlation Engine",
    what_it_is: "Calculates the exact statistical difference in next-day recovery score, HRV (rMSSD), and RHR between days when a specific habit was logged vs days when it was absent (over the trailing 30–60 days).",
    what_is_good: [
      { label: "Positive / Neutral Habits", desc: "No significant penalty on nocturnal recovery or sleep architecture.", color: "green" },
      { label: "Detrimental Habits (ΔHRV < -8ms)", desc: "Clearly degrades autonomic tone. Identifying your personal triggers empowers smart lifestyle adjustments.", color: "yellow" }
    ],
    directive: "Log habits consistently in the morning habit prompt to uncover your personal recovery multipliers and drainers."
  },
  alcohol_latency: {
    category: "Toxicology & Autonomic Delay",
    title: "Alcohol Sympathetic Delay Latency",
    what_it_is: "Measures the delay (in hours) before your heart rate settles down to your baseline sleeping heart rate (+2 bpm). Alcohol metabolization keeps sympathetic tone fired up, inhibiting deep sleep.",
    what_is_good: [
      { label: "Clean Baseline (0.0h Penalty)", desc: "Sober recovery. Heart rate stabilizes within normal physiological latency (~1.0–1.5h).", color: "green" },
      { label: "Mild Delay (+1.0 to 2.0h)", desc: "1–2 drinks with dinner. Minor suppression of REM sleep.", color: "yellow" },
      { label: "Heavy Delay (+3.0h+)", desc: "Significant alcohol consumption. Vagal outflow blocked, resting HR elevated all night.", color: "red" }
    ],
    directive: "Finish your last drink 3–4 hours before sleep and drink electrolyte water to mitigate sympathetic elevation."
  },
  caffeine_clearance: {
    category: "Pharmacokinetics",
    title: "Caffeine Depletion Curve (t½ = 5.0h)",
    what_it_is: "Simulates the exponential decay of caffeine in your bloodstream based on the average 5-hour metabolic half-life. Evaluates residual milligrams at your target bedtime.",
    what_is_good: [
      { label: "Clear (≤25 mg at Bedtime)", desc: "Adenosine receptors remain unblocked, facilitating deep slow-wave stage 3/4 sleep.", color: "green" },
      { label: "Sleep Disruption (>25 mg at Bedtime)", desc: "Residual caffeine competitively antagonizes adenosine receptors, reducing deep sleep and increasing micro-awakenings.", color: "red" }
    ],
    directive: "Set a hard caffeine cutoff at least 9–10 hours before your scheduled lights-out time."
  },
  strain_recovery_balance: {
    category: "Training Adaptation",
    title: "Strain vs Recovery Balance (4 Quadrants)",
    what_it_is: "Plots your 7-day rolling average cardiovascular strain against your 7-day rolling average recovery score in a 4-quadrant adaptation matrix.",
    what_is_good: [
      { label: "Optimal Overload (Top-Right)", desc: "High Strain + High Recovery: Sweet spot for athletic breakthrough and rapid adaptation.", color: "green" },
      { label: "Restoring & Primed (Top-Left)", desc: "Low Strain + High Recovery: Tapering or rebuilding adaptive energy.", color: "cyan" },
      { label: "Overreaching (Bottom-Right)", desc: "High Strain + Low Recovery: Accumulating fatigue; injury risk elevated if sustained.", color: "red" },
      { label: "Detraining / Stressed (Bottom-Left)", desc: "Low Strain + Low Recovery: High non-exercise systemic stress or inactivity.", color: "yellow" }
    ],
    directive: "Oscillate purposefully between Optimal Overload and Restoring phases. Avoid spending more than 4 consecutive days in Overreaching."
  },
  cardiovascular_age: {
    category: "Biological Longevity",
    title: "Cardiovascular Fitness Age",
    what_it_is: "Based on the validated Jackson et al. / HUNT study regression algorithm: estimates biological heart age by combining precise VO2 Max (aerobic capacity) with baseline resting heart rate.",
    what_is_good: [
      { label: "Younger than Calendar Age", desc: "High VO2 max and strong stroke volume reflect athletic cardiovascular remodeling.", color: "green" },
      { label: "18.0 Biological Floor", desc: "Optimal peak biological youthfulness bound.", color: "cyan" },
      { label: "Older than Calendar Age", desc: "Cardiovascular deconditioning. Aerobic interval training and Zone 2 volume will lower fitness age rapidly.", color: "yellow" }
    ],
    directive: "Two Zone 2 cardio sessions plus one interval session per week will systematically drop your cardiovascular fitness age."
  },
  sport_strain_penalties: {
    category: "Biomechanics & Recovery",
    title: "Readiness Cost per Sport Type",
    what_it_is: "Calculates the average next-day recovery score penalty per unit of cardiovascular strain for different exercise modalities (running, cycling, swimming, strength).",
    what_is_good: [
      { label: "Cycling (~0.9% / strain)", desc: "Non-impact concentric exercise: permits high cardiovascular volume with rapid recovery.", color: "green" },
      { label: "Swimming (~0.7% / strain)", desc: "Zero-impact, supportive buoyancy: lowest autonomic muscle trauma.", color: "cyan" },
      { label: "Strength (~1.4% / strain)", desc: "High central nervous system and neuromuscular motor unit fatigue.", color: "yellow" },
      { label: "Running (~1.8% / strain)", desc: "High eccentric impact: causes micro-trauma and delayed inflammatory repair.", color: "red" }
    ],
    directive: "When recovery is yellow or red, substitute running sessions with cycling or swimming to build volume without heavy eccentric penalties."
  },
  sleep_thermal: {
    category: "Environmental Physiology",
    title: "Sleep Thermal Environment",
    what_it_is: "Tracks ambient bedroom temperature and relative humidity against sleep efficiency and deep slow-wave duration. Grounded in sleep medicine research.",
    what_is_good: [
      { label: "Optimal Temp: 17.0 – 19.5 °C", desc: "Allows natural nocturnal core body temperature drop of ~1°C required for deep sleep.", color: "green" },
      { label: "Optimal Humidity: 45 – 55%", desc: "Prevents airway dryness and nighttime awakenings from thirst.", color: "green" },
      { label: "Warm Room (>20.5 °C)", desc: "Sleep efficiency drops by ~3.2% per 1.5°C increase. Causes restlessness and night sweats.", color: "red" }
    ],
    directive: "Keep your bedroom cool and use breathable bedding to facilitate natural nocturnal core cooling."
  },
  acwr: {
    category: "Workload Dynamics",
    title: "Acute:Chronic Workload Ratio (ACWR)",
    what_it_is: "Compares your acute 7-day fatigue load to your chronic 28-day fitness load (Gabbett model). The gold standard metric in professional sports for injury prevention.",
    what_is_good: [
      { label: "Under-training (<0.80)", desc: "Fitness loss; reduced cardiovascular conditioning.", color: "cyan" },
      { label: "The Sweet Spot (0.80 – 1.30)", desc: "Optimal progressive overload with minimal soft-tissue injury risk. Peak adaptation zone.", color: "green" },
      { label: "Overload Window (1.31 – 1.50)", desc: "Controlled overreaching; monitor recovery closely.", color: "yellow" },
      { label: "Danger Zone (>1.50)", desc: "Injury risk spikes 2x to 4x. Deload recommended immediately.", color: "red" }
    ],
    directive: "Keep your acute load increases below 10–15% week-over-week to stay firmly in the 0.8–1.3 sweet spot."
  },
  training_monotony: {
    category: "Periodization Load",
    title: "Training Monotony & Strain Index (Foster)",
    what_it_is: "Carl Foster's model: Monotony = Mean Strain / Standard Deviation of Strain. Strain Index = Mean × Monotony × 7. Measures whether your training incorporates healthy day-to-day variance or repetitive stagnation.",
    what_is_good: [
      { label: "Balanced Monotony (≤1.5)", desc: "Healthy polarization between hard days and light/rest days. Maximizes adaptation.", color: "green" },
      { label: "High Monotony (>2.0 with Mean >11)", desc: "Repetitive moderate strain without hard or easy days leads to overtraining, illness, and performance plateaus.", color: "red" }
    ],
    directive: "Make your hard days truly hard, and your easy days truly easy. Never train at the same moderate intensity every day."
  },
  load_polarization: {
    category: "Endurance Periodization",
    title: "Cardiovascular 80/20 Polarization",
    what_it_is: "Stephen Seiler's 3-zone polarized training model: checks whether ~80% of training time is in Zone 1–2 (low intensity), <10% in Zone 3 (moderate/threshold), and ~10% in Zone 4–5 (high intensity).",
    what_is_good: [
      { label: "Polarized (≥75% Z1-2, ≤12% Z3)", desc: "Optimal endurance adaptation. Builds vast mitochondrial capillary bed without excessive autonomic stress.", color: "green" },
      { label: "Threshold Black Hole (Z3 > 15%)", desc: "Too much time spent in Zone 3: causes high fatigue without the mitochondrial benefits of Zone 2 or the anaerobic benefits of Zone 5.", color: "red" }
    ],
    directive: "Keep your easy runs and rides slow enough to hold a conversation, saving all-out efforts for interval days."
  },
  daytime_stress: {
    category: "Autonomic Balance",
    title: "Daytime Stress-to-Rest Balance Ratio",
    what_it_is: "The ratio of minutes spent in parasympathetic rest (Garmin stress < 25) to minutes spent in high sympathetic stress (Garmin stress ≥ 50) during waking hours.",
    what_is_good: [
      { label: "Optimal (Ratio ≥ 1.5)", desc: "Rest minutes exceed high-stress minutes by 50%+. High autonomic reserves.", color: "green" },
      { label: "Moderate (1.0 – 1.4)", desc: "Equal balance between sympathetic activation and recovery breaks.", color: "yellow" },
      { label: "Sympathetic Dominance (<1.0)", desc: "High chronic daytime stress drains autonomic tone before bedtime, impairing sleep.", color: "red" }
    ],
    directive: "Take brief 3–5 minute walking or breathing breaks during the workday to keep your stress-to-rest ratio above 1.5."
  }
};

export function showExplanation(key) {
  const item = FEATURE_EXPLANATIONS[key];
  if (!item) return;

  const modal = document.getElementById("explanation-modal");
  const catEl = document.getElementById("exp-category");
  const titleEl = document.getElementById("exp-title");
  const whatEl = document.getElementById("exp-what-it-is");
  const dirEl = document.getElementById("exp-directive");
  const benchContainer = document.getElementById("exp-benchmarks");

  if (catEl) catEl.innerText = item.category || "SPORTS SCIENCE";
  if (titleEl) titleEl.innerText = item.title || "Feature Overview";
  if (whatEl) whatEl.innerText = item.what_it_is || "";
  if (dirEl) dirEl.innerText = item.directive || "";

  if (benchContainer && item.what_is_good) {
    benchContainer.innerHTML = item.what_is_good.map(b => {
      let colorClass = "bg-augur-green/10 text-augur-green border-augur-green/30";
      if (b.color === "yellow") colorClass = "bg-amber-500/10 text-amber-400 border-amber-500/30";
      if (b.color === "red") colorClass = "bg-rose-500/10 text-rose-400 border-rose-500/30";
      if (b.color === "cyan") colorClass = "bg-cyan-500/10 text-cyan-400 border-cyan-500/30";
      return `
        <div class="p-2.5 rounded-2xl bg-augur-cardInner border border-augur-border space-y-1">
          <span class="px-2 py-0.5 rounded-full text-[9px] font-black uppercase border ${colorClass} inline-block font-mono">
            ${b.label}
          </span>
          <p class="text-[10px] text-zinc-300 font-sans leading-snug">${b.desc}</p>
        </div>
      `;
    }).join('');
  }

  if (modal) modal.classList.remove("hidden");
}

export function closeExplanationModal() {
  const modal = document.getElementById("explanation-modal");
  if (modal) modal.classList.add("hidden");
}
export const closeExplanation = closeExplanationModal;

