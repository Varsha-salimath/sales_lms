# CRT voice viva — what is built

Every CRT day ends with a 3–4 minute spoken viva with **Asha** (Gemini Live native audio).
A day only counts as complete — and the next day only unlocks — once its viva is passed.
Design background and the original prototype: `docs/AI_VIVA_PRD.md` (Saraga).

## Switch it on

1. Add the key to the server `.env` (backend only, never in the browser):
   `GEMINI_API_KEY=…`
2. `docker compose --env-file .env up -d backend`

Until a key is set the viva is **off**: nothing is gated and learners see no viva step.
Optional settings (env or `site_config.json`, lower-case in site config):

| Setting | Default | Meaning |
|---|---|---|
| `GEMINI_LIVE_MODEL` | `gemini-3.8-live` | Voice model (Asha) |
| `GEMINI_TEXT_MODEL` | `gemini-flash-latest` | Writes the questions and scores the answers |
| `GEMINI_VOICE` | `Kore` | Asha's voice |
| `crt_viva_required` | `1` | Set `0` to make the viva optional (not gating) |

## Flow

1. Learner finishes all sessions of Day N → the day shows **Viva pending** (home + day page).
2. `/crt/N/viva`: how it works, mic check, attempts left, past attempts.
3. **Start** → `start_attempt` generates 5 fresh questions from that day's lessons, session outlines
   and quiz answers (avoiding questions from earlier attempts), then mints a short-lived Gemini Live token.
   The paper stays on the server; Asha receives one question at a time through the `get_next_stem` tool.
4. The call: Asha asks, the learner answers; a pause of 3 s, "I'm done" or releasing "Hold to talk" ends
   the answer. Thin answers get one follow-up (max 2 per viva). 5-minute hard stop.
5. `finish_attempt` scores it → `/viva/<attempt>` report.

## What is measured per question

| Signal | How |
|---|---|
| Time to start answering | From the moment Asha's audio finishes playing to the learner's first speech (browser), capped by the server's own clock |
| Pauses | Silences over 2 s inside an answer; count and longest |
| Speaking time, words per minute, filler words | Mic activity + transcript |
| Left the screen | Tab hidden or window lost focus while a question was open |
| Knowledge | Text model grades the transcript against the question's model answer and key points (0–100), with covered / missed points and feedback |

**Score** = 70% Knowledge + 30% Fluency. Pass = 60 and at least 4 of 5 questions answered; 80+ = "Ready".
Fluency is built from the timing above; long silences and leaving the screen lower it and are flagged
("watch-outs") for the Training Manager, but never fail a learner on their own.

## Attempts

3 per day. Closing the tab mid-viva still counts if anything was answered (scored as is).
After 3 failed attempts the day is blocked; the learner's Training Manager (or an admin) opens the report
or **Voice vivas** (`/vivas`) and clicks **Unlock 3 more** (`Sales Viva Unlock`).

## Data

- `Sales Viva Attempt` — one per attempt (scores, verdict, flags, summary, paper, live state).
- `Sales Viva Turn` — child rows: question, transcript, timing, knowledge/fluency, feedback.
- `Sales Viva Unlock` — extra attempts granted.

Only System Manager/Moderator can open these in Desk; learners and managers use the API, which checks that
the viewer is the learner, their manager (reporting tree / team access) or staff.

## Code

- Backend: `backend/lms/lms/sales_viva.py`; gating in `sales_journey._crt_states` (`viva_pending`).
- Frontend: `pages/Sales/SalesViva.vue` (call), `pages/Sales/viva/liveViva.js` (audio engine + timing),
  `pages/Sales/VivaReport.vue`, `pages/Sales/VivaResults.vue`.
