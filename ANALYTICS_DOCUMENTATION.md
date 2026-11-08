# LifeOS — Analytics & Behavioral Intelligence Documentation

> **Status:** Step 10 Implemented & Verified  
> **Application:** `apps.analytics`  
> **Engine Stack:** Python 3.13, Django ORM, MySQL, Pandas, NumPy, Plotly  

---

## 1. Overview & Architecture

LifeOS implements **Personal Behavioral Intelligence — A Debugger for Humans**. Its analytical pipeline transforms historical telemetry across productivity, academics, habits, routines, well-being, and finances into actionable self-awareness observations.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        HTTP / Browser Request                          │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Analytics Views Layer                           │
│  - analytics_dashboard_view        - habit_analytics_view              │
│  - productivity_analytics_view     - wellbeing_analytics_view          │
│  - study_analytics_view            - behavioral_insights_view          │
│  - time_analytics_view             - comparison_view                   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Analytics Services Layer                           │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────┐  │
│  │ date_utils.py        │  │ productivity_service │  │ study_service│  │
│  ├──────────────────────┤  ├──────────────────────┤  ├──────────────┤  │
│  │ habit_service.py     │  │ time_service.py      │  │ wellbeing_...│  │
│  ├──────────────────────┤  ├──────────────────────┤  ├──────────────┤  │
│  │ finance_service.py   │  │ comparison_service   │  │ insights_... │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────┘  │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │                                 │
                   ▼                                 ▼
┌─────────────────────────────────────┐  ┌───────────────────────────────┐
│         Plotly Charts Layer         │  │       Django ORM / MySQL      │
│  (Minimal Modern Dark + Soft Indigo)│  │ (Strict user-isolated queries)│
└─────────────────────────────────────┘  └───────────────────────────────┘
```

---

## 2. Major Metrics & Mathematical Formulas

### A. Productivity Metrics
1. **Task Completion Rate**:
   $$\text{Completion Rate} = \left(\frac{\text{Completed Tasks}}{\text{Total Tasks Active or Due in Period}}\right) \times 100$$
2. **Tasks Completed Per Day**:
   $$\text{Velocity} = \frac{\text{Completed Tasks}}{\text{Days Count in Period}}$$
3. **Average Task Completion Time**:
   $$\text{Avg Duration} = \frac{\sum \text{actual\_minutes}}{\text{Count of Completed Tasks with actual\_minutes} > 0}$$
   *Rule: Tasks without recorded actual minutes are strictly excluded from duration averaging.*
4. **Estimation Error**:
   $$\text{Estimation Error} = \text{Actual Duration} - \text{Estimated Duration}$$
   - **Positive ($> 0$):** Task was **underestimated** (took longer than planned).
   - **Negative ($< 0$):** Task was **overestimated** (completed faster than planned).
   - **Zero ($= 0$):** Estimate was mathematically exact.
5. **Estimation Accuracy**:
   $$\text{Accuracy} = \max\left(0, 100 - \left(\frac{|\text{Actual} - \text{Estimated}|}{\text{Estimated}} \times 100\right)\right)$$
6. **Total Productive Tracked Time**:
   $$\text{Productive Time} = \sum \text{Activity.duration\_minutes} + \sum \text{Task.actual\_minutes}$$

---

### B. Study & Academic Metrics
1. **Total Study Duration**:
   $$\text{Total Hours} = \frac{\sum \text{StudySession.duration\_minutes}}{60.0}$$
2. **Study Consistency Rate**:
   $$\text{Consistency} = \left(\frac{\text{Distinct Days with Recorded Study Sessions}}{\text{Total Days in Period}}\right) \times 100$$
3. **Syllabus Topic Completion Rate**:
   $$\text{Syllabus Mastery} = \left(\frac{\text{Completed Topics}}{\text{Total Curriculum Topics}}\right) \times 100$$
4. **Study Planning Variance**:
   $$\text{Variance} = \text{Actual Study Hours} - \text{Planned Study Hours}$$
5. **Study Plan Adherence**:
   $$\text{Plan Adherence} = \left(\frac{\text{Completed Plans}}{\text{Total Scheduled Plans}}\right) \times 100$$

---

### C. Frequency-Aware Habit Metrics
LifeOS evaluates habits against their declared frequency cadences:
1. **Daily Habits**:
   $$\text{Expected Completions} = \text{Days in Period}$$
   $$\text{Completion Rate} = \left(\frac{\text{Completed HabitLogs}}{\text{Days in Period}}\right) \times 100$$
2. **Weekly Habits** (e.g. 3x/week):
   $$\text{Expected Completions} = \max\left(1, \text{round}\left(\frac{\text{Days in Period}}{7} \times \text{target\_count}\right)\right)$$
   $$\text{Completion Rate} = \left(\frac{\text{Completed HabitLogs}}{\text{Expected Completions}}\right) \times 100$$
   *Non-Penalizing Rule: A 3x/week habit is never evaluated against a 7-day expectation.*
3. **Habit Streak Fidelity**:
   Direct daily contiguous streaks are reported strictly for `DAILY` habits. Custom/weekly habits are evaluated against multi-week completion blocks.

---

### D. Time Management Metrics
1. **Category Time Distribution**:
   Sums activity minutes, study session minutes, and completed task durations mapped to parent categories without double-counting.
2. **Schedule Block Adherence**:
   $$\text{Adherence Rate} = \left(\frac{\text{Completed ScheduleBlocks}}{\text{Total Scheduled Blocks in Period}}\right) \times 100$$

---

### E. Personal Well-being & Statistical Correlations
1. **Average Biometric Scores**:
   $$\bar{M} = \frac{\sum \text{mood\_score}}{N}, \quad \bar{E} = \frac{\sum \text{energy\_score}}{N}, \quad \bar{S} = \frac{\sum \text{stress\_score}}{N}, \quad \bar{H} = \frac{\sum \text{sleep\_hours}}{N}$$
2. **Pearson Correlation Coefficient ($r$)**:
   $$r_{xy} = \frac{\sum_{i=1}^{n} (x_i - \bar{x})(y_i - \bar{y})}{\sqrt{\sum_{i=1}^{n}(x_i - \bar{x})^2} \sqrt{\sum_{i=1}^{n}(y_i - \bar{y})^2}}$$
3. **Minimum Observation Threshold**:
   - Strict requirement: **$N \ge 14$ paired observations** are required before any exploratory correlation is displayed.
   - For $N < 14$, the UI renders an informative progress bar indicating the number of logs required.
4. **Non-Causal Interpretation Table**:
   - $r \ge +0.5$: Strong positive association
   - $+0.2 \le r < +0.5$: Moderate positive association
   - $-0.2 < r < +0.2$: Little to no linear association
   - $-0.5 < r \le -0.2$: Moderate inverse association
   - $r \le -0.5$: Strong inverse association
   *Disclaimer: Correlation indicates co-occurrence in historical observations, not biological or psychological causation.*

---

### F. Period Comparison System
1. **Absolute Delta**:
   $$\Delta = \text{Current Value} - \text{Previous Value}$$
2. **Percentage Change**:
   $$\% \Delta = \left(\frac{\text{Current Value} - \text{Previous Value}}{|\text{Previous Value}|}\right) \times 100$$
   - **Zero Denominator Protection:** If $\text{Previous Value} = 0$, the system displays `N/A (baseline was 0)` rather than causing a division-by-zero error or showing an infinite percentage.

---

## 3. Behavioral Insights Engine Rules

The engine uses transparent, deterministic heuristics without external ML dependencies:

| Domain | Rule Trigger | Confidence | Insight Narrative |
|---|---|---|---|
| **Productivity** | Tasks completed $\ge 1.25\times$ prior period ($N \ge 3$) | `HIGH` | Task Completion Velocity Increased |
| **Productivity** | Tasks completed $\le 0.70\times$ prior period ($N_{\text{prev}} \ge 4$) | `HIGH` | Task Completion Rate Moderated |
| **Productivity** | Avg estimation error $\ge +15.0$ min ($N \ge 3$) | `HIGH` | Estimation Bias: Tasks Frequently Take Longer Than Expected |
| **Productivity** | Avg estimation error $\le -15.0$ min ($N \ge 3$) | `HIGH` | Planning Tendency: Tasks Completed Faster Than Estimated |
| **Study** | Top subject $\ge 60\%$ and bottom active subject $\le 10\%$ of time | `HIGH` | Subject Study Distribution Imbalance |
| **Study** | Active subject near target date with incomplete topics | `HIGH` | Syllabus Milestone Approaching: [Subject] |
| **Habits** | Habit completion $\ge 80\%$ with $\ge 3$ expected logs | `HIGH` | Consistent Keystone Habit: [Habit] |
| **Habits** | Habit completion $< 40\%$ with $\ge 3$ expected logs | `MEDIUM` | Habit Friction Observed: [Habit] |
| **Time** | Timetable schedule adherence $\ge 80\%$ ($N \ge 5$) | `HIGH` | High Schedule Adherence |
| **Time** | Timetable schedule adherence $< 50\%$ ($N \ge 5$) | `HIGH` | Timetable Schedule Divergence |
| **Well-being** | $N \ge 14$ and Pearson $\|r\| \ge 0.40$ | `HIGH` | Well-being Pattern: [Variables Correlation] |
| **Well-being** | Avg stress $\ge 7.0$ and avg energy $\le 4.5$ | `HIGH` | Rest & Recovery Advisory |
| **Finance** | Single category $\ge 40\%$ of total expenses | `HIGH` | Top Spending Driver: [Category] |
| **Finance** | Income $> 0$ and savings rate $\ge 20\%$ | `HIGH` | Positive Cash Flow & Savings Rate |

---

## 4. Plotly Interactive Visualizations

All visualizations adhere to the **Minimal Modern Dark + Soft Indigo Accents** palette:
- **Card/Paper Background:** `#1B1F2A`
- **Main Font:** Inter, `#F3F4F6`
- **Grid Lines:** `#2A2F3A`
- **Interactive Mode:** Responsive, `displayModeBar: false`, unified hover tooltips.
- **Local Asset Serving:** `static/js/plotly.min.js` bundled locally for zero-latency, offline-capable rendering without CDN reliance.

---

## 5. Security & Multi-User Data Isolation

Every query and calculation in `apps.analytics`:
1. Enforces `request.user` filtering on all ORM queries (`Task`, `StudySession`, `HabitLog`, `Activity`, `DailyMetric`, `Transaction`, `ScheduleBlock`).
2. Scopes dismissed insights strictly to `DismissedInsight(user=request.user)`.
3. Validates date ranges to prevent temporal overflow or SQL injection.
4. Protects against Insecure Direct Object References (IDOR).
