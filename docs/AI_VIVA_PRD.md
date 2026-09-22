# AI Viva — CRT end-of-day oral assessment

**PRD + technical feasibility** for Infinity Learn Sales LMS  
**Course:** `sales-crt` · **Local stack already running** · **Researched 22 Sep 2026**  
**FX used in this doc:** ₹84 / USD (midpoint of ₹83–85; recheck before a production PO)

This is the missing assessment gate after each CRT day. It is **not** a chatbot and **not** a generic oral tutor. The learner finishes that day's `Course Lesson` chain; **Asha** examines them on that day's `Sales CRT Session` topics and content links only.

---

## Recommendation (read this first)

**Latency is now a hard requirement.** Ship **native speech-to-speech** (Architecture B) with persona Asha. Keep the old cascade as the **low-cost fallback**, not the target.

Priority order: **(1) <500 ms conversational feel** · **(2) assessment reliability** · **(3) Indic / Sarvam** · **(4) cost** · **(5) LMS fit**.

| Layer | Choice |
| --- | --- |
| Architecture | **B — native S2S** over WebRTC. Cascade (Arch C) is the cheap fallback if S2S budget is refused. |
| Persona | **Asha** — examiner with coach warmth. Not a chatbot. |
| Primary voice | **OpenAI `gpt-live-1`** WebRTC (full duplex). **Azure `gpt-realtime-2.1`** WebRTC in **South India** if Legal wants residency without leaving S2S. |
| Cheaper S2S alt | Gemini **3.8 Live** (~$0.023/min audio) if OpenAI minute-rate is too high |
| Question feed | Tool `get_next_stem` — fetches that day's reviewed bank. Voice model does not invent the exam. |
| Rubric eval | **gpt-4.1-mini** async on the transcript. Voice model does **not** grade. |
| Indic overlay | **Sarvam** `saaras:v3-realtime` + `bulbul:v3` in Phase 2 Hindi. Not the MVP examiner. |
| Do not use as examiner | **Bodhan** — REST clips, 30 s cap, no session API |
| Frontend | Vue `/viva/:dayNumber` WebRTC to vendor; Frappe issues ephemeral token |
| Backend | Frappe `lms.lms.sales_viva.*` → MariaDB Sales Viva* + Redis + existing Socket.IO |
| MVP languages | **English + Hinglish** on S2S. Hindi via Sarvam in Phase 2. |
| 5-min S2S cost | **$0.30 (₹25)** on `gpt-live-1` · **~$0.18 (₹15)** on Gemini 3.8 Live |
| 5-min cascade fallback | **$0.15 (₹13)** — keep this stack; it will not hit 500 ms |

**Can we hit 500 ms?** Yes on the **barge-in / overlapping** clock with native S2S (Azure publishes WebRTC ~100 ms; independent US-East WebRTC benches put OpenAI Realtime at **232 ms p50 / 281 ms p95** and Gemini Live at **250 ms p50**). After a **clean silence** end-of-utterance, published conversational numbers cluster **0.8–1.2 s** (`gpt-live-1` 0.798 s turn-taking; Gemini 3.8 Live 1.18 s; `gpt-realtime-2.1` 1.12 s minimal). Measure both clocks. Do not use a cascade and hope.

Sarvam wins India residency and Indic STT/TTS. It has **no native S2S**. Bodhan is a batch Indic API, not a viva. OpenAI Live / Azure Realtime is the examiner path that can feel under 500 ms.

---

## 1. Product design — end-of-day CRT viva

### Session defaults

| Rule | MVP value |
| --- | --- |
| Default duration | 6 minutes (floor 5, hard stop 8) |
| Stem questions | 5, one per day-concept cluster |
| Follow-ups per concept | Max 1 |
| Follow-ups per session | Max 2 |
| Difficulty mix | 2 understand, 2 apply, 1 scenario |
| Pass / Ready cut-off | 60 / 80 |
| Same-day attempts | 1 retry |

### Persona: Asha (ship this)

One voice. Firm, fair, brief. She sounds like a CRT faculty who has sat 200 vivas: one acknowledgement after a solid answer, then the next probe. Not a cheerleader tutor. Not a cold board examiner. Not conversational small-talk. Students take her seriously; they do not feel mocked. Hinglish answers are accepted without comment.

| Stance | Verdict | Why |
| --- | --- | --- |
| Teacher | Reject | Teaches. Viva must measure what the day already taught. |
| Cold examiner | Reject | Raises anxiety; CRT is training, not a board exam. |
| Coach / tutor | Reject for scoring | Drifts into explanation; inflates scores; feels like a bot. |
| **Asha (examiner + warmth)** | **Ship this** | Preserves assessment validity and completion rate. |

### Session shape

| Rule | MVP value | Rationale |
| --- | --- | --- |
| Thinking time | 8 s after TTS ends, then 25 s answer window | Oral exam, not an essay |
| Silence | 8 s nudge once; 20 s more → skip concept, score 0 | Protects the remaining bank |
| “I don’t know” | Score 0 on stem; one easier probe; then next topic | Honesty is allowed; mastery is not inferred |
| Repeat / rephrase | Once per stem, free; then clock keeps running | Accent/noise fairness, not a stall tactic |
| Interruptions | Learner barge-in stops TTS after 280 ms | Feels live; examiner does not talk over them |
| STT failure | One retry prompt; second fail → type fallback 400 chars | Never fail the day on a mic |
| Auto-end | Timer, or 5 stems resolved, or learner abort | Always write a result row |

### Adaptive move logic

| Stem verdict | Next move | Leave topic when |
| --- | --- | --- |
| Correct (≥80) | One deeper application follow-up, or next topic if follow-up budget spent | Follow-up asked or budget 0 |
| Partial (40–79) | One probe on the missing piece | Probe scored, or student says they don’t know |
| Incorrect (<40) | One clarification at recall level, then leave | Clarification done — do not tutor |

### CRT lock fit

Unlock when that day's lessons are 100% `Complete` in `LMS Course Progress`. Fail or skip does **not** permanently block Day N+1: one retry, then progress with a **Needs revision** flag. Staff skip. Last-day viva complete (any score) unlocks Sales Training Evaluation — same pattern as today's CRT → eval gate.

Duration and counts are product rules, not model defaults. Asha's system prompt is versioned on `Sales Viva Settings`.

---

## 2. Question generation — hybrid, day-scoped

Questions are generated from that CRT day's sessions only: topic, description, lesson body, and `Sales CRT Content Link` URLs. No general sales trivia. No other day's product pitch.

**Pick C — hybrid. Not A. Not B.**

Pre-generate a reviewed bank after schedule ingest / lesson save. Live, generate only the follow-up and the leave-topic decision.

| Mode | Verdict | Why |
| --- | --- | --- |
| A · Bank only | Reject as sole mode | Cheap and auditable, but two trainees in a hostel get the same five stems by dinner |
| B · Fully live | Reject for scoring | Off-syllabus questions and ~400 ms extra before every stem |
| **C · Hybrid** | **Ship** | 24 stems/day in the bank (8 recall/understand, 8 apply, 8 scenario). Session draws 5 unseen. Follow-ups are live |

### Cognitive mix for a sales CRT day (target share of 24-question bank)

| Level | Share |
| --- | --- |
| Recall | 15% |
| Understand | 25% |
| Apply | 25% |
| Reason | 15% |
| Scenario | 15% |
| Practical | 5% |

A 5-question draw should land ~1 recall, 2 understand/apply, 1 reason or scenario, 1 practical (LSQ / product / call flow).

### What the generator reads

| Source | DocType / field | Use |
| --- | --- | --- |
| Day sessions | `Sales CRT Session.topic`, description, `session_type` | Concept list; skip break/lunch |
| Lesson body | `Course Lesson.body` | Facts the day actually taught |
| Content links | `Sales CRT Content Link.url` + label | Fetch title + extract; do not invent |
| Day number | `day_number` on the session | Hard scope filter |
| Forbidden | Other days, web, model priors | Prompt + post-filter |

### Draw algorithm

Hash `member + day_number + attempt_index + bank_version` to shuffle. Enforce one question per `concept_id`. Never reuse a stem the learner already heard on a prior attempt of the same day. If the bank is stale (lesson body changed), bump `bank_version` and regenerate overnight.

### Sample CRT Day-2 stems (illustrative)

| Level | Stem |
| --- | --- |
| Understand | Why do we open a Class 10 parent call with the child's current board result before the pitch? |
| Apply | A parent says Foundation is the same as school tuition. How do you separate them in one sentence? |
| Reason | If you skip need-generation and jump to Math Champ, what usually happens to the demo booking? |
| Scenario | Mrs Sharma has 90 seconds. Walk the close from recap to the Saturday demo slot. |
| Practical | Which LSQ disposition do you use when the parent asked to call after the PTM? |

---

## 3. Evaluation framework (rubric JSON)

Spoken answers are scored on **meaning** against a model answer and allowed alternates. Delivery is logged, never weighted. This matches how a fair CRT faculty marks a Hindi-medium joiner who knows the pitch.

### What counts (100%) vs diagnostic (0%)

| Dimension | Weight | Scores academically? | Note |
| --- | --- | --- | --- |
| Concept accuracy | 35% | Yes | Facts match the day's material |
| Understanding | 20% | Yes | Can explain why, not only what |
| Application | 20% | Yes | Uses it in a call / objection |
| Reasoning | 15% | Yes | Cause → effect in the sales motion |
| Follow-up recovery | 10% | Yes | Did the probe get them there |
| Clarity of wording | 0% | No — diagnostic | Poor English is not a fail |
| Confidence / energy | 0% | Never | Mic + personality bias |
| Accent / fluency | 0% | Never | Indian English and Hinglish are in-scope |

Each stem is 0 / 40 / 70 / 100 (wrong / partial / mostly / full). Partial is the default when a key point is missing but the rest is right. Alternate correct answers are listed on the bank item; the evaluator must accept them. Technically right, poorly worded: full marks on accuracy, diagnostic flag on clarity.

Concept score = mean of stems tagged to that concept. Overall = weighted sum above. Bands reuse the LMS report cut-offs: Needs improvement <60, Average 60–79, Good 80–89, Excellent ≥90.

### Pass policy

| Overall | Status |
| --- | --- |
| ≥80 | Ready — unlock next day, no flag |
| 60–79 | Pass — unlock, Needs revision |
| <60 after retry | Complete with fail flag; still unlock Day N+1 |
| Abort / no audio | Incomplete — does not unlock |

**Do not reuse OJT keyword scoring.** `Sales OJT Attempt` scores a turn if keywords hit a beat threshold. That is the wrong instrument for a viva. The evaluator returns structured JSON stored on `Sales Viva Session`.

### LMS-storeable result JSON

```json
{
  "schema_version": "1.0",
  "viva_session": "VIVA-…",
  "member": "user@infinitylearn.com",
  "course": "sales-crt",
  "day_number": 2,
  "duration_sec": 348,
  "overall": 74,
  "band": "Average",
  "status": "Pass",
  "ready": false,
  "weights": {
    "accuracy": 0.35,
    "understanding": 0.20,
    "application": 0.20,
    "reasoning": 0.15,
    "followup": 0.10
  },
  "dimensions": {
    "accuracy": 80,
    "understanding": 70,
    "application": 70,
    "reasoning": 60,
    "followup": 80
  },
  "concepts": [
    { "id": "need-gen", "title": "Need generation", "score": 70, "weak": false }
  ],
  "strengths": ["Separates Foundation from tuition"],
  "weak_concepts": ["LSQ dispositions"],
  "revision": ["CRT 2 · LSQ session"],
  "turns": [
    {
      "i": 1,
      "q_id": "d2-q07",
      "level": "apply",
      "question": "…",
      "transcript": "…",
      "score": 70,
      "reason": "Named the difference, missed demo hook"
    }
  ],
  "diagnostics": {
    "clarity": 55,
    "confidence": null,
    "accent": null,
    "stt_wer_est": 0.11,
    "language": "en-IN+hi-mix"
  },
  "model": { "eval": "gpt-4.1-mini", "prompt_rev": "asha-v3" }
}
```

---

## 4. Speech-to-speech architecture

Optimise **<500 ms feel, then assessment reliability, then Indic, then cost, then LMS**. Architecture **B** wins that order. Architecture **C** stays as the **low-cost fallback** if S2S budget is refused. Architecture A feels like a walkie-talkie.

### Architecture B path (ship for <500 ms)

```
Learner mic (WebRTC)
  → Native S2S (gpt-live-1 / Azure gpt-realtime-2.1 / Gemini 3.8 Live)
       · system prompt: Asha the examiner
       · tool: get_next_stem(day_number) → reviewed bank only
       · interrupt / barge-in native
  → Transcript stream ──→ Eval LLM (gpt-4.1-mini JSON rubric, off the audio path)
  → Vue `/viva/:dayNumber` plays remote audio; Frappe never transcodes
```

### Architecture C path (low-cost fallback — keep this)

```
Learner mic (opus / PCM)
  → VAD (browser + optional Flux EagerEndOfTurn)
  → Streaming STT (Deepgram Nova-3 / Sarvam saaras:v3-realtime)
  → Cheap LLM (turn + follow-up) ──→ Streaming TTS (Azure en-IN / Sarvam Bulbul / Cartesia)
  → Eval LLM (JSON rubric, off the TTFA path)
```

|  | A · Batch cascade | **B · Native S2S (pick)** | C · Hybrid stream (fallback) |
| --- | --- | --- | --- |
| Path | File STT → LLM → file TTS | gpt-live-1 / Azure realtime / Gemini Live | Stream STT → mini LLM → stream TTS |
| Published TTFA | 3.0–6.0 s | **~100–300 ms WebRTC benches; 0.8–1.2 s after clean silence** | **1.4–2.2 s typical India** |
| Hits <500 ms? | No | **Yes on barge-in / overlapping clock** | Only with speculative start; p50 still ~0.8–1.5 s |
| 5-min $ | ~$0.12 | **$0.18–$0.30** | **$0.15** |
| JSON scoring | Good (separate eval) | **Good if eval is a second pass** | Good (separate eval) |
| Indian English | Depends on STT | Fair; Hinglish mixed | Best if Nova-3 multi / Sarvam |
| Indic / residency | — | Weak unless Azure South India | Sarvam India-hosted overlay |
| Scale | Easy | Vendor concurrency $ | Browser→vendor STT; Frappe stays thin |
| Complexity | Lowest | Medium (WebRTC + tools) | Medium (two streams) |
| Verdict | Local prototype only | **MVP if 500 ms is hard** | **Fallback if S2S $ is refused** |

**Two clocks, do not mix them**

| Clock | What it measures | Who can hit <500 ms |
| --- | --- | --- |
| **TTS first-byte** | Text already exists → first audio sample | Almost everyone. Cartesia ~40–90 ms claimed / ~166–190 ms measured. ElevenLabs Flash ~75 ms **inference**. Sarvam Bulbul **<250 ms**. Bodhan ~200 ms clip. This is **not** conversational TTFA. |
| **Barge-in / overlapping TTFA** | User is still wrapping up; model starts audio | **Native full-duplex S2S.** Azure WebRTC **~100 ms**. Independent US-East: OpenAI Realtime **232 ms p50**, Gemini Live **250 ms p50**. |
| **After-silence TTFA** | VAD end-of-utterance → first Asha sample | Published S2S: `gpt-live-1` **0.798 s** turn-taking; Gemini 3.8 Live **1.18 s**; `gpt-realtime-2.1` **1.12 s** minimal / **2.33 s** high reasoning. Cascade India typical **1.4–2.2 s**. |

Sub-500 ms **after a hard silence** is not a published OpenAI/Gemini EOU number. Sub-500 ms **as the learner experiences the turn** (model starts as they trail off, or WebRTC S2S on a fat path) **is** what native S2S is for. That is why B is the pick.

**Reliability without giving up speed:** A realtime model will compliment and wander if it both chats and grades. So it does **not** grade. Asha's system prompt + a tool that returns the next bank stem + a separate async evaluator is the examiner contract. You still pay S2S rates. You do not pay them twice for scoring.

---

## 5. Vendor and model comparison

Rates researched **22 Sep 2026**. FX ₹84 / USD. List prices move; treat this as the planning sheet, not a PO.

### Speech-to-text (streaming unless noted)

| Provider | Model | USD / min | INR / min | Indic / Hinglish | Use |
| --- | --- | --- | --- | --- | --- |
| Deepgram | Nova-3 mono stream (promo / regular) | 0.0048 / 0.0077 | 0.40 / 0.65 | Indian English strong; Hinglish = multi | Default STT |
| Deepgram | Nova-3 multilingual stream | 0.0058 / 0.0092 | 0.49 / 0.77 | Code-mix better | **Budget this for MVP** |
| Deepgram | Flux English (turn detect) | 0.0065 promo | 0.55 | English agent VAD | Optional VAD |
| AssemblyAI | Universal-2 async | 0.0025 (0.15/hr) | 0.21 | 99 langs; not India-first | Bank ingest / recordings |
| AssemblyAI | Universal-Streaming | 0.0025 (0.15/hr session) | 0.21 | Limited Indic | Lowest stream STT |
| AssemblyAI | U3.5 Pro Realtime | 0.0075 (0.45/hr) | 0.63 | EN/ES/DE/FR | Skip |
| OpenAI | gpt-4o-mini-transcribe | 0.003 | 0.25 | Decent IN-EN; weak Hindi | Lowest-cost STT (Stack A) |
| OpenAI | gpt-4o-transcribe / Whisper-class | 0.006 | 0.50 | Same family | Fallback |
| OpenAI | gpt-realtime-whisper / live-transcribe | 0.017 | 1.43 | Live only | Too dear |
| Google | Chirp 3 STT v2 standard | 0.016 | 1.34 | Broad multilingual | Skip for cost |
| Azure | Speech standard realtime | 0.0167 (1/hr) | 1.40 | en-IN, hi-IN, many Indic | India-region fallback |
| AWS | Transcribe standard | 0.024 | 2.02 | Some Indic | Skip |
| Sarvam | `saaras:v3-realtime` WS | 0.0060 (₹0.50) | 0.50 | Best Hinglish / 22 langs; Fast mode <150 ms first token | Phase 2 Hindi STT; India-hosted |
| Sarvam | `saarika:v2.5` (legacy) | same family | — | 11 langs; keep only if already wired | Do not start new work here |
| Bodhan | `indic-transcribe` REST | 0.0012 (₹0.10) | 0.10 | 22 langs; **30 s clips**; 8 RPM | Not a live viva |

Sources: deepgram.com/pricing (Aug–Sep 2026 promo vs regular); assemblyai.com/docs + blog Jul 2026; developers.openai.com/api/docs/pricing (22 Sep 2026); cloud.google.com/speech-to-text/pricing; Azure $1/hr standard; AWS tier 1 $0.024/min; **docs.sarvam.ai pricing 22 Sep 2026: STT ₹30/hour = ₹0.50/min** (earlier marketing ₹1.50/min is stale); console.bodhan.ai ₹0.10/min.

### Text-to-speech

| Provider | Model | USD / 1M chars | 6k chars (5-min) | TTFA | Use |
| --- | --- | --- | --- | --- | --- |
| Azure | Neural / HD Flash | 16 | $0.10 (₹8) | 120–250 ms stream | **Default Asha en-IN** |
| Azure | Neural HD | 22 | $0.13 | similar | Skip |
| OpenAI | tts-1 / gpt-4o-mini-tts | 15 | $0.09 | ~300 ms | Fallback |
| Cartesia | Sonic 3 | 33–50 | $0.20–$0.30 | 40–80 ms | If TTFA slips |
| ElevenLabs | Flash / Turbo API | 50 | $0.30 | 75–300 ms | Premium voice only |
| ElevenLabs | Multilingual v2/v3 | 100 | $0.60 | higher | Do not |
| Deepgram | Aura-2 | 30 | $0.18 | agent-oriented | Optional one-vendor |
| Google | Chirp 3 HD TTS | 30 | $0.18 | good | Skip |
| Google | Standard / WaveNet-class | 4 | $0.02 | OK | Austerity only |
| Sarvam | Bulbul v3 WS | 35.71 (₹30/10k) | $0.21 | **<250 ms** first-byte (India-hosted) | Phase 2 Hindi / Hinglish TTS overlay |
| Bodhan | `indic-speak` REST | 7.14 (₹6/10k) | $0.04 | ~200 ms first audio; **~30 s / sentence-or-two**; 4 RPM | Not live examiner |
| Smallest | Lightning v3.1 | ~17.50 ($0.175/10k) | $0.11 | **<100 ms** TTFB claimed; 12 langs incl. Indic | Speculative cascade TTS alt |

TTS dominates the bill. Cut cost by shortening Asha, not by swapping the evaluator model. Never ElevenLabs in MVP.

### LLM layer — do not use one fat model everywhere

| Job | Model | In / out per 1M | 5-min $ | Why |
| --- | --- | --- | --- | --- |
| Bank generation (batch) | gpt-4.1-mini or gpt-5.6-terra | 0.40 / 1.60 (4.1-mini) | ~$0.002 amortised | Needs instruction-following |
| Turn + follow-up | gpt-4o-mini or gpt-5.6-luna | 0.15 / 0.60 or 0.20 / 1.20 | ~$0.002 | Cheap, fast, JSON mode |
| Final rubric eval | **gpt-4.1-mini** | 0.40 / 1.60 | ~$0.002 | Stricter schema; still cents |
| Realtime conversation | gpt-realtime-2.1 / mini | audio 32/64 or 10/20 | see S2S stack | WebRTC S2S; 60 min session |
| Live session (minute) | **gpt-live-1** | **$0.05 / min** | **$0.25 / 5 min** | **Pick for <500 ms feel** |
| Live session (audio) | Gemini 3.8 Live | $0.005 in + $0.018 out / min | ~$0.12 / 5 min | Cheaper S2S; 1.18 s published TTFA |
| Indic chat (text) | sarvam-105b | ₹29.28 / ₹73.2 per 1M | cents | `sarvam-m` is **deprecated** |

Official OpenAI price page 22 Sep 2026 lists gpt-5.6-luna ($0.20/$1.20), gpt-realtime-2.1 audio $32/$64 per 1M, gpt-realtime-2.1-mini $10/$20, gpt-live-1 $0.05/min billed per second. gpt-4o-mini $0.15/$0.60 and gpt-4.1-mini $0.40/$1.60 still quoted Aug 2026 — use luna if 4o-mini is unset. Gemini 3.8 Live (15 Sep 2026): $3/$12 per 1M audio tokens, also listed as $0.005/$0.018 per minute.

### Sarvam AI — India speech stack, not a native examiner

Researched **22 Sep 2026** from docs.sarvam.ai, sarvam.ai/api-pricing, and the Aug 2026 changelog.

| Item | What they ship |
| --- | --- |
| Products | `saaras:v3` / `saaras:v3-realtime` STT · `saarika:v2.5` legacy STT · `bulbul:v3` TTS · `sarvam-105b` / `sarvam-30b` chat. **`sarvam-m` rejected by the API.** |
| India | Bengaluru company. **All processing in India.** VPC / on-prem / SageMaker self-host. SOC 2 + ISO 27001 claimed. |
| Indic | STT: 22 scheduled + English, native Hinglish/Tanglish. TTS: 11 langs (en-IN, hi, ta, te, kn, mr, bn, ml, gu, pa, or). |
| Latency | STT Fast mode **<150 ms first token**. TTS **<250 ms first-byte** over `wss://api.sarvam.ai/text-to-speech/ws`. These are **component** numbers, not conversational TTFA. |
| Stream vs batch | Realtime WS (partials, VAD, mid-call reconfig) · legacy WS (finals only) · REST ≤30 s · Batch ≤2 h. |
| API | REST + **WebSocket**. No public WebRTC. **No native speech-to-speech model.** Voice agents are a cascade (their own SLNG story says so). |
| Full duplex | No. Barge-in is **client-side**: stop player, close TTS socket, open a new one. No in-band cancel. |
| Session | Realtime STT is continuous. TTS idle socket dies at **~1 min** (send `ping`). Managed Voice Agents product: **₹3.50/min** — chatbot/IVR, not an exam. |
| Examiner? | **No.** Excellent Indic ears and mouth. Asha's policy, bank tool, and rubric still have to live in our stack. |
| Price | STT **₹30/hour = ₹0.50/min ($0.006)**. TTS **₹30/10k chars**. 105B **₹29.28 / ₹73.2 per 1M**. |

**Where Sarvam wins:** India residency, Hinglish STT, Hindi TTS, cheaper STT than the old ₹1.50/min sheet, Pipecat/LiveKit ready. **Where it loses vs OpenAI Live:** no native S2S, so after-silence TTFA is still a cascade; no full-duplex; Voice Agents will answer off-curriculum unless we bolt on the same examiner contract.

### Bodhan AI — public API exists, not a viva product

Bodhan (IIT Madras / AI4Bharat / NVIDIA) publishes OpenAI-shaped APIs at `https://api.bodhan.ai/v1`. Docs: console.bodhan.ai/api-docs.

| Item | What they ship |
| --- | --- |
| Products | `indic-transcribe` · `indic-speak` · `indic-translate` · `indic-ocr`. Plus **Student Tutor Bot** and **Teacher Assistant Bot** as education products — those are chat tutors, not a public viva session API. |
| India | Sovereign / India-hosted. Open weights on Hugging Face. |
| Indic | 22–25 languages + English (hi, ta, te, kn, mr, bn, and more). |
| Latency | TTS **~200 ms time to first audio** on a **clip**. No published conversational TTFA. |
| Stream vs batch | **REST only.** STT accepts **≤30 s**. TTS: “a sentence or two, about 30 seconds.” Longer audio is rejected, not chunked. |
| API | REST. No WebSocket, no WebRTC, no session object. |
| Full duplex | No. |
| Limits | `indic-transcribe` **8 RPM** · `indic-speak` **4 RPM**. 429 + Retry-After. |
| Examiner? | **No.** There is no speech-to-speech viva, rubric, or live session endpoint. |
| Price | STT **₹0.10/min**. TTS **₹6/10k chars**. Cheapest Indic batch in this sheet. |

Use Bodhan for overnight bank-audio, gold-set transcription, or self-host if Legal mandates open weights. **Do not** point the CRT mic at it.

### Other Indic realtime (short)

| Vendor | Role | Latency published | Examiner? | Note |
| --- | --- | --- | --- | --- |
| **Smallest.ai Hydra** | Native S2S, waitlist | Marketing **<300 ms**; own bench **864 ms** median V2V | No | 15+ langs incl. hi/ta/te/kn/mr. India + SF. Watch, do not block MVP. |
| **Smallest Lightning** | Streaming TTS | **<100 ms** TTFB | n/a | Useful in a speculative cascade |
| **Gnani** Prisma/Timbre | India STT+TTS WS | STT p95 ~200 ms; TTS first-byte **<250 ms** | No | 10+ Indic; sales-quoted |
| **Reverie** | Telephony STT/TTS | “sub-second” STT; no public $ | No | 11+ Indic; custom quote |
| **Skit.ai** | Managed collections agent | “within a second” | No | Not a DIY viva API |
| **Sarvam+ElevenLabs hybrid** | Sarvam STT + EL Flash TTS | STT <150 ms + TTS ~75 ms inference | No | Still a cascade; EL $0.08/min Agents + LLM extra |

---

## 6. Indian language and accent

**MVP: English + Hinglish. Hindi Phase 2. Rest Phase 3.**

CRT faculty already run rooms in Indian English with Hindi mixed in. Scoring accent or forcing Devanagari on Day 1 will tank completion and reliability. Multilingual from day one is a science project.

| Language | MVP | STT plan | TTS plan | Notes |
| --- | --- | --- | --- | --- |
| Indian English | Yes — primary | Nova-3 mono or multi | Azure en-IN (Asha) | Accent must not score |
| Hinglish (code-mix) | Yes — accept | Nova-3 multilingual | Asha stays English | Answers like “need generation ka point…” are valid |
| Hindi | Phase 2 | Sarvam Saaras v3 | Sarvam Bulbul v3 | Same rubric, translated bank |
| Tamil / Telugu / Kannada | Phase 3 | Sarvam or Bodhan | Sarvam / Bodhan | Only if CRT localises |
| Marathi / Bengali / others | Phase 3 | Same | Same | Do not block MVP |

### Code-mix rules for the evaluator

Transcribe as mixed. Do **not** translate before scoring — translation drops product nouns (Math Champ, LSQ, Foundation). The rubric matches concepts, not wording.

### Why not Hindi on day one

The 500 ms bar is an English+Hinglish S2S problem first. Sarvam STT is now **₹0.50/min** (docs, Sep 2026) — cheaper than the old ₹1.50/min sheet — but the Hindi bank must still be dual-authored or you score translations of hallucinations. Ship English+Hinglish S2S, measure WER on a 200-clip gold set of IL sales trainees, then add Hindi (Sarvam ears/mouth) when Saaras WER on that set is ≤12% and the Hindi bank is faculty-reviewed.

### In-India processing

OpenAI Live processes outside India. **Azure `gpt-realtime-2.1` lists South India.** Azure Central India exists for Speech. Gemini Live on Vertex India is a procurement question. Sarvam and Bodhan process in India. For CRT training audio (not school-child PII) US S2S is acceptable in MVP with a DPA + 30-day deletion. If Legal treats trainee voice as sensitive HR data, pick Azure South India realtime first — do not drop S2S for Bodhan clips.

Navana Bodhi is telephony-first STT, not a viva stack. Bhashini is procurement-heavy. Do not block MVP on either.

---

## 7. Latency budget — India production

Ship against **two clocks**. The hard product bar is **perceived <500 ms**.

| Clock | Definition | Hard bar |
| --- | --- | --- |
| **Perceived / barge-in TTFA** | First audible Asha sample after the learner *intends* to finish (overlap allowed; model may start while they trail off) | **p50 ≤ 500 ms** |
| **After-silence TTFA** | VAD / EndOfTurn → first audible sample | Log it. Published S2S sits **0.8–1.2 s**. Do not fail the launch solely on this clock if perceived is green. |
| **TTS first-byte** | Text already in hand → first audio | Diagnostic only. Easy <200–250 ms. |

### What vendors actually publish (22 Sep 2026)

| Vendor | Number | What it is |
| --- | --- | --- |
| Azure GPT Realtime | WebRTC **~100 ms** · WebSocket **~200 ms** | Microsoft connection-method table. Not “after 400 ms of silence.” |
| OpenAI Realtime (independent, US-East WebRTC, `gpt-4o-realtime`) | **232 ms p50 / 281 ms p95** | Ken Imoto, 50 turns, same script. Under 300 ms. |
| Gemini Live (same bench) | **250 ms p50 / 295 ms p95** | Same methodology. |
| OpenAI `gpt-live-1` | **0.798 s** turn-taking | Full Duplex Bench vs 1.41 s for `gpt-realtime-2.1`. |
| OpenAI `gpt-realtime-2` / 2.1 | **1.12 s** minimal · **2.33 s** high reasoning | Artificial Analysis Big Bench Audio. |
| Gemini 3.8 Live | **1.18 s** TTFA · Extended Thinking **1.35 s** | Independent (developersdigest, Sep 2026). |
| Agora on ChatGPT GPT-Live (app, not API) | **~1.1 s** last-speech-frame → first audio | Different product surface. |
| Smallest Hydra | Marketing **<300 ms** · own bench **864 ms** median V2V | Waitlist. Do not plan CRT on it. |
| Sarvam | STT Fast **<150 ms** first token · TTS **<250 ms** first-byte | Components. Add LLM + EOU and you are back in cascade math. |
| Deepgram Flux | **~260 ms p50** EndOfTurn; `EagerEndOfTurn` starts the LLM early | The speculative-cascade lever. |
| Cartesia Sonic 3.5 | **~40 ms** Turbo claimed · **~166–190 ms** measured | Fastest TTS chunk, not E2E. |
| ElevenLabs Flash | **~75 ms** model inference | Docs are explicit: TTFA is larger. |
| Bodhan | **~200 ms** TTS first audio | Clip REST. |

India last-mile adds RTT on US vendors. Azure **South India** (`gpt-realtime-2` / `2.1`) is the published in-region S2S. OpenAI direct has no India region. Gemini Live is WebSocket (partners add WebRTC); Vertex India routing is a procurement question.

### Architecture B — why this is the 500 ms path

Native S2S does not wait for STT-final + LLM-TTFT + TTS-init. Full duplex (`gpt-live-1`) listens while it talks. Azure's published WebRTC hop is ~100 ms. Independent US benches already sit under 300 ms p50. That is the stack you ship when 500 ms is hard.

### Architecture C — milliseconds if we fall back (or go speculative)

| Component | Mumbai optimistic (ms) | India typical (ms) | Speculative (Flux EagerEOT + Cartesia/Sarvam) |
| --- | --- | --- | --- |
| VAD / EOU | 400 | 500 | **0–150** (eager start before final) |
| STT finalize | 180 | 250 | overlapped |
| Net RTT | 40 | 180 | 40 if India colo |
| LLM TTFT | 250 | 350 | 150–250 (small model, streamed) |
| TTS first byte | 100 | 150 | 40–250 |
| Jitter buffer | 60 | 80 | 40 |
| **Sum (after-silence TTFA)** | **1,030 ms** | **1,510 ms** | **~400–800 ms aim** |

VAD silence is a product choice (400 ms) on a conservative cascade. Speculative cascade **starts TTS before STT final**. That is the only honest way a cascade approaches 500 ms. It needs India colo (Mumbai/Hyderabad) for Deepgram+LLM+TTS, or Sarvam in-India for STT+TTS plus an India-region LLM. Budget **400–800 ms**, not 200 ms.

| Architecture | Perceived p50 | After-silence p50 | Feels like |
| --- | --- | --- | --- |
| A batch file cascade | 3.5 s | 3.5–6.0 s | IVR. Do not ship. |
| C hybrid stream (fallback) | 1.5 s | 1.4–2.2 s | Phone viva with a short think |
| C speculative (India colo) | 0.5–0.8 s | 0.4–0.8 s | Close, if Legal refuses US S2S |
| **B native S2S (pick)** | **<500 ms target** | 0.8–1.2 s published | Human examiner overlap |

### SLOs (latency-first)

| Metric | Target | Breach |
| --- | --- | --- |
| Perceived TTFA p50 | **≤ 500 ms** | > 700 ms for a day |
| Perceived TTFA p95 | **≤ 800 ms** | > 1.2 s |
| After-silence TTFA p50 | ≤ 1.0 s (log) | > 1.5 s |
| Turn error rate | < 2% | empty audio + 5xx + WS drop |
| Barge-in stop | **≤ 200 ms** (S2S native) | Asha talks over the learner |

Eval LLM runs after the turn is committed, **off the audio path**. Final rubric can take 1–2 s at hang-up; the learner already hears “that is the end of today’s viva.”

---

## 8. Unit economics

FX **₹84 / USD**. One viva per learner per learning day. Numbers below include a **15% buffer** on metered APIs for repeats / “please repeat”.

Assumptions for 5-min: 2.2 min student STT, 6,000 examiner chars TTS, LLM 8k in / 1.2k out.  
Assumptions for 10-min: 4.2 min STT, 12,000 chars TTS, LLM 14k / 2k.  
Infra includes 30-day opus audio, Redis state, logs.

### Cost per viva by stack

| Stack | 5-min | 10-min | Perceived TTFA | Role |
| --- | --- | --- | --- | --- |
| A · Lowest viable cascade | $0.13 (₹11) | $0.26 (₹22) | 1.6–2.4 s | Austerity |
| C · Balanced cascade | **$0.15 (₹13)** | **$0.29 (₹24)** | 1.4–2.2 s | **Low-cost fallback** |
| **B1 · gpt-live-1 (pick)** | **$0.30 (₹25)** | **$0.58 (₹49)** | **<500 ms target** | **MVP if 500 ms is hard** |
| B2 · Gemini 3.8 Live | $0.18 (₹15) | $0.34 (₹29) | benches ~250 ms p50 US | Cheaper S2S |
| B3 · Azure realtime-2.1 South India | ~$0.28–0.40 | ~$0.55–0.75 | WebRTC ~100 ms hop | Residency + S2S |

### Balanced 5-minute bill of materials

| Line | Meter | USD | INR |
| --- | --- | --- | --- |
| STT Deepgram Nova-3 | 2.2 min × $0.0077 | 0.017 | 1 |
| TTS Azure Neural en-IN | 6,000 chars × $16/1M | 0.096 | 8 |
| Turn LLM gpt-4o-mini / luna | 8k in / 1.2k out | 0.002 | 0 |
| Eval gpt-4.1-mini | final JSON | 0.002 | 0 |
| Bank share | 24 Qs/day, weekly regen | 0.003 | 0 |
| Infra + 30-day audio + logs | Redis, S3-class, Socket.IO | 0.010 | 1 |
| 15% repeat / barge-in buffer | on metered APIs | 0.020 | 2 |
| **Total (rounded)** | production planning | **0.15** | **13** |

10-min balanced cascade: 4.2 min STT ($0.032) + 12k chars TTS ($0.192) + LLM $0.008 + infra $0.016 + bank $0.003 + buffer ≈ **$0.29 (₹24)**.

Share of the cascade 5-min rupee: TTS ~64%, buffer + infra ~20%, STT ~11%, LLM + bank ~5%. Cut cascade cost by shortening Asha.

### gpt-live-1 5-minute bill of materials (pick)

| Line | Meter | USD | INR |
| --- | --- | --- | --- |
| gpt-live-1 voice session | 5.0 min × $0.05 | 0.250 | 21 |
| Backend tool / follow-up (luna or 4o-mini) | small; often cached | 0.003 | 0 |
| Eval gpt-4.1-mini | final JSON, off-path | 0.002 | 0 |
| Bank share | 24 Qs/day, weekly regen | 0.003 | 0 |
| Infra + 30-day audio + logs | Redis, S3-class, Socket.IO | 0.010 | 1 |
| 15% repeat / barge-in buffer | on metered APIs | 0.038 | 3 |
| **Total (rounded)** | production planning | **0.30** | **25** |

Gemini 3.8 Live 5-min: ~$0.023/min audio × 5 = $0.115 + eval/infra/buffer ≈ **$0.18 (₹15)** — same rupee as the old cascade, with S2S feel. Use if OpenAI minute-rate is the blocker.

**vs the old $0.15 cascade:** `gpt-live-1` is **~2×** ($0.30). Gemini Live is **~1.2×** ($0.18). You are buying the 500 ms clock, not prettier TTS.

### Volume (cascade fallback $0.15 — multiply ×2 for gpt-live-1)

| Volume | 5-min / day | 10-min / day | 5-min × 22d month | CRT batch (4 days, 5-min) |
| --- | --- | --- | --- | --- |
| 1,000 students/day | $150 (₹12,600) | $290 (₹24,360) | $3,300 (₹2,77,200) | $600 (₹50,400) |
| 10,000 students/day | $1,500 (₹1,26,000) | $2,900 (₹2,43,600) | $33,000 (₹27,72,000) | $6,000 (₹5,04,000) |
| 100,000 students/day | $15,000 (₹12,60,000) | $29,000 (₹24,36,000) | $3,30,000 (₹2,77,20,000) | $60,000 (₹50,40,000) |

CRT today is 4 days / 26 sessions. A 1,000-learner batch of 5-min **cascade** vivas is **$600 (₹50,400)**. The same batch on **gpt-live-1** is **$1,200 (₹1,00,800)**. 100k/day is a national-scale program, not this LMS's current CRT.

Per learner / 4-day CRT (5-min): cascade **$0.60 (₹50)** · gpt-live-1 **$1.20 (₹101)** · Gemini Live **$0.72 (₹60)**.  
Per learner / 22-day month (5-min): cascade **$3.30 (₹277)** · gpt-live-1 **$6.60 (₹554)**.

Extra workers at 100k concurrent-ish closes: +$800–2,000/month Socket.IO / Redis — under 2% of the API bill. Vector DB is not required in MVP (day corpus is small). No RAG tax.

---

## 9. Metrics

Instrument on day one; do not wait for a BI project.

### Product

| Metric | Formula | Target | Why |
| --- | --- | --- | --- |
| Completion | ended_with_result / started | ≥ 85% | Silence + latency kill this first |
| Drop-off | 1 − completion | ≤ 15% | By minute and by question index |
| Duration | mean(ended_at − started_at) | 5.5–6.5 min | Clock drift = too many follow-ups |
| Stems answered | mean stems with score | ≥ 4.5 / 5 | Skips from STT or silence |
| Retry rate | attempt≥2 / learners who started | ≤ 25% | Hard exam or bad audio |
| CSAT 1–5 | optional 1-tap after result | ≥ 3.8 | Asha tone check |
| Perceived TTFA | barge-in / overlap clock | **p50 ≤ 500 ms** | Hard feel bar |

### Learning

| Metric | Formula | Target | Why |
| --- | --- | --- | --- |
| Mean overall | avg(overall) | 65–80 | Outside = bank too easy/hard |
| Concept mastery | % concepts ≥70 | rising day-over-day | Feeds revision list |
| Score delta | day N − day 1 (same member) | +5 pts by day 4 | Is CRT working |
| Follow-up success | follow-up≥70 / follow-ups | ≥ 45% | Probes should teach a little |
| Revision follow-through | revisited weak lesson / flagged | ≥ 40% | Else the flag is theatre |

### AI quality

| Metric | Formula | Target | Why |
| --- | --- | --- | --- |
| Relevance | faculty: on-day / sampled Qs | ≥ 95% | Off-syllabus kills trust |
| Duplicate stems | exact+near dup in a batch day | < 8% | Hostel leak |
| Hallucination | Q not grounded in day sources / sampled | < 2% | Hard gate |
| Human agreement | QWK vs faculty on gold | ≥ 0.65 launch / 0.75 steady | See §10 |
| False pass | AI≥60 & human<50 / pairs | < 8% | Certification risk |
| False fail | AI<60 & human≥70 / pairs | < 10% | Attrition risk |
| Follow-up relevance | faculty binary | ≥ 90% | No random tangents |

### Speech and system

| Metric | Formula | Target | Why |
| --- | --- | --- | --- |
| WER Indian English | edit distance / words on gold | ≤ 12% | Below this, eval is guessing |
| STT empty rate | turns with blank text / turns | < 3% | Mic + VAD |
| Silence skips | auto-skip / stems | < 10% | Thinking time too tight? |
| Language detect | en vs hi-mix vs other | ≥ 90% on mix clips | Routing |
| Perceived TTFA p50 / p95 | barge-in / overlap clock | **500 ms / 800 ms** | Hard feel bar |
| After-silence TTFA p50 | VAD end → first audio | ≤ 1.0 s (log) | Do not mix with perceived |
| API uptime blended | successful turns / attempts | 99.5% | Multi-vendor fallback |
| Cost / session | sum vendor + infra | ≤ $0.35 5-min S2S · ≤ $0.18 cascade | Alert at $0.45 / $0.22 |

---

## 10. Evaluation accuracy benchmark

Do not go live on a vibe. Double-score a gold set the way a board exam anchors markers.

| Bar | Number |
| --- | --- |
| MVP gold answers | **200** (not 500) |
| Min quadratic weighted kappa | **0.65** |
| Max mean score error | **±8 pts** |

500 double-scored vivas is right before we let scores touch a certificate. For a same-day CRT training gate, 200 answers (≈40 sessions × 5 stems) across 2 faculties and 2 days of content is enough to catch a broken rubric. Collect the rest in shadow mode.

### Protocol

1. **Record** — Opus of every MVP beta viva; consent in Hello ILians update.
2. **Blind mark** — Two CRT faculties score stems 0/40/70/100 from transcript + audio.
3. **Adjudicate** — If |F1−F2| > 30, a lead marks a third; that is the gold.
4. **AI mark** — Frozen `prompt_rev` asha-vN; no peeking at gold.
5. **Compare** — QWK, Pearson r, mean signed error, false pass/fail.
6. **Ship bar** — QWK ≥ 0.65, |MSE| ≤ 8, false pass < 8%, false fail < 10%.
7. **Hold** — If false pass ≥ 8%, do not unlock next day on AI score.

### Continuous calibration

Every week sample 40 new stems (stratified by day and band). If QWK drops below 0.60, freeze prompt changes and roll back `prompt_rev`. Retrain nothing — this is prompt + bank maintenance. Faculties get a `/viva-review` queue, not a spreadsheet.

Shadow mode for the first CRT batch: AI score is stored but the lock uses “viva completed” only. Turn on score-gated Ready after the 200-pair bar is met.

---

## 11. Assessment integrity — light touch

CRT joiners sit in PGs with notes on the second screen. We do **not** ship webcam proctoring, room scan, or keyloggers. We make the leaked-PDF strategy expensive.

| Control | How | Invasiveness |
| --- | --- | --- |
| Random draw | member+attempt hash into 24-Q bank | None |
| No shared sequence | Concept order shuffled | None |
| Live follow-up | Cannot pre-write the probe | None |
| Scenario mutation | Parent name, class, objection rotate | None |
| Read-aloud detector | Very low pause variance + high token overlap with lesson body → flag, do not auto-zero | Low |
| Long pause | Already in product rules; not a cheat signal alone | None |
| Second attempt new draw | Never the same five stems | None |
| Tab-idle | Existing heartbeat; pause timer if tab hidden > 8 s | Low |
| Type fallback abuse | Cap 400 chars; still scored; TM can see | None |

**Do not build:** face match, eye tracking, always-on screen share, or device fingerprint theatre. This is internal sales training. Integrity failures become a TM conversation, not a police action.

---

## 12. LMS technical architecture

Frappe LMS + Vue SPA already running. Course slug `sales-crt`. Persistence is MariaDB + Redis + DocTypes. Do not add a sidecar app for MVP.

### Lock chain after viva

```
Hello ILians (unchanged)
  → CRT day 1 lessons (lesson_locking)
  → Viva day 1 (/viva/1)
  → CRT day 2…N (same pattern)
  → Viva day N (/viva/:n)
  → Training eval (existing)
  → OJT sim (existing)
  → Certificate (existing)
```

### New DocTypes (mirror OJT, do not overload it)

| DocType | Grain | Key fields |
| --- | --- | --- |
| Sales Viva Settings | Singleton | persona_rev, duration_sec, pass_mark, ready_mark, stt_vendor, tts_vendor |
| Sales Viva Blueprint | course × day_number × bank_version | source_hash, status (Draft/Live), generated_at |
| Sales Viva Question | child of Blueprint | q_id, concept_id, level, stem, model_answer, alternates[], followup_hint, source_session |
| Sales Viva Session | member × day × attempt | status, started/ended, overall, band, result_json, audio_url, prompt_rev |
| Sales Viva Turn | child of Session | role, text, audio_url, q_id, score, reason, stt_ms, llm_ms, tts_ms |
| Sales Viva Score | child of Session | concept_id, score, weak, revision_lesson |

### APIs — `lms.lms.sales_viva`

| Method | Role |
| --- | --- |
| `get_day_state(day_number)` | Lock, progress, last result — like `get_crt_detail` |
| `start_session(day_number)` | Create Session, draw 5 questions, return greeting TTS URL |
| `submit_turn(session, transcript \| audio_ref)` | HTTP fallback; primary path is Socket.IO |
| `complete_session(session)` | Run eval LLM, write JSON + children, set lock |
| `get_result(session)` | Learner + TM view |
| `generate_bank(day_number)` | Moderator / cron after `import_schedule` |
| `review_queue()` | Faculty gold-set marking |

### Vue

Add `path: '/viva/:dayNumber'`, name `SalesViva`, next to `/crt/:crtNumber` (SalesCRT) and `/ojt/:scenarioKey`. CRT detail CTA: “Start today’s viva” only when `get_day_state.unlocked`. Reuse the OJT sim chrome (timer, transcript rail, end screen) — different engine.

### Audio path (keep Frappe thin)

**S2S (pick):** Browser opens **WebRTC** to OpenAI `/v1/realtime` or Azure `/openai/v1/realtime/calls` with a 60-second ephemeral token from `start_session`. Vue plays remote audio natively. Transcripts (`response.output_audio_transcript.delta` / equivalent) POST to Frappe. Frappe never transcodes. Redis key `viva:{session}` holds `remaining_ms`, `followups_used`, `asked_ids`, `current_q`. Asha calls tool `get_next_stem` → Frappe returns the next bank item only.

**Cascade fallback:** Browser streams opus to Deepgram (or Sarvam `saaras:v3-realtime`) with the same token pattern. Frappe (or the browser) calls streaming TTS and pushes chunks on existing Socket.IO (`:9000`).

**Reuse:** `lesson_locking`, `sales_journey._crt_states`, heartbeat, enrollment auto-create, staff skip, MariaDB, Redis, Socket.IO, CRT Excel import hook.

**Do not add in MVP:** Vector DB, separate Node voice server, our own WebRTC SFU, Hindi UI, webcam proctor, RAG over the whole LMS. Vendor WebRTC is fine — we are not standing up an SFU.

### Question feed

`import_schedule` already writes Sales CRT Session + Course Lesson + content_links. After a successful import, enqueue `generate_bank` per distinct `day_number` (today: 4 days, 26 sessions). Skip `session_type` in break, lunch. Pull `lesson.body` and link titles. Store `source_hash` so a re-import only regenerates changed days.

---

## 13. MVP vs later

### Phase 1 — MVP (6–8 weeks)

- [x] English + Hinglish, Asha, 6-min, 5+2 questions
- [ ] Hybrid bank + live follow-ups, day-scoped
- [ ] **Arch B:** `gpt-live-1` (or Azure `gpt-realtime-2.1` South India) WebRTC + tool-fetched stems
- [ ] Async `gpt-4.1-mini` rubric on transcript (voice model does not grade)
- [ ] DocTypes + `lms.lms.sales_viva` + `/viva/:dayNumber`
- [ ] Sequential lock after day's lessons; 1 retry
- [ ] JSON rubric; confidence/accent excluded
- [ ] TM result view (not a full analytics suite)
- [ ] 200-answer shadow benchmark before score-gating
- [ ] Keep Arch C cascade wired as **budget fallback** (feature flag)

**In:** type fallback, native barge-in, 30-day audio, cost alert, perceived-TTFA telemetry.  
**Out:** Hindi UI, webcam, cross-day memory, certificate coupling, vector RAG, custom cloned voice, Bodhan on the live path.

### Phase 2

Hindi track (**Sarvam** `saaras:v3-realtime` + `bulbul:v3`, or S2S if Gemini/OpenAI Hinglish WER holds), faculty review queue, 500-pair calibration, concept mastery dashboard, 10-min optional, score-gated Ready.

### Phase 3

More Indic (ta/te/kn/mr/bn) via Sarvam overlay, optional Bodhan self-host if Legal mandates open weights, Smallest Hydra if it exits waitlist under 500 ms on our gold set.

### Engineering shape

Three people, 6–8 weeks: Frappe DocTypes + APIs + lock hook + `get_next_stem` tool; Vue viva page + **WebRTC** client; speech vendor glue + Asha prompt pack; 1 week overlapping faculty gold-set. Local stack already up — build against `sales.localhost`, no TM sheet required.

---

## 14. Vendor shortlist and three stacks

| Component | Provider | Model / API | Latency | Accuracy | Indic | Est. cost | Integrate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S2S (pick) | OpenAI | **gpt-live-1** | 0.798 s turn-taking; US WebRTC benches ~232 ms p50 | Natural + full duplex | Fair Hinglish | **$0.05/min** | WebRTC |
| S2S residency | Azure | gpt-realtime-2.1 South India | WebRTC **~100 ms** hop | Same family | Fair Hinglish | token $32/$64 audio | WebRTC |
| S2S cheap | Google | Gemini 3.8 Live | 1.18 s pub · ~250 ms US bench | Strong | en-IN, hi, ta, te, kn, mr, bn | $0.005+$0.018/min | WSS (partners: WebRTC) |
| STT fallback | Deepgram | Nova-3 / Flux | partials <300 ms; Flux EOT ~260 ms | Best IN-EN/$ | Multi / Hinglish | $0.0077 / $0.0065 | WS |
| STT IN | Sarvam | `saaras:v3-realtime` | Fast **<150 ms** first token | Best Hinglish | 22 langs | **₹0.50/min** | WS, India |
| STT IN | Bodhan | indic-transcribe | clip, not live | Untested here | 22 langs | ₹0.10/min | REST, 30 s |
| LLM eval | OpenAI | gpt-4.1-mini | 1–2 s off-path | Better schema | n/a | cents | JSON mode |
| TTS fallback | Azure | Neural en-IN stream | 120–250 ms | Exam-credible | hi-IN later | $16/1M | SDK |
| TTS alt | Cartesia | Sonic 3.5 | 40–90 ms claimed / ~170 ms meas. | Agent-natural | 42 langs | ~$35–50/1M | Speculative cascade |
| TTS IN | Sarvam | Bulbul v3 | **<250 ms** | Best Hindi | 11 langs | ₹30/10k | Phase 2 |

### Stack A — Lowest viable cascade · $0.13 / $0.26

gpt-4o-mini-transcribe → gpt-4o-mini (all LLM) → Azure Neural en-IN. After-silence TTFA 1.6–2.4 s. **Fallback only.**

### Stack C — Balanced cascade (FALLBACK) · $0.15 / $0.29

Deepgram Nova-3 / Flux → gpt-4o-mini/luna turn → gpt-4.1-mini eval → Azure Neural en-IN (or Cartesia / Sarvam if we speculate).  
**$0.15 (₹13) / 5-min, $0.29 (₹24) / 10-min. Typical India TTFA 1.4–2.2 s.** Speculative + India colo: aim 400–800 ms.

Keep this wired. It is the stack if Finance refuses S2S. It is **not** the 500 ms target.

### Stack B — Native S2S (PICK) · $0.30 / $0.58 on gpt-live-1

**OpenAI `gpt-live-1` WebRTC** (or Azure `gpt-realtime-2.1` South India, or Gemini 3.8 Live) + tool `get_next_stem` + `gpt-4.1-mini` eval on the transcript.

**$0.30 (₹25) / 5-min, $0.58 (₹49) / 10-min** on live-1. Gemini Live ~**$0.18 / $0.34**.

Wins the new priority order: conversational feel first, scores still auditable because the voice model does not grade. Indic weaker than Sarvam — add Sarvam in Phase 2, do not wait for Hindi to ship the viva.

---

## 15. Final recommendation

**Ship native S2S (Architecture B / Stack B), persona Asha.** Cascade (Architecture C / old Stack B) stays as the **low-cost fallback** behind a feature flag.

Priority: **(1) <500 ms feel** · **(2) assessment reliability** · **(3) Sarvam/Bodhan/Indic** · **(4) cost** · **(5) LMS**.

Student mic → **WebRTC `gpt-live-1`** (or Azure `gpt-realtime-2.1` South India) → Asha speaks from a **tool-fetched** day bank → transcript → **gpt-4.1-mini** rubric off-path → Vue `/viva/:dayNumber` → `lms.lms.sales_viva.*` → MariaDB + Redis + existing Socket.IO.

---

### Latency-first architecture (sub-500 ms)

**Can we hit <500 ms TTFA?** Yes — on the **barge-in / overlapping** definition, with **native speech-to-speech**. That is the clock the learner feels. After a **clean silence**, published S2S numbers are **0.8–1.2 s**; we log that clock and do not pretend a cascade will beat it.

| Definition | Hit <500 ms? | Evidence (22 Sep 2026) |
| --- | --- | --- |
| TTS first-byte (text already ready) | Yes, easy | Cartesia ~40–90 ms claimed; Sarvam Bulbul <250 ms; ElevenLabs Flash ~75 ms **inference** |
| Perceived / barge-in (model starts as they trail off) | **Yes — this is the target** | Azure WebRTC **~100 ms**. Independent US-East: OpenAI Realtime **232 ms p50 / 281 ms p95**; Gemini Live **250 ms p50**. `gpt-live-1` is full-duplex. |
| After-silence EOU (STT-final + LLM + TTS) | Not as a published OpenAI/Gemini EOU number | `gpt-live-1` **0.798 s** turn-taking; Gemini 3.8 Live **1.18 s**; `gpt-realtime-2.1` **1.12 s** minimal. Cascade India **1.4–2.2 s**. |

**Recommended stack if latency is hard**

| Role | Pick | Why |
| --- | --- | --- |
| Primary examiner voice | **OpenAI `gpt-live-1` WebRTC** | Full duplex, $0.05/min, 0.798 s published turn-taking, 60 min session, interrupt native. English + Hinglish MVP. |
| If Legal wants India residency without leaving S2S | **Azure `gpt-realtime-2.1` WebRTC, South India** | Same family. Microsoft publishes **~100 ms** WebRTC. Region exists. |
| If minute-rate is the blocker | **Gemini 3.8 Live** | ~$0.023/min audio, 70+ langs incl. hi/ta/te/kn/mr/bn, barge-in, 15 min audio session (extendable). |
| Indic overlay (Phase 2) | **Sarvam** `saaras:v3-realtime` + `bulbul:v3` | India-hosted. No native S2S — use as ears/mouth, not as the examiner brain. |
| Never on the live mic | **Bodhan** | REST, 30 s clips, 4–8 RPM. Batch / open-weights only. |

**Sarvam vs Bodhan vs OpenAI Realtime**

|  | OpenAI `gpt-live-1` / Azure realtime | Sarvam | Bodhan |
| --- | --- | --- | --- |
| Hits 500 ms feel | **Yes (S2S / WebRTC)** | No — cascade of STT+LLM+TTS | No — clip REST |
| Indic (hi, Hinglish, ta, te, kn, mr, bn) | Fair Hinglish; weak ta/te/kn | **Best** (STT 22, TTS 11) | Broad Indic, batch only |
| India residency | Azure South India yes; OpenAI no | **Yes, default** | **Yes** |
| Full duplex / interrupt | **Yes** | Client-side barge-in only | No |
| Examiner-suitable | **Yes, with prompt + bank tool + separate eval** | Components only; Voice Agents (₹3.50/min) are chatbots | Tutor bots exist; **no viva API** |
| Cost / 5-min viva | **$0.30 (₹25)** live-1 · ~$0.18 Gemini | Cascade-like if we assemble it; managed agent ₹3.50/min | Too cheap to matter — cannot run the session |

**Cost vs the old $0.15 cascade 5-min number:** live-1 is **2× ($0.30)**. Gemini Live is **~1.2× ($0.18)**. You are paying for the clock, not for prettier vowels.

**Keep assessment reliable (hard #2)**

1. **Examiner system prompt** — Asha: short, no teaching, no off-curriculum, no small-talk. Versioned on `Sales Viva Settings`.
2. **Tool `get_next_stem(day_number)`** — returns the next unseen bank item for that CRT day only. The voice model does not invent stems.
3. **Separate async evaluator** — `gpt-4.1-mini` scores the transcript against model answer + alternates. The voice model does **not** both chat and grade.
4. Shadow mode until QWK ≥ 0.65 on 200 pairs.

**If they refuse US S2S:** speculative cascade — Deepgram **Flux `EagerEndOfTurn`** + small LLM (luna / 4o-mini) + **Cartesia Sonic** or **Sarvam Bulbul** streaming TTS. Aim **400–800 ms**, not 200 ms. Requires **India colo** (Mumbai/Hyderabad) for Deepgram+LLM+TTS, or Sarvam in-India for speech plus an India-region LLM. Still keep the same bank tool + async eval.

**MVP path:** English + Hinglish **S2S** so the viva *feels* under 500 ms. **Sarvam Hindi in Phase 2**. Do not wait for Hindi to start. Do not put Bodhan on the mic.

### Vendor scorecard

| Vendor | TTFA published | Indic | Cost / min (voice) | Examiner-suitable | India data residency |
| --- | --- | --- | --- | --- | --- |
| **OpenAI gpt-live-1** | 0.798 s turn-taking; US WebRTC benches ~232 ms p50 | en + Hinglish fair | **$0.05** | **Yes + tools + eval** | No (US) |
| **Azure gpt-realtime-2.1** | WebRTC **~100 ms** hop | en + Hinglish fair | token; ~$0.05–0.08 equiv. | **Yes + tools + eval** | **South India** |
| **Gemini 3.8 Live** | 1.18 s pub; ~250 ms US bench | en-IN, hi, ta, te, kn, mr, bn | **$0.023** audio | Yes + tools + eval | Vertex India = ask |
| **Sarvam** Saaras+Bulbul | STT <150 ms · TTS <250 ms (**components**) | **22 / 11 langs, Hinglish** | STT ₹0.50 · TTS ₹3/1k | **Ears/mouth only** | **Yes** |
| **Bodhan** | ~200 ms TTS clip | 22 langs | STT ₹0.10 · TTS ₹0.60/1k | **No** | **Yes** |
| **ElevenLabs Agents** | Flash ~75 ms inference | Multilingual, not India-first | $0.08 + LLM | Chatbot platform | No |
| **Cartesia Sonic** | 40–90 ms TTS | 42 langs claimed | ~$0.03–0.05 / 6k chars | TTS only | No |
| **Deepgram Flux / Nova** | <300 ms partials; EOT ~260 ms | IN-EN + multi | $0.0065–0.0077 | STT only | No |
| **Smallest Hydra** | <300 ms claimed; 864 ms own V2V | 15+ incl. Indic | waitlist | Watch | India + SF |
| **Gnani / Reverie / Skit** | TTS <250 ms / “sub-second” / “<1 s” | Strong Indic | sales-quoted | No (not a viva API) | Yes |

### The chain, one line each

| Layer | Choice |
| --- | --- |
| Persona | Asha — examiner with coach warmth |
| Voice | `gpt-live-1` WebRTC (Azure South India realtime if residency wins) |
| Questions | Hybrid bank after CRT ingest; live follow-ups only |
| Scope | That day's Sales CRT Session + lesson + content links — via **tool**, not model memory |
| Lock | After day lessons complete; 1 retry; then unlock next day |
| Scoring | 35/20/20/15/10 — never confidence or accent — **async eval model** |
| Backend | Frappe 16, `lms.lms.sales_viva`, MariaDB, Redis |
| Frontend | `/viva/:dayNumber` WebRTC beside `/crt/:crtNumber` |
| Fallback | Arch C cascade $0.15 if S2S budget is refused |
| Indic | Sarvam Phase 2; Bodhan never on the live path |
| Effort | 6–8 weeks, 3 people, local `sales.localhost` first |

### Cost at a glance (₹84/USD)

|  | 5-min S2S (live-1) | 5-min Gemini Live | 5-min cascade fallback |
| --- | --- | --- | --- |
| One viva | **$0.30 (₹25)** | $0.18 (₹15) | $0.15 (₹13) |
| Learner / 4-day CRT | $1.20 (₹101) | $0.72 (₹60) | $0.60 (₹50) |
| 1k students × 4 CRT days | $1,200 (₹1,00,800) | $720 (₹60,480) | $600 (₹50,400) |

### Accuracy expectation

With a faculty-reviewed bank, a **tool-gated** stem, and a **separate** eval model: concept accuracy should match a lenient human marker on clear audio. Expect argument on partials (the 40 vs 70 band) — that is what the gold set is for. Do not promise inter-rater perfection. Do not let the voice model write its own marks.

### Major risks

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| S2S wanders off-curriculum | It is a chat model with a mic | Examiner prompt + `get_next_stem` tool + refuse free-form teaching |
| Voice model grades itself | Inflated, unauditable marks | Async `gpt-4.1-mini` only; transcript is the artefact |
| After-silence clock > 500 ms | People will say “you missed the bar” | Instrument **both** clocks; hold the launch on **perceived** p50 |
| India RTT on US OpenAI | p95 blows the feel | Azure South India realtime, or Gemini Vertex IN, or speculative Sarvam cascade |
| Hinglish WER | Wrong transcript → wrong score | Gold WER; type fallback; Sarvam STT overlay if S2S mix fails |
| S2S $ at 10k/day | 2× the old cascade | Gemini Live price path; cascade flag for low-stakes retries |
| Legal / residency | Voice leaving India | DPA + 30-day delete; Azure South India or Sarvam if required |
| Lock rage | Failing viva blocks CRT | Retry then unlock with flag — training, not boards |

### MVP success criteria

| Bar | Number |
| --- | --- |
| Completion | ≥ 85% |
| Perceived TTFA | **p50 ≤ 500 ms, p95 ≤ 800 ms** |
| After-silence TTFA | log; p50 ≤ 1.0 s |
| Human–AI QWK | ≥ 0.65 on 200 pairs |
| Cost | ≤ $0.35 (₹29) per 5-min S2S · cascade fallback ≤ $0.18 |
| Off-syllabus questions | < 2% of sampled stems |
| Accent/confidence in score | 0 — schema forbids it |

---

Start with native S2S so the viva feels live. Keep the cascade. Score meaning, not accent. Asha examines; she does not tutor. Frappe stays the system of record.
