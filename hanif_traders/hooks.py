app_name = "hanif_traders"
app_title = "Hanif Traders"
app_publisher = "Salman"
app_description = "Custom App for Hanif Traders"
app_email = "salman.hanif917@gmail.com"
app_license = "mit"

fixtures = [
    # Only our custom field on Employee
    {"dt": "Custom Field", "filters": [["name", "in", [
        "Employee-custom_cnic",
        "Employee-custom_cnic_image",
        "Employee-custom_cnic_picture",
        "Employee-custom_age",
        "Employee-custom_phone_number"
    ]]]},

    # Only permissions we set via Role Permission Manager (optional but recommended)
    {
        "dt": "Custom DocPerm", "filters": [["parent", "in", [
        "Technician Points Log",
        "Technician Points Redemption",
        "Complain"
    ]]]
    },

    {
        "dt": "Workspace",
        "filters": [["module", "=", "Hanif Traders"]]
    },
    {
        "dt": "Workflow",
        "filters": [["document_type", "=", "Complain"]]
    },
    {
        "dt": "Server Script",
        "filters": [["module", "=", "Hanif Traders"]]
    },
    {
        "dt": "Client Script",
        "filters": [["module", "=", "Hanif Traders"]]
    },
    {
        "dt": "Workflow State",
        "filters": [["workflow_state_name", "in", ["CSC Verified"]]]
    },
    {
        "dt": "Number Card",
        "filters": [["name", "in", [
            "Weekly Complain",
            "Weekly Complain Resolved",
            "No of Line Items"
        ]]]
    },
]

app_include_js = ["/assets/hanif_traders/js/stock_check_dialog.js"]


# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "hanif_traders",
# 		"logo": "/assets/hanif_traders/logo.png",
# 		"title": "Hanif Traders",
# 		"route": "/hanif_traders",
# 		"has_permission": "hanif_traders.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/hanif_traders/css/hanif_traders.css"
# app_include_js = "/assets/hanif_traders/js/hanif_traders.js"

# include js, css files in header of web template
# web_include_css = "/assets/hanif_traders/css/hanif_traders.css"
# web_include_js = "/assets/hanif_traders/js/hanif_traders.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "hanif_traders/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "hanif_traders/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "hanif_traders.utils.jinja_methods",
# 	"filters": "hanif_traders.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "hanif_traders.install.before_install"
# after_install = "hanif_traders.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "hanif_traders.uninstall.before_uninstall"
# after_uninstall = "hanif_traders.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "hanif_traders.utils.before_app_install"
# after_app_install = "hanif_traders.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "hanif_traders.utils.before_app_uninstall"
# after_app_uninstall = "hanif_traders.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "hanif_traders.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Employee": {
		"validate": "hanif_traders.api.employee.calculate_age",
        "on_update": "hanif_traders.api.employee.sync_technician_details"
	},
    "Purchase Receipt": {
        "validate": "hanif_traders.api.purchase_receipt.explode_bundle_items",
        "on_submit": "hanif_traders.api.purchase_receipt.create_stock_entry_on_submit",
        "on_cancel": "hanif_traders.api.purchase_receipt.cancel_stock_entry"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"hanif_traders.tasks.all"
# 	],
# 	"daily": [
# 		"hanif_traders.tasks.daily"
# 	],
# 	"hourly": [
# 		"hanif_traders.tasks.hourly"
# 	],
# 	"weekly": [
# 		"hanif_traders.tasks.weekly"
# 	],
# 	"monthly": [
# 		"hanif_traders.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "hanif_traders.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "hanif_traders.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "hanif_traders.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["hanif_traders.utils.before_request"]
# after_request = ["hanif_traders.utils.after_request"]

# Job Events
# ----------
# before_job = ["hanif_traders.utils.before_job"]
# after_job = ["hanif_traders.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"hanif_traders.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

