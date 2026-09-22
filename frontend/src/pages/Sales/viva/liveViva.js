// Gemini Live voice viva engine (browser side).
//
// Streams the mic to Gemini Live as 16 kHz PCM, plays Asha's 24 kHz audio, relays her tool calls to
// Frappe, and measures how each answer is delivered: time to start speaking after Asha finishes the
// question, pauses, speaking time and tab switches. Turn-taking is ours (Gemini's own voice detection is
// off): a turn ends after a real pause, "I'm done", or releasing "Hold to talk".
// Audio pipeline and turn-taking by Saraga (see docs/AI_VIVA_PRD.md).

import { call } from 'frappe-ui'

const PCM_IN = 16000
const PCM_OUT = 24000
// Conversational pace: an answer ends after ~1.6 s of silence, and nobody gets long thinking time.
const VAD = {
	speechRms: 0.022,
	bargeRms: 0.038,
	bargeMs: 280,
	minSpeechMs: 1000,
	endSilenceMs: 1600,
	maxAnswerMs: 45000,
}
const NUDGE_AFTER_MS = 6000 // no answer yet: Asha prompts once
const MOVE_ON_AFTER_MS = 12000 // still nothing: recorded as no answer, next question
const PAUSE_MS = 2000

export function createLiveViva({ attempt, wsUrl, setup, timeLimitS, onChange }) {
	const s = {
		phase: 'connecting', // connecting | asha | listening | thinking | ending | done | error
		ws: null,
		micStream: null,
		micCtx: null,
		micNode: null,
		micSrc: null,
		playCtx: null,
		playAt: 0,
		playSources: [],
		ashaSpeaking: false,
		inActivity: false,
		holdMode: false,
		speechMs: 0,
		silenceMs: 0,
		bargeMs: 0,
		activityStartedAt: 0,
		ended: false,
		finishing: false,
		questionNumber: 0,
		questions: 5,
		ashaText: '',
		userText: '',
		error: '',
		repeatsLeft: 1,
		secondsLeft: timeLimitS,
		level: 0,
		timer: null,
		timeUpSent: false,
		m: freshMetrics(),
	}

	function freshMetrics() {
		return {
			askEndAt: 0, // when Asha finished saying the question (audio actually done playing)
			firstSpeechAt: 0,
			lastActivityEndAt: 0,
			think_ms: 0,
			answer_ms: 0,
			speech_ms: 0,
			pause_count: 0,
			longest_pause_ms: 0,
			tab_switches: 0,
			silentRun: 0,
			transcript: '',
			awaiting: false, // a question is open and we are waiting for the learner
			nudged: false,
			movedOn: false,
		}
	}

	const emit = () => onChange && onChange(snapshot())
	const snapshot = () => ({
		phase: s.phase,
		questionNumber: s.questionNumber,
		questions: s.questions,
		ashaText: s.ashaText,
		userText: s.m.transcript,
		error: s.error,
		secondsLeft: s.secondsLeft,
		level: s.level,
		repeatsLeft: s.repeatsLeft,
		holdMode: s.holdMode,
		inActivity: s.inActivity,
	})

	// ---------- audio helpers ----------
	const b64ToBytes = (b64) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))
	function bytesToB64(bytes) {
		let out = ''
		for (let i = 0; i < bytes.length; i += 0x8000) out += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000))
		return btoa(out)
	}
	function downsample(input, inRate, outRate) {
		if (inRate === outRate) return input
		const ratio = inRate / outRate
		const out = new Float32Array(Math.round(input.length / ratio))
		for (let i = 0; i < out.length; i++) {
			const start = Math.floor(i * ratio)
			const end = Math.min(Math.floor((i + 1) * ratio), input.length)
			let sum = 0
			for (let j = start; j < end; j++) sum += input[j]
			out[i] = sum / Math.max(1, end - start)
		}
		return out
	}
	function floatTo16(f32) {
		const out = new Int16Array(f32.length)
		for (let i = 0; i < f32.length; i++) {
			const v = Math.max(-1, Math.min(1, f32[i]))
			out[i] = v < 0 ? v * 0x8000 : v * 0x7fff
		}
		return out
	}
	function rms(f32) {
		let sum = 0
		for (let i = 0; i < f32.length; i++) sum += f32[i] * f32[i]
		return Math.sqrt(sum / Math.max(1, f32.length))
	}
	const send = (obj) => s.ws && s.ws.readyState === 1 && s.ws.send(JSON.stringify(obj))

	// ---------- playback ----------
	function playCtx() {
		if (!s.playCtx) {
			const Ctor = window.AudioContext || window.webkitAudioContext
			s.playCtx = new Ctor({ sampleRate: PCM_OUT })
			s.playAt = s.playCtx.currentTime
		}
		if (s.playCtx.state === 'suspended') s.playCtx.resume()
		return s.playCtx
	}
	function playPcm(u8) {
		const ctx = playCtx()
		const even = u8.byteLength - (u8.byteLength % 2)
		if (even < 2) return
		const int16 = new Int16Array(u8.buffer, u8.byteOffset, even / 2)
		const f32 = new Float32Array(int16.length)
		for (let i = 0; i < int16.length; i++) f32[i] = int16[i] / 32768
		const data = Math.abs(ctx.sampleRate - PCM_OUT) < 1 ? f32 : downsample(f32, PCM_OUT, ctx.sampleRate)
		const buf = ctx.createBuffer(1, data.length, ctx.sampleRate)
		buf.getChannelData(0).set(data)
		const src = ctx.createBufferSource()
		src.buffer = buf
		src.connect(ctx.destination)
		const at = Math.max(s.playAt, ctx.currentTime)
		src.start(at)
		s.playAt = at + buf.duration
		s.playSources.push(src)
		src.onended = () => {
			s.playSources = s.playSources.filter((x) => x !== src)
		}
	}
	function stopPlayback() {
		s.playSources.forEach((src) => {
			try {
				src.stop()
			} catch (e) {}
		})
		s.playSources = []
		if (s.playCtx) s.playAt = s.playCtx.currentTime
		s.ashaSpeaking = false
	}
	// Milliseconds of Asha's audio still queued to play.
	const queuedMs = () => (s.playCtx ? Math.max(0, (s.playAt - s.playCtx.currentTime) * 1000) : 0)

	// ---------- mic + turn-taking ----------
	async function openMic() {
		s.micStream = await navigator.mediaDevices.getUserMedia({
			audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
		})
	}
	function startActivity() {
		if (s.ended || s.inActivity) return
		const now = Date.now()
		s.inActivity = true
		s.speechMs = 0
		s.silenceMs = 0
		s.bargeMs = 0
		s.activityStartedAt = now
		const m = s.m
		if (m.awaiting) {
			if (!m.firstSpeechAt) {
				m.firstSpeechAt = now
				m.think_ms = m.askEndAt ? Math.max(0, now - m.askEndAt) : 0
			} else if (m.lastActivityEndAt) {
				// They stopped, Asha said "go on", they carried on: the gap is a pause in the answer.
				const gap = now - m.lastActivityEndAt
				if (gap >= PAUSE_MS) {
					m.pause_count += 1
					m.longest_pause_ms = Math.max(m.longest_pause_ms, gap)
				}
			}
		}
		send({ realtimeInput: { activityStart: {} } })
		s.phase = 'listening'
		emit()
	}
	function cancelActivity() {
		// A noise, not an answer: close the activity with Gemini but undo what it did to the metrics,
		// so the think-time clock and the nudge timer carry on as if it never happened.
		if (!s.inActivity) return
		s.inActivity = false
		s.holdMode = false
		const m = s.m
		if (m.awaiting && m.firstSpeechAt === s.activityStartedAt) {
			m.firstSpeechAt = 0
			m.think_ms = 0
		}
		send({ realtimeInput: { activityEnd: {} } })
		s.phase = 'listening'
		emit()
	}
	function endActivity() {
		if (!s.inActivity) return
		s.inActivity = false
		s.holdMode = false
		const now = Date.now()
		if (s.m.awaiting) {
			s.m.speech_ms += Math.round(s.speechMs)
			s.m.lastActivityEndAt = now
		}
		send({ realtimeInput: { activityEnd: {} } })
		s.phase = 'thinking'
		emit()
	}
	function startMicStream() {
		const Ctor = window.AudioContext || window.webkitAudioContext
		const ctx = new Ctor()
		s.micCtx = ctx
		if (ctx.state === 'suspended') ctx.resume()
		s.micSrc = ctx.createMediaStreamSource(s.micStream)
		const node = ctx.createScriptProcessor(4096, 1, 1)
		s.micNode = node
		let pending = []
		let pendingLen = 0
		const target = Math.floor(PCM_IN * 0.25)
		node.onaudioprocess = (ev) => {
			if (s.ended) return
			const input = ev.inputBuffer.getChannelData(0)
			const energy = rms(input)
			const dt = (input.length / ctx.sampleRate) * 1000
			s.level = Math.min(1, energy * 12)
			const ashaTalking = queuedMs() > 60
			if (ashaTalking && !s.inActivity && !s.holdMode) {
				s.bargeMs = energy >= VAD.bargeRms ? s.bargeMs + dt : 0
				if (s.bargeMs >= VAD.bargeMs) {
					stopPlayback()
					startActivity()
				} else return
			} else if (!s.inActivity && !s.holdMode) {
				if (energy >= VAD.speechRms) startActivity()
			}
			if (!s.inActivity) return
			if (energy >= VAD.speechRms) {
				if (s.m.awaiting && s.m.silentRun >= PAUSE_MS) {
					s.m.pause_count += 1
					s.m.longest_pause_ms = Math.max(s.m.longest_pause_ms, Math.round(s.m.silentRun))
				}
				s.m.silentRun = 0
				s.speechMs += dt
				s.silenceMs = 0
			} else {
				s.silenceMs += dt
				s.m.silentRun += dt
			}
			const held = Date.now() - s.activityStartedAt
			const ds = downsample(input, ctx.sampleRate, PCM_IN)
			pending.push(ds)
			pendingLen += ds.length
			// A cough, a chair scrape or Asha's own voice through the speakers can open a turn with
			// almost no speech in it. Without this the turn only ended at maxAnswerMs — up to 45
			// seconds of silence with "Listening" on screen and no nudge, because firstSpeechAt was
			// already set. Drop the turn instead and let the nudge timer take over again.
			if (!s.holdMode && s.silenceMs >= VAD.endSilenceMs && s.speechMs < VAD.minSpeechMs) {
				cancelActivity()
				pending = []
				pendingLen = 0
				return
			}
			const shouldEnd =
				!s.holdMode &&
				((s.silenceMs >= VAD.endSilenceMs && s.speechMs >= VAD.minSpeechMs) || held >= VAD.maxAnswerMs)
			if (pendingLen >= target || shouldEnd) {
				const merged = new Float32Array(pendingLen)
				let off = 0
				pending.forEach((p) => {
					merged.set(p, off)
					off += p.length
				})
				pending = []
				pendingLen = 0
				const pcm = floatTo16(merged)
				send({ realtimeInput: { audio: { data: bytesToB64(new Uint8Array(pcm.buffer)), mimeType: 'audio/pcm;rate=16000' } } })
			}
			if (shouldEnd) {
				// The trailing silence that ended the turn isn't a pause inside the answer.
				s.m.silentRun = 0
				endActivity()
			}
		}
		const mute = ctx.createGain()
		mute.gain.value = 0
		s.micSrc.connect(node)
		node.connect(mute)
		mute.connect(ctx.destination)
	}

	// ---------- tab switches ----------
	let lastSwitchAt = 0
	function countSwitch() {
		// One tab switch fires blur (while the tab is still visible) and then visibilitychange.
		// Counting both doubled the score penalty, so ignore a second signal within a second.
		const now = Date.now()
		if (now - lastSwitchAt < 1000) return
		lastSwitchAt = now
		s.m.tab_switches += 1
		emit()
	}
	function onVisibility() {
		if (document.hidden && s.m.awaiting && !s.ended) countSwitch()
	}
	function onBlur() {
		// Window focus lost without the tab hiding (e.g. another app over the browser).
		if (!document.hidden && s.m.awaiting && !s.ended) countSwitch()
	}

	// ---------- tools ----------
	async function runTool(fc) {
		const name = fc.name || ''
		let metrics = null
		if (name === 'commit_answer') {
			const m = s.m
			const now = Date.now()
			metrics = {
				think_ms: m.firstSpeechAt ? m.think_ms : m.askEndAt ? now - m.askEndAt : 0,
				answer_ms: m.firstSpeechAt ? now - m.firstSpeechAt : 0,
				speech_ms: m.speech_ms,
				pause_count: m.pause_count,
				longest_pause_ms: m.longest_pause_ms,
				tab_switches: m.tab_switches,
				transcript: m.transcript,
			}
		}
		try {
			const msg = await call('lms.lms.sales_viva.run_tool', {
				attempt,
				name,
				args: fc.args || {},
				metrics,
			})
			const result = (msg && msg.result) || {}
			s.questions = msg.questions || s.questions
			if (name === 'get_next_stem' && !result.error) {
				s.questionNumber = msg.question_number
				s.m = freshMetrics()
				s.m.awaiting = true
				s.repeatsLeft = 1
			}
			if (name === 'commit_answer' && result.ok) {
				// Answer accepted. A follow-up starts a new measurement window for the same question.
				s.m = freshMetrics()
				s.m.awaiting = Boolean(result.use_probe)
			}
			if ((name === 'finish_viva' && result.ok) || (msg && msg.done)) {
				s.ended = true
				// Scoring normally starts on Asha's next turnComplete. If that never arrives (her
				// closing line was interrupted, or the socket went quiet), the learner would sit on
				// "Listening" with a dead mic until the timer ran out, so close it ourselves.
				setTimeout(() => {
					if (!s.finishing) finish()
				}, 8000)
			}
			emit()
			return { id: fc.id, name, response: { result } }
		} catch (e) {
			return { id: fc.id, name, response: { error: (e && e.message) || 'tool failed' } }
		}
	}
	async function handleToolCall(toolCall) {
		const responses = []
		for (const fc of toolCall.functionCalls || []) responses.push(await runTool(fc))
		send({ toolResponse: { functionResponses: responses } })
	}

	// ---------- Gemini messages ----------
	function onServerMessage(msg) {
		if (msg.setupComplete) {
			startMicStream()
			s.phase = 'asha'
			emit()
			send({
				clientContent: {
					turns: [
						{
							role: 'user',
							parts: [{ text: 'Begin the viva. Greet me in one short sentence, then call get_next_stem and ask that question.' }],
						},
					],
					turnComplete: true,
				},
			})
			return
		}
		if (msg.toolCall) return handleToolCall(msg.toolCall)
		const sc = msg.serverContent
		if (!sc) return
		if (sc.interrupted) stopPlayback()
		if (sc.inputTranscription && sc.inputTranscription.text && s.m.awaiting) {
			s.m.transcript = `${s.m.transcript} ${sc.inputTranscription.text}`.replace(/\s+/g, ' ').trim()
			emit()
		}
		if (sc.outputTranscription && sc.outputTranscription.text) {
			s.ashaText += sc.outputTranscription.text
			emit()
		}
		if (sc.modelTurn && sc.modelTurn.parts) {
			if (s.phase !== 'asha') {
				s.phase = 'asha'
				s.ashaText = ''
			}
			s.ashaSpeaking = true
			sc.modelTurn.parts.forEach((p) => p.inlineData && p.inlineData.data && playPcm(b64ToBytes(p.inlineData.data)))
			emit()
		}
		if (sc.turnComplete) {
			s.ashaSpeaking = false
			// The question "ends" when her audio has actually finished playing, not when the text arrived.
			// A nudge doesn't restart the clock: think time runs from the end of the question itself.
			const endAt = Date.now() + queuedMs()
			if (s.m.awaiting && !s.m.firstSpeechAt && !s.m.askEndAt) s.m.askEndAt = endAt
			if (s.ended) {
				setTimeout(finish, queuedMs() + 600)
				return
			}
			setTimeout(() => {
				if (!s.inActivity && !s.ended) {
					s.phase = 'listening'
					emit()
				}
			}, queuedMs())
		}
	}

	function connect() {
		return new Promise((resolve, reject) => {
			const ws = new WebSocket(wsUrl)
			s.ws = ws
			let opened = false
			ws.onopen = () => {
				opened = true
				send({ setup })
				resolve()
			}
			ws.onerror = () => !opened && reject(new Error('Could not connect to the voice service.'))
			ws.onclose = () => {
				if (!s.ended && opened) fail('The voice connection dropped.')
			}
			ws.onmessage = (ev) => {
				const apply = (text) => {
					try {
						onServerMessage(JSON.parse(text))
					} catch (e) {}
				}
				if (ev.data instanceof Blob) ev.data.text().then(apply)
				else apply(ev.data)
			}
		})
	}

	// Silence before answering: prompt once, then move on. Timing is still recorded as think time.
	function checkSilence() {
		const m = s.m
		if (!m.awaiting || !m.askEndAt || m.firstSpeechAt || s.inActivity || s.ended || queuedMs() > 60) return
		const waited = Date.now() - m.askEndAt
		const say = (text) =>
			send({ clientContent: { turns: [{ role: 'user', parts: [{ text }] }], turnComplete: true } })
		if (waited >= MOVE_ON_AFTER_MS && !m.movedOn) {
			m.movedOn = true
			m.transcript = 'No answer'
			say(
				"(System: the learner did not answer within 12 seconds.) Say 'Okay, let's move on' and call commit_answer with complete true and transcript 'No answer'."
			)
		} else if (waited >= NUDGE_AFTER_MS && !m.nudged) {
			m.nudged = true
			say("(System: the learner hasn't started answering.) Prompt them in three or four words, e.g. 'Any thoughts?', then stop.")
		}
	}

	function tick() {
		checkSilence()
		s.secondsLeft = Math.max(0, s.secondsLeft - 1)
		if (s.secondsLeft === 0 && !s.timeUpSent) {
			s.timeUpSent = true
			send({ clientContent: { turns: [{ role: 'user', parts: [{ text: 'Time is up. Call finish_viva now and say goodbye in one sentence.' }] }], turnComplete: true } })
			setTimeout(() => !s.finishing && finish(), 15000)
		}
		emit()
	}

	// ---------- lifecycle ----------
	let onDone = null
	function cleanup() {
		clearInterval(s.timer)
		document.removeEventListener('visibilitychange', onVisibility)
		window.removeEventListener('blur', onBlur)
		stopPlayback()
		if (s.micNode) {
			s.micNode.onaudioprocess = null
			try {
				s.micNode.disconnect()
			} catch (e) {}
		}
		try {
			s.micSrc && s.micSrc.disconnect()
			s.micCtx && s.micCtx.close()
		} catch (e) {}
		if (s.micStream) s.micStream.getTracks().forEach((t) => t.stop())
		try {
			s.playCtx && s.playCtx.close()
		} catch (e) {}
		s.playCtx = null
		if (s.ws) {
			s.ws.onclose = null
			try {
				s.ws.close()
			} catch (e) {}
		}
	}
	async function finish(reason = 'finished') {
		if (s.finishing) return
		s.finishing = true
		s.ended = true
		s.phase = 'ending'
		emit()
		cleanup()
		try {
			const report = await call('lms.lms.sales_viva.finish_attempt', { attempt, reason })
			s.phase = 'done'
			emit()
			onDone && onDone(report)
		} catch (e) {
			fail((e && e.messages && e.messages[0]) || 'Could not save your viva. Please tell your trainer.')
		}
	}
	function fail(message) {
		s.error = message
		s.phase = 'error'
		emit()
		if (!s.finishing) {
			cleanup()
			call('lms.lms.sales_viva.finish_attempt', { attempt, reason: 'error' }).catch(() => {})
		}
	}

	return {
		async start(done) {
			onDone = done
			await openMic()
			try {
				await connect()
			} catch (e) {
				// The mic is already open at this point: without this the browser kept recording
				// (and the recording light stayed on) until the page was reloaded.
				cleanup()
				throw e
			}
			document.addEventListener('visibilitychange', onVisibility)
			window.addEventListener('blur', onBlur)
			s.timer = setInterval(tick, 1000)
			emit()
		},
		// "I'm done": end the answer now instead of waiting for the pause.
		done() {
			s.m.silentRun = 0
			endActivity()
		},
		holdStart() {
			s.holdMode = true
			stopPlayback()
			startActivity()
		},
		holdEnd() {
			s.holdMode = false
			s.m.silentRun = 0
			endActivity()
		},
		repeat() {
			if (s.repeatsLeft <= 0 || s.inActivity) return
			s.repeatsLeft -= 1
			// Restart the waiting clock. Without this the nudge and the 12-second "no answer" were
			// measured from the original question, so asking for a repeat could record "No answer"
			// the moment the repeat finished playing.
			s.m.askEndAt = 0
			s.m.nudged = false
			s.m.movedOn = false
			send({ clientContent: { turns: [{ role: 'user', parts: [{ text: 'Please repeat the current question once.' }] }], turnComplete: true } })
			emit()
		},
		stop: () => finish('left'),
		destroy: cleanup,
	}
}
