frappe.ui.form.on('Tax Filing Summary', {
    refresh: function(frm) {
        // Add action button if conditions are met
        if (frm.doc.docstatus === 1 && 
            frm.doc.status_spt === 'Kurang Bayar' && 
            !frm.doc.payment_entry) {
            
            frm.add_custom_button(__('Generate Payment Entry'), function() {
                frappe.call({
                    method: 'pajak_indonesia.pelaporan.doctype.tax_filing_summary.tax_filing_summary.generate_payment_entry',
                    args: {
                        tax_filing_id: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message && r.message.status === 'success') {
                            frappe.show_alert({
                                message: r.message.message,
                                indicator: 'green'
                            });
                            
                            // Redirect to Payment Entry
                            if (r.message.payment_entry_id) {
                                frappe.set_route('Form', 'Payment Entry', r.message.payment_entry_id);
                            } else {
                                frm.reload_doc();
                            }
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                message: r.message.message,
                                indicator: 'red'
                            });
                        }
                    }
                });
            }, __('Create'));
        }
        
        // Add view button if payment exists
        if (frm.doc.payment_entry) {
            frm.add_custom_button(__('View Payment'), function() {
                frappe.set_route('Form', 'Payment Entry', frm.doc.payment_entry);
            }, __('View'));
        }

        // Add adjustment button if conditions are met
        if (frm.doc.docstatus === 1 && 
            frm.doc.status_spt === 'Lebih Bayar' && 
            !frm.doc.adjustment_entry) {
            
            frm.add_custom_button(__('Generate Tax Adjustment'), function() {
                frappe.call({
                    method: 'pajak_indonesia.pelaporan.doctype.tax_filing_summary.tax_filing_summary.generate_adjustment_entry',
                    args: {
                        tax_filing_id: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message && r.message.status === 'success') {
                            frappe.show_alert({
                                message: r.message.message,
                                indicator: 'green'
                            });
                            
                            // Redirect to Tax Adjustment Entry
                            if (r.message.adjustment_entry_id) {
                                frappe.set_route('Form', 'Tax Adjustment Entry', r.message.adjustment_entry_id);
                            } else {
                                frm.reload_doc();
                            }
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                message: r.message.message,
                                indicator: 'red'
                            });
                        }
                    }
                });
            }, __('Create'));
        }
        
        // Add view button if adjustment exists
        if (frm.doc.adjustment_entry) {
            frm.add_custom_button(__('View Adjustment'), function() {
                frappe.set_route('Form', 'Tax Adjustment Entry', frm.doc.adjustment_entry);
            }, __('View'));
        }
    }
});