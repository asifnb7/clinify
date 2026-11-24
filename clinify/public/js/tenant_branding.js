(() => {
	function addPlatformAttribution() {
		if (!window.frappe?.boot || frappe.boot.clinify_is_control_site !== false) {
			return false;
		}

		const navItems = document.querySelector("header.navbar .navbar-nav");
		const userMenu = navItems?.querySelector(".dropdown-navbar-user");
		if (!navItems || !userMenu) return false;

		if (navItems.querySelector(".clinify-platform-attribution")) return true;

		const item = document.createElement("li");
		item.className = "nav-item clinify-platform-attribution";
		item.setAttribute("role", "note");
		item.setAttribute("aria-label", "Powered by Clinify");
		item.textContent = "Powered by Clinify";
		navItems.insertBefore(item, userMenu);
		return true;
	}

	const observer = new MutationObserver(() => {
		if (addPlatformAttribution()) observer.disconnect();
	});

	if (document.documentElement) {
		observer.observe(document.documentElement, { childList: true, subtree: true });
	}

	if (addPlatformAttribution()) observer.disconnect();
})();
