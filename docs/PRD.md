# Product Requirements Document (PRD)

**Project Name:** Debrief Golf
**Document Version:** 5.0 (The Perfect 10 / Final Blueprint)
**Target Platform:** Responsive Web Application (Optimized for Desktop/Tablet deep-dive analysis, Mobile-ready)

## 1. Executive Summary & Vision

### 1.1 Problem Statement

There is a widespread dissatisfaction with Garmin's basic native aggregations. Golfers desire Arccos-level Strokes Gained diagnostics, dispersion modeling, outlier filtering, and prescriptive post-round learning, which are currently missing from the native Garmin Golf ecosystem.

### 1.2 Product Overview

Debrief Golf is a unified golf analytics, diagnostics, and learning web application built to ingest and synthesize the complete spectrum of data generated across the entire Garmin Golf hardware ecosystem:

- **On-Course Devices:** Approach Smartwatches (S70, S62, S42), CT10 Club Tracking Sensors, Approach Handhelds (G12/G80), and Laser Rangefinders (Z82, Z30).
- **Launch Monitors & Simulators:** Approach R10 (Doppler radar) and Approach R50 (Optical/Camera launch monitor) covering both Driving Range practice sessions and Home Tee Hero / Virtual Simulator rounds.

Debrief Golf provides an Arccos-grade post-round diagnostic platform that bridges on-course performance with launch monitor delivery data and prescriptive learning modules.

### 1.3 Non-Goals (Explicitly Out of Scope)

- **No Live In-Round GPS Rangefinder Interface:** The app does not act as an on-course rangefinder or live caddie while playing.
- **No Direct Hardware Bluetooth Management:** Device pairing remains inside native Garmin apps/hardware.

## 2. Target Audience & User Personas

| Persona | Profile & Behavior | Primary Pain Point | Platform Goal |
|---|---|---|---|
| **The Data-Driven Amateur** | Mid-to-low handicap, analytical golfer who owns Garmin hardware (Approach watches, CT10 sensors, R10/R50 launch monitors). | Dissatisfaction with Garmin's basic native aggregations. | Wants Arccos-level Strokes Gained diagnostics, dispersion modeling, and outlier filtering. |
| **The PGA Coach** | Professional instructor managing multiple students. | Raw data from students is too cluttered to parse efficiently before a 45-minute lesson. | Needs the 1-Page Lesson Brief to quickly understand a student's mechanical flaws and strategic errors. |

## 3. Success Metrics & KPIs

| Metric Category | KPI Definition | Target Benchmark |
|---|---|---|
| **Activation** | Percentage of users who complete their first "2-Minute Fast Audit". | >85% of synced rounds fully verified. |
| **Engagement** | Percentage of users who click a YouTube practice combine link after syncing a round. | >35% conversion to Practice Hub within 7 days. |
| **Retention** | 30-day active user retention rate. | >45% of users returning following a synced round. |

## 4. Ingestion, Data Integrity & Edge Cases

### 4.1 Multi-Source Garmin Data Pipeline

- **Garmin Connect API (OAuth 2.0):** Automatic cloud sync for completed scorecards, GPS shot tracks, and activity files.
- **Direct .FIT File Upload:** Fallback binary parser for watch activities and offline round recovery.
- **Launch Monitor Ingestion:** Parses CSV/JSON exports from Approach R10 and R50 containing detailed ball and club delivery arrays.

### 4.2 The "2-Minute Fast Audit" Wizard

- **Fringe vs. True Putting Isolation:** Automatically prompts when a putter is used outside the green boundary polygon.
- **"Insert Shot Between" Timeline Tool:** Allows users to insert missing shots between two registered coordinates with automatic coordinate snapping.
- **Penalty Drop Logic Wizard:** Distinguishes Lateral Hazard from Out of Bounds / Lost Ball.
- **Strike Quality & Contact Tagging:** One-tap tagging modal for shots yielding <-0.4 Strokes Gained.

### 4.3 Edge Cases & Fallbacks

- **Garmin API Webhook Failure:** If the Garmin API webhook fails, the system immediately presents the direct .FIT drag-and-drop fallback to the user.
- **Corrupted Data Parsing:** If a .FIT file is corrupted or missing essential coordinates, the round is automatically flagged as "Casual Practice / Extreme Weather" to prevent corrupting the Smart Bag baselines.

## 5. On-Course Analytics & Performance Hub

### 5.1 Granular Strokes Gained Engine

Benchmarked against target handicap buckets (Scratch, 5, 10, 15, 20, 25 HDCP):

```
SG = Benchmark(Start Lie, Start Dist) - Benchmark(End Lie, End Dist) - 1
```

### 5.2 Advanced Coaching Diagnostics & Error Avoidance

- **Putting Mechanics Split:** Calculates lag speed efficiency (>20 ft) and start-line conversion (<6 ft).
- **The "Tiger 5" Scoring Killers:** Tracks double bogeys+, 3-putts, Par 5 bogeys, blown recoveries inside 50y, and penalties inside 150y.
- **Short-Sided vs. Safe Leave Analysis:** Identifies when an approach shot leaves the player short-sided.

### 5.3 Spatial Strategy & 2D Dispersion Maps

- **Smart Bag Integration:** Outlier-filtered carry, roll, and lateral standard deviation per club.
- **Dispersion Cone Visualizer:** Overlays empirical 2D dispersion ellipses over hole satellite maps to highlight high-risk aim points.

## 6. Launch Monitor & Simulator Integration

### 6.1 Driving Range Practice Diagnostics

- **Delivery Profiling:** Aggregates delivery numbers per club across practice sessions (e.g., Club Path, Face Angle, Spin Axis, Smash Factor).
- **Sim vs. Real-World Gapping Delta:** Compares launch monitor carry numbers against on-course GPS tracked distances.

### 6.2 Virtual / Sim Round Hub (Home Tee Hero, E6, GSPro)

Dedicated simulator dashboard segregated from real-world handicap calculations.

## 7. Actionable Learning Hub & Prescriptions

### 7.1 Prescriptive Practice Combines

Pairs step-by-step written instructions with curated video tutorials:

| Weakness Identified | Generated Combine Drill | Target Metric |
|---|---|---|
| Approach (100–125y) | 9-Ball Wedge Matrix | ≥7/9 inside 20ft radius. |
| Driver Dispersion | 30-Yard Corridor Test | Spin axis within ±4°, lateral miss <15y. |
| Iron Strike Quality | Low-Point Compression | Smash factor >1.36, clean turf interaction. |
| Putting Lag Speed | Safety Circle Test | ≥80% inside 3ft ring. |

### 7.2 1-Page "Coach-Ready" Lesson Brief

Generates a headless PDF export summarizing net stroke leaks, strike patterns, Tiger 5 metrics, and a recommended coaching agenda.

## 8. UI/UX Layout Specification

```
┌────────────────────────────────────────────────────────────────────────┐
│ NAVIGATION:  Dashboard | Rounds | Practice (R10/R50) | Virtual Bag | Share│
├────────────────────────────────────────┬───────────────────────────────┤
│ ROUND SNAPSHOT: 78 (+6) vs 5 HDCP      │ TIGER 5 DISASTER METER        │
│ • SG: OTT:  +1.20                      │ • Doubles+: 1                 │
│ • SG: APP:  -2.40 ⚠️ (Toe/Open Bias)   │ • 3-Putts: 2 (Speed Issue)    │
│ • SG: ARG:  +0.35 (1 Short-Sided)      │ • Par 5 Bogeys: 0             │
│ • SG: PUTT: -1.15 (Lag Proximity: 4.8ft)│ • Clean Card Index: 83%       │
├────────────────────────────────────────┴───────────────────────────────┤
│ R10/R50 PRACTICE LINKAGE (7-IRON DELIVERY PROFILE)                     │
│ • Avg Path: -3.8° (Out-to-In)  |  Avg Face: +1.9° (Open)  | Smash: 1.34│
├────────────────────────────────────────────────────────────────────────┤
│ HOLE REPLAY & STRATEGY ENGINE                                          │
│ ┌───────────────────────────┬────────────────────────────────────────┐ │
│ │ Hole 7 | Par 4 | 418y     │ Mapbox Satellite Canvas               │ │
│ │ Shot 2: 7-Iron (162y)     │ • Plotted Shot Vector (SG: -0.58)      │ │
│ │ Tag: "Heel / Push-Slice"  │ • 2D Dispersion Ellipse vs Tucked Pin  │ │
│ │ Result: Short-Sided Bunker│ • Center-Green Aim Comparison Line     │ │
│ └───────────────────────────┴────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

## 9. Technical Architecture & Security

### 9.1 Technology Stack

- **Frontend:** Next.js 15 (App Router, TS), Tailwind CSS, shadcn/ui, Recharts, Mapbox GL / Deck.gl, IndexedDB.
- **Backend:** FastAPI (Python 3.12+), NumPy, Pandas, fitparse, SQLModel / SQLAlchemy.
- **Database:** PostgreSQL 16 with PostGIS.
- **Testing:** pytest (backend), Vitest + React Testing Library (frontend).

### 9.2 Data Privacy & Security Constraints

- **GDPR & CCPA Compliance:** Because we are tracking precise user locations via GPS coordinates and authenticating through Garmin Connect via OAuth 2.0, strict GDPR and CCPA compliance requirements must be implemented.
- **Data Retention:** Explicit data retention policies must be defined, ensuring users can fully delete their spatial and scorecard data upon request.

See [`docs/DATA_PRIVACY.md`](./DATA_PRIVACY.md) for the working policy that translates this section into concrete implementation to-dos.

## 10. Phased Development Roadmap

This execution plan breaks the platform into test-driven phases optimized for modern full-stack development.

- **Phase 1: Environment, Database Schemas & Data Parsers** — Setup PostgreSQL 16 + PostGIS via Docker. Build SQLModel/SQLAlchemy models (Users, Courses, Holes, Rounds, Shots). Implement Broadie Strokes Gained baseline lookup tables and Garmin .FIT / CSV parsers.
- **Phase 2: Analytics Core (Strokes Gained, Tiger 5 & Smart Bag)** — Create the Strokes Gained calculation engine supporting all distance sub-brackets. Evaluate scorecard arrays for Tiger 5 violations and calculate the Clean Card Index (CCI). Implement IQR outlier rejection for Smart Bag club gapping and lateral dispersion.
- **Phase 3: Frontend Foundations & The "2-Minute Fast Audit" Wizard** — Scaffold Next.js 15 App Router with shadcn/ui. Build the audit wizard to handle missed tap-ins, penalty drop classifiers, and strike tagging. Connect the .FIT file upload UI to the FastAPI backend.
- **Phase 4: Hole Replay, Dispersion Maps & Strategy Engine** — Integrate Mapbox GL to render hole satellite imagery and vector paths. Add SVG/Deck.gl overlays to display 2D dispersion ellipses for selected clubs. Implement the Short-Sided and Sucker Pin strategy alert banners.
- **Phase 5: Practice Hub, R10/R50 Delivery & Coach Export** — Create the Practice Hub UI with prescriptive combines, written instructions, and embedded video assets. Build the R10/R50 delivery profile view (Face-to-Path, Spin Axis, Smash Factor). Implement the printable 1-Page Coach Lesson Brief via React-PDF.

See [`docs/DEVELOPMENT_PLAN.md`](./DEVELOPMENT_PLAN.md) for this roadmap expanded into actionable tasks and acceptance criteria.
