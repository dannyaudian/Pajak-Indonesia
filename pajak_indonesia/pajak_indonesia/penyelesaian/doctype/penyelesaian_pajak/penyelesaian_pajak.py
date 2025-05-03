import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_days
from frappe.model.workflow import apply_workflow

class PenyelesaianPajak(Document):
    def validate(self):
        self.validate_dates()
        self.calculate_tax_amount()
        self.set_payment_due_date()
        self.validate_reference()
    
    def validate_dates(self):
        """Validate posting and due dates"""
        if getdate(self.posting_date) > getdate(self.due_date):
            frappe.throw("Due Date cannot be before Posting Date")
    
    def calculate_tax_amount(self):
        """Calculate tax amount based on base amount and rate"""
        self.tax_amount = flt(self.tax_base_amount) * (flt(self.tax_rate) / 100)
    
    def set_payment_due_date(self):
        """Set payment due date based on tax type"""
        if not self.payment_due_date:
            # Default payment terms based on tax type
            if self.jenis_pajak == "PPN":
                # End of next month
                end_of_month = getdate(f"{self.tahun_pajak}-{self.masa_pajak}-01")
                self.payment_due_date = add_days(end_of_month, 60)
            elif self.jenis_pajak in ["PPh 21", "PPh 23", "PPh 26"]:
                # 10th of next month
                next_month = add_days(getdate(f"{self.tahun_pajak}-{self.masa_pajak}-01"), 40)
                self.payment_due_date = next_month
    
    def validate_reference(self):
        """Validate reference document"""
        if self.reference_type and self.reference_name:
            doc = frappe.get_doc(self.reference_type, self.reference_name)
            
            # Validate document status
            if doc.docstatus != 1:
                frappe.throw(f"Reference document {self.reference_name} must be submitted")
            
            # Validate tax period
            if hasattr(doc, 'masa_pajak') and doc.masa_pajak != self.masa_pajak:
                frappe.throw("Tax period mismatch with reference document")
            
            if hasattr(doc, 'tahun_pajak') and doc.tahun_pajak != self.tahun_pajak:
                frappe.throw("Tax year mismatch with reference document")
    
    def on_submit(self):
        """Handle document submission"""
        # Update reference document status if needed
        if self.reference_type and self.reference_name:
            frappe.db.set_value(self.reference_type, self.reference_name, 
                              "status", "Payment In Progress")
    
    def on_cancel(self):
        """Handle document cancellation"""
        # Revert reference document status if needed
        if self.reference_type and self.reference_name:
            frappe.db.set_value(self.reference_type, self.reference_name, 
                              "status", "Submitted")
    
    def on_update_after_submit(self):
        """Handle post-submission updates"""
        # Update reference document when payment is completed
        if self.workflow_state == "Payment Completed" and self.reference_type and self.reference_name:
            frappe.db.set_value(self.reference_type, self.reference_name, {
                "status": "Paid",
                "ntpn": self.ntpn
            })