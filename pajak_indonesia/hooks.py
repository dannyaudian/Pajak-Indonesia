from frappe import _

app_name = "pajak_indonesia"
app_title = "Pajak Indonesia"
app_publisher = "Your Organization"
app_description = "Indonesian Tax Management App"
app_email = "your@email.com"
app_license = "MIT"
required_apps = ["erpnext"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/pajak_indonesia/css/pajak_indonesia.css"
app_include_js = "/assets/pajak_indonesia/js/pajak_indonesia.js"

# Modules and configuration
# ------------------------
modules = {
    "E-Faktur": "efaktur",
    "E-Bupot": "ebupot",
    "SPT": "spt", 
    "Penyelesaian": "penyelesaian",
    "Pelaporan": "pelaporan"
}

# Setup and installation
# ----------------------
after_install = "pajak_indonesia.setup.custom_fields.after_install"

# Document hooks and events
# ------------------------
doc_events = {
    "Sales Invoice": {
        "on_submit": [
            "pajak_indonesia.efaktur.utils.create_document",
            "pajak_indonesia.pelaporan.utils.auto_tag_gl_entry"
        ],
        "on_cancel": "pajak_indonesia.efaktur.utils.cancel_efaktur"
    },
    "Purchase Invoice": {
        "on_submit": "pajak_indonesia.ebupot.utils.create_document_if_pph",
        "on_cancel": "pajak_indonesia.ebupot.utils.cancel_ebupot"
    },
    "Payment Entry": {
        "validate": "pajak_indonesia.ebupot.utils.link_deduction_to_bupot",
        "on_submit": "pajak_indonesia.ebupot.utils.update_ebupot_status",
        "on_cancel": "pajak_indonesia.ebupot.utils.revert_ebupot_status"
    },
    "GL Entry": {
        "before_insert": "pajak_indonesia.pelaporan.utils.tag_ppn_out_gl",
        "autoname": "pajak_indonesia.pelaporan.utils.gl_entry_naming_override",
        "after_insert": "pajak_indonesia.pelaporan.utils.auto_tag_gl_entry"
    }
}



# UI and list view customizations
# ------------------------------
get_list_custom_fields = {
    "Customer": ["tax_id"],
    "Supplier": ["tax_id"]
}

list_view_settings = {
    "Sales Invoice": {
        "add_fields": ["has_generated_efaktur"],
        "filters": [["docstatus", "=", "1"]]
    },
    "Purchase Invoice": {
        "add_fields": ["fp_masukan_status"],
        "filters": [["docstatus", "=", "1"]]
    },
    "Efaktur Document": {
        "add_fields": ["status", "jumlah_ppn"],
        "filters": []
    },
    "Ebupot Document": {
        "add_fields": ["status", "pph_dipotong"],
        "filters": []
    },
    "Tax Filing Summary": {
        "add_fields": ["status_spt", "tanggal_pelaporan"],
        "filters": []
    }
}

# Website-specific
# --------------
website_route_rules = [
    {"from_route": "/faktur/<name>", "to_route": "efaktur/view"},
    {"from_route": "/pajak/e-faktur", "to_route": "efaktur/list"}
]


# Workspace and dashboard
# ---------------------
workspace_info = {
    "Pajak Indonesia": {
        "category": "Modules",
        "color": "#3498db",
        "icon": "tax",
        "type": "module",
        "link": "Pajak Indonesia",
        "label": _("Pajak Indonesia")
    }
}

# Dashboards
dashboards = [
    "Pajak Indonesia"
]

# Charts for dashboard
charts = [
    {
        "name": "PPN Comparison",
        "chart_name": _("PPN Comparison"),
        "chart_type": "Custom",
        "source": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_ppn_comparison_chart"
    },
    {
        "name": "Filing Status",
        "chart_name": _("Filing Status"),
        "chart_type": "Custom",
        "source": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_filing_status_chart"
    },
    {
        "name": "Monthly Tax Amounts",
        "chart_name": _("Monthly Tax Amounts"),
        "chart_type": "Custom",
        "source": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_monthly_tax_chart"
    },
    {
        "name": "Tax Types Distribution",
        "chart_name": _("Tax Types Distribution"),
        "chart_type": "Custom",
        "source": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_tax_types_chart"
    }
]

# Dashboard number cards
number_cards = [
    {
        "name": "PPN YTD",
        "document_type": "Custom",
        "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_number_cards"
    },
    {
        "name": "PPh 21 YTD",
        "document_type": "Custom",
        "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_number_cards"
    },
    {
        "name": "PPh 23 YTD",
        "document_type": "Custom",
        "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_number_cards"
    },
    {
        "name": "E-Faktur Count",
        "document_type": "Custom",
        "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_number_cards"
    },
    {
        "name": "E-Bupot Count",
        "document_type": "Custom",
        "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_number_cards"
    }
]

# Export / import functions 
export_import_fixtures = True
fixtures = [
    {
        "dt": "Custom Field", 
        "filters": [["module", "=", "Pajak Indonesia"]]
    },
    {
        "dt": "Tax Category"
    },
    {
        "dt": "Salary Component",
        "filters": [["is_tax_applicable", "=", 1]]
    }
]

# Workspace and dashboard
# ---------------------
workspace_info = {
    "Pajak Indonesia": {
        "category": "Modules",
        "color": "#3498db",
        "icon": "octicon octicon-file-directory",
        "icon": "tax",
        "type": "module",
        "link": "Pajak Indonesia",
        "label": "Pajak Indonesia"
        "label": _("Pajak Indonesia")
    }
}

# Dashboards
dashboards = [
    "Pajak Indonesia"
]

# Charts to be used in the dashboard
# Charts for dashboard
charts = [
    {
        "name": "PPN Comparison",
        "chart_name": _("PPN Comparison"),
        "chart_type": "Custom",
        "source": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_ppn_comparison_chart"
    },
    {
        "name": "Filing Status",
        "chart_name": _("Filing Status"),
        "chart_type": "Custom",
        "source": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_filing_status_chart"
    },
    {
        "name": "Monthly Tax Amounts",
        "chart_name": _("Monthly Tax Amounts"),
        "chart_type": "Custom",
        "source": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_monthly_tax_chart"
    }
]

# Number Cards
# Dashboard number cards
number_cards = [
    {
        "name": "PPN YTD",
        "document_type": "Custom",
        "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_number_cards"
    },
    {
        "name": "PPh 21 YTD",
        "document_type": "Custom",
        "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_number_cards"
    },
    {
        "name": "PPh 23 YTD",
        "document_type": "Custom",
        "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_number_cards"
    },
    {
        "name": "E-Faktur Count",
        "document_type": "Custom",
        "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_number_cards"
    },
    {
        "name": "E-Bupot Count",
        "document_type": "Custom",
        "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.get_number_cards"
    }
]
