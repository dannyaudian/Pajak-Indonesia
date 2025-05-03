import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
import json
import os

def setup_custom_fields():
    """Setup Custom Fields for Indonesian Tax Module"""
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load custom fields from JSON
    with open(os.path.join(current_dir, '..', 'custom_fields', 'cf_tax.json')) as f:
        custom_fields = json.load(f)
    
    # Create custom fields
    create_custom_fields(custom_fields)
    
    # Update properties of standard fields if needed
    update_standard_fields()

def update_standard_fields():
    """Update properties of standard fields if needed"""
    # Example: Make tax_id searchable in list view
    for doctype in ["Customer", "Supplier"]:
        if frappe.db.exists("DocType", doctype):
            frappe.db.set_value(
                "DocField",
                {"parent": doctype, "fieldname": "tax_id"},
                "in_list_view",
                1
            )

def after_install():
    """Run after module installation"""
    setup_custom_fields()