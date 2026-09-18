/**
 * Sales LMS auth UI — section routing + Frappe login.js compatibility.
 * Does NOT replace login.js APIs, handlers, or session logic.
 */
(function () {
	function restoreAuthButtonLabels() {
		$(".btn-login, .btn-forgot, .btn-login-with-email-link, .btn-signup").each(
			function () {
				const label = $(this).data("label");
				if (label) {
					$(this).text(label);
				}
			}
		);
		$(".page-card-body").removeClass("invalid");
	}

	function syncActiveSection() {
		const route = (window.location.hash.slice(1) || "login").replaceAll("-", "_");
		const map = {
			login: ".for-login",
			email: ".for-login",
			steptwo: ".for-login",
			signup: ".for-signup",
			forgot: ".for-forgot",
			login_with_email_link: ".for-login-with-email-link",
		};
		const selector = map[route] || map.login;
		$(".il-auth-panel section").removeClass("is-active");
		$(selector).addClass("is-active");
	}

	const _resetSections = login.reset_sections;
	login.reset_sections = function (hide) {
		_resetSections.call(this, hide);
		if (hide || hide === undefined) {
			$(".il-field")
				.removeClass("invalid")
				.find(".field-error")
				.text("");
			restoreAuthButtonLabels();
		}
		syncActiveSection();
	};

	login.login = function () {
		login.reset_sections();
		$(".for-login").toggle(true).addClass("is-active");
		restoreAuthButtonLabels();
		syncActiveSection();
	};

	login.email = function () {
		login.login();
		$("#login_email").trigger("focus");
	};

	login.steptwo = function () {
		login.login();
		$("#login_password").trigger("focus");
	};

	login.forgot = function () {
		login.reset_sections();
		if ($("#login_email").val()) {
			$("#forgot_email").val($("#login_email").val());
		}
		$(".for-forgot").toggle(true).addClass("is-active");
		restoreAuthButtonLabels();
		$("#forgot_email").trigger("focus");
		syncActiveSection();
	};

	login.login_with_email_link = function () {
		login.reset_sections();
		if ($("#login_email").val()) {
			$("#login_with_email_link_email").val($("#login_email").val());
		}
		$(".for-login-with-email-link").toggle(true).addClass("is-active");
		restoreAuthButtonLabels();
		$("#login_with_email_link_email").trigger("focus");
		syncActiveSection();
	};

	login.signup = function () {
		login.reset_sections();
		$(".for-signup").toggle(true).addClass("is-active");
		restoreAuthButtonLabels();
		$("#signup_fullname").trigger("focus");
		syncActiveSection();
	};

	login.route = function () {
		let route = window.location.hash.slice(1);
		if (!route) route = "login";
		route = route.replaceAll("-", "_");
		if (typeof login[route] === "function") {
			login[route]();
		} else {
			login.login();
		}
	};

	login.show_field_error = function (input_id, message) {
		const $field = $("#" + input_id).closest(".il-field, .form-group");
		$field.addClass("invalid").find(".field-error").text(message);
	};

	login.call = function (args, callback, url) {
		login.set_status("Verifying...", "blue");
		return frappe.call({
			type: "POST",
			url: url || "/",
			args: args,
			callback: callback,
			freeze: false,
			statusCode: login.login_handlers,
		});
	};

	const orig200 = login.login_handlers && login.login_handlers[200];
	if (orig200) {
		login.login_handlers[200] = function (data) {
			if (data && data.message === "Logged In") {
				window.location.replace(resolvePostLoginTarget(data));
				return;
			}
			return orig200.apply(this, arguments);
		};
	}

	function resolvePostLoginTarget(data) {
		const params = new URLSearchParams(window.location.search);
		const requested = params.get("redirect-to") || params.get("redirect_to") || "";
		const fromServer = (data && data.home_page) || "";
		return sanitizeRedirect(requested) || sanitizeRedirect(fromServer) || "/dashboard";
	}

	function sanitizeRedirect(url) {
		if (!url) return null;
		url = String(url).trim();
		if (url.charAt(0) !== "/" || url.indexOf("//") === 0) return null;
		if (
			url.indexOf("/api") === 0 ||
			url.indexOf("/app") === 0 ||
			url.indexOf("/desk") === 0 ||
			url.indexOf("/assets") === 0 ||
			url.indexOf("/files") === 0
		) {
			return null;
		}
		if (url === "/lms" || url === "/lms/") return "/dashboard";
		if (url.indexOf("/lms/") === 0) return url.slice(4) || "/dashboard";
		if (url === "/login") return "/dashboard";
		return url;
	}

	function bindPasswordToggle() {
		$(".toggle-password")
			.off("click")
			.on("click", function (event) {
				event.preventDefault();
				const input = $($(this).attr("toggle"));
				const showing = input.attr("type") === "text";
				input.attr("type", showing ? "password" : "text");
				$(this).attr(
					"aria-label",
					showing ? "Show password" : "Hide password"
				);
			});
	}

	frappe.ready(function () {
		$(".form-forgot").removeClass("hide");
		$(".form-login-with-email-link").removeClass("hide");
		$(".form-signup").removeClass("hide");
		bindPasswordToggle();
		login.route();
		syncActiveSection();

		$(document).on("input", ".il-field input", function () {
			$(this).closest(".il-field, .form-group").removeClass("invalid");
		});
	});
})();
