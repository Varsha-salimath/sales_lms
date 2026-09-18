/**
 * LMS auth UI for /login and /update-password (student.infinitylearn.com look).
 *
 * Loaded on every website page through web_include_js, so it exits immediately elsewhere.
 * On /login it only layers screen routing and button state on top of Frappe's login.js —
 * the login, forgot-password and email-link API calls stay Frappe's own.
 */
(function () {
	const path = document.body && document.body.dataset.path;
	if (path !== "login" && path !== "update-password") return;

	const SCREENS = {
		welcome: ".for-welcome",
		login: ".for-login",
		email: ".for-login",
		steptwo: ".for-login",
		forgot: ".for-forgot",
		login_with_email_link: ".for-login-with-email-link",
		signup: ".for-signup",
	};
	const BACK_TARGET = {
		login: "#welcome",
		login_with_email_link: "#welcome",
		forgot: "#login",
		signup: "#welcome",
	};
	const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

	function onReady(fn) {
		if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
		else fn();
	}

	function currentRoute() {
		const route = (window.location.hash.slice(1) || "welcome").replaceAll("-", "_");
		return SCREENS[route] ? route : "welcome";
	}

	// ---------- /login ----------

	function showScreen(route) {
		const panel = document.querySelector(".il-auth-panel");
		const back = document.querySelector(".il-auth-back");
		document.querySelectorAll(".il-auth-content > section").forEach((section) => {
			section.classList.remove("is-active");
			section.style.display = "";
		});
		const target = document.querySelector(SCREENS[route]);
		if (target) target.classList.add("is-active");
		if (panel) panel.dataset.screen = route === "welcome" ? "welcome" : "form";
		if (back) back.hidden = route === "welcome";

		const focusId = {
			login: "login_email",
			email: "login_email",
			steptwo: "login_password",
			forgot: "forgot_email",
			login_with_email_link: "login_with_email_link_email",
		}[route];
		if (focusId) setTimeout(() => document.getElementById(focusId)?.focus(), 60);
		document.title = `LMS | ${
			{
				welcome: "Login",
				login: "Login",
				forgot: "Forgot Password",
				login_with_email_link: "Login Link",
			}[route] || "Login"
		}`;
		refreshButtons();
	}

	function restoreButtonLabels() {
		document.querySelectorAll(".il-auth-submit").forEach((button) => {
			if (button.dataset.label) button.textContent = button.dataset.label;
		});
	}

	function clearErrors() {
		document.querySelectorAll(".il-field.invalid").forEach((field) => field.classList.remove("invalid"));
		document.querySelectorAll(".field-error").forEach((el) => (el.textContent = ""));
		document.querySelectorAll(".il-auth-banner").forEach((el) => (el.style.display = ""));
	}

	function value(id) {
		return (document.getElementById(id)?.value || "").trim();
	}

	function refreshButtons() {
		const consent = document.querySelector(".for-login .il-consent-input");
		const set = (selector, enabled) => {
			const button = document.querySelector(selector);
			// Leave "Sent" / "Verifying..." states alone; login.js owns those.
			if (button && button.textContent.trim() === button.dataset.label) button.disabled = !enabled;
		};
		set(".btn-login", value("login_email") && value("login_password") && (!consent || consent.checked));
		set(".btn-forgot", EMAIL_RE.test(value("forgot_email")));
		set(".btn-login-with-email-link", EMAIL_RE.test(value("login_with_email_link_email")));
	}

	function patchLoginJs() {
		if (typeof login === "undefined") return;

		// Frappe's reset_sections hides every <section>; re-apply our active screen afterwards.
		const originalReset = login.reset_sections;
		login.reset_sections = function (hide) {
			originalReset.call(this, hide);
			if (hide || hide === undefined) {
				clearErrors();
				restoreButtonLabels();
			}
		};

		Object.keys(SCREENS).forEach((route) => {
			login[route] = function () {
				clearErrors();
				restoreButtonLabels();
				if (route === "forgot" && value("login_email") && !value("forgot_email")) {
					document.getElementById("forgot_email").value = value("login_email");
				}
				if (route === "login_with_email_link" && value("login_email") && !value("login_with_email_link_email")) {
					document.getElementById("login_with_email_link_email").value = value("login_email");
				}
				showScreen(route);
			};
		});

		login.route = function () {
			login[currentRoute()]();
		};

		login.show_field_error = function (inputId, message) {
			const field = document.getElementById(inputId)?.closest(".il-field");
			if (!field) return;
			field.classList.add("invalid");
			const error = field.querySelector(".field-error");
			if (error) error.textContent = message;
		};

		login.call = function (args, callback, url) {
			login.set_status(__("Verifying..."), "blue");
			return frappe.call({
				type: "POST",
				url: url || "/",
				args: args,
				callback: callback,
				freeze: false,
				statusCode: login.login_handlers,
			});
		};

		const handlers = login.login_handlers || {};
		const original200 = handlers[200];
		if (original200) {
			handlers[200] = function (data) {
				if (data && data.message === "Logged In") {
					window.location.replace(postLoginTarget(data));
					return;
				}
				return original200.apply(this, arguments);
			};
		}
		// Any error response puts the button back so the user can retry.
		[401, 404, 417, 429, 500, 502].forEach((code) => {
			const original = handlers[code];
			handlers[code] = function () {
				const result = original ? original.apply(this, arguments) : undefined;
				setTimeout(() => {
					restoreButtonLabels();
					refreshButtons();
				}, 0);
				return result;
			};
		});
	}

	function postLoginTarget(data) {
		const params = new URLSearchParams(window.location.search);
		const requested = params.get("redirect-to") || params.get("redirect_to") || "";
		return safeRedirect(requested) || safeRedirect((data && data.home_page) || "") || "/dashboard";
	}

	function safeRedirect(url) {
		if (!url) return null;
		url = String(url).trim();
		if (url.charAt(0) !== "/" || url.startsWith("//")) return null;
		if (/^\/(api|app|desk|assets|files)(\/|$)/.test(url)) return null;
		if (url === "/lms" || url === "/lms/") return "/dashboard";
		if (url.startsWith("/lms/")) return url.slice(4) || "/dashboard";
		if (url === "/login") return "/dashboard";
		return url;
	}

	function bindLogin() {
		document.querySelector(".il-auth-back")?.addEventListener("click", () => {
			window.location.hash = BACK_TARGET[currentRoute()] || "#welcome";
		});

		document.querySelectorAll(".toggle-password").forEach((button) => {
			button.addEventListener("click", (event) => {
				event.preventDefault();
				const input = document.querySelector(button.getAttribute("toggle"));
				if (!input) return;
				const show = input.type === "password";
				input.type = show ? "text" : "password";
				button.setAttribute("aria-label", show ? __("Hide password") : __("Show password"));
				button.querySelector("use")?.setAttribute("href", show ? "#il-i-eye" : "#il-i-eye-off");
			});
		});

		document.addEventListener("input", (event) => {
			if (!event.target.closest(".il-auth-form")) return;
			event.target.closest(".il-field")?.classList.remove("invalid");
			refreshButtons();
		});
		document.addEventListener("change", (event) => {
			if (event.target.classList.contains("il-consent-input")) refreshButtons();
		});
		// Browsers autofill without firing input events.
		setTimeout(refreshButtons, 400);
		setTimeout(refreshButtons, 1500);
	}

	// ---------- /update-password ----------

	function buildUpdatePasswordShell() {
		const section = document.querySelector("section.for-reset-password") || document.querySelector("#reset-password")?.closest("section");
		if (!section || document.querySelector(".il-auth-shell")) return;

		const params = new URLSearchParams(window.location.search);
		const hasKey = Boolean(params.get("key"));

		const shell = document.createElement("div");
		shell.className = "il-auth-shell";
		shell.innerHTML = `
			<aside class="il-auth-brand" aria-label="Infinity Learn">
				<div class="il-auth-brand-bg" aria-hidden="true"></div>
				<div class="il-auth-brand-content">
					<img class="il-auth-logo" src="/assets/lms/images/il-logo-white.svg" alt="Infinity Learn by Sri Chaitanya" width="296" height="234" />
				</div>
			</aside>
			<main class="il-auth-panel" data-screen="form"><div class="il-auth-content"></div></main>`;
		section.classList.add("is-active");
		shell.querySelector(".il-auth-content").appendChild(section);
		document.body.prepend(shell);
		document.querySelector(".page-content-wrapper")?.remove();

		document.title = `LMS | ${hasKey ? "Set Password" : "Change Password"}`;
		const head = section.querySelector(".page-card-head");
		if (head) {
			const expired = params.get("password_expired");
			head.innerHTML = `
				<h1 class="il-auth-title">${hasKey ? __("Set Password") : __("Change Password")}</h1>
				<p class="il-auth-subtitle">${
					expired
						? __("Your password has expired. Please set a new one.")
						: hasKey
							? __("Choose a password for your LMS account")
							: __("Enter your current password, then choose a new one")
				}</p>`;
		}

		const labels = {
			old_password: __("Current Password"),
			new_password: __("New Password"),
			confirm_password: __("Confirm Password"),
		};
		Object.entries(labels).forEach(([id, text]) => {
			const label = section.querySelector(`label[for="${id}"]`);
			if (label) label.textContent = text;
		});
		if (hasKey) section.querySelector("#old_password")?.closest(".form-group")?.classList.add("il-auth-hidden");
		section.querySelectorAll("input[type='password']").forEach((input) => (input.placeholder = ""));

		const button = section.querySelector("#update");
		if (button) button.textContent = hasKey ? __("Set password") : __("Update password");

		const links = document.createElement("div");
		links.className = "il-auth-links";
		links.innerHTML = `<a class="il-auth-link" href="/login#login">${__("Back to login")}</a>`;
		section.appendChild(links);
	}

	window.__ = window.__ || ((text) => text);

	// Frappe may include this file before or after its inline login.js, so patch as soon as
	// `login` exists and route again once login.js's own ready handler has run.
	let patched = false;
	function ensurePatched() {
		if (!patched && typeof login !== "undefined") {
			patchLoginJs();
			patched = true;
		}
		return patched;
	}
	if (path === "login") ensurePatched();

	onReady(() => {
		if (path === "update-password") {
			buildUpdatePasswordShell();
			return;
		}
		ensurePatched();
		bindLogin();
		const boot = () => {
			document.querySelectorAll(".il-auth-form.hide").forEach((form) => form.classList.remove("hide"));
			if (typeof login !== "undefined" && login.route) login.route();
			else showScreen(currentRoute());
		};
		// Run after every other ready handler (including login.js's own login.route()).
		const later = () => setTimeout(() => {
			ensurePatched();
			boot();
		}, 0);
		if (typeof frappe !== "undefined" && frappe.ready) frappe.ready(later);
		else later();
		window.addEventListener("hashchange", () => {
			if (typeof login !== "undefined" && login.route) login.route();
			else showScreen(currentRoute());
		});
	});
})();
