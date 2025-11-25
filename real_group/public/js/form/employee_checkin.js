frappe.ui.form.on("Employee Checkin", {
    refresh(frm) {
        frm.add_custom_button(__('Fetch Location'), function() {
        fetch_geolocation(frm);
        });
    }
}); 

fetch_geolocation = async (frm) => {
		if (!navigator.geolocation) {
			frappe.msgprint({
				message: __("Geolocation is not supported by your current browser"),
				title: __("Geolocation Error"),
				indicator: "red",
			});
			return;
		}

		frappe.dom.freeze(__("Fetching your geolocation") + "...");

		navigator.geolocation.getCurrentPosition(
			async (position) => {
				frm.set_value("custom_latitude", position.coords.latitude);
				frm.set_value("custom_longitude", position.coords.longitude);

				await frm.call("set_geolocation");
				frappe.dom.unfreeze();
			},
			(error) => {
				frappe.dom.unfreeze();

				let msg = __("Unable to retrieve your location") + "<br><br>";
				if (error) {
					msg += __("ERROR({0}): {1}", [error.code, error.message]);
				}
				frappe.msgprint({
					message: msg,
					title: __("Geolocation Error"),
					indicator: "red",
				});
			},
		);
	}