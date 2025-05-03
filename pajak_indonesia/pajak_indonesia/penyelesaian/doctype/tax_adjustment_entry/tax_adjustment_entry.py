import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate
from erpnext.accounts.general_ledger import make_gl_entries

class TaxAdjustmentEntry(Document):
    def validate(self):
        self.validate_dates()
        self.validate_reference()
        self.set_original_values()
        self.calculate_final_values()
        self.validate_accounts()
    
    def validate_dates(self):
        """Validate posting date and tax period"""
        if not (2000 <= int(self.tahun_pajak) <= 2099):
            frappe.throw(_("Tax Year must be between 2000 and 2099"))
            
        posting_date = getdate(self.posting_date)
        if posting_date.year != int(self.tahun_pajak) or \
           str(posting_date.month).zfill(2) != self.masa_pajak:
            frappe.throw(_("Posting Date must be within the selected tax period"))
    
    def validate_reference(self):
        """Validate reference document"""
        if self.reference_doctype and self.reference_name:
            doc = frappe.get_doc(self.reference_doctype, self.reference_name)
            
            # Check if document is submitted
            if doc.docstatus != 1:
                frappe.throw(_("Reference document must be submitted"))
            
            # Validate tax period
            if hasattr(doc, 'masa_pajak') and doc.masa_pajak != self.masa_pajak:
                frappe.throw(_("Tax period mismatch with reference document"))
            if hasattr(doc, 'tahun_pajak') and doc.tahun_pajak != self.tahun_pajak:
                frappe.throw(_("Tax year mismatch with reference document"))
    
    def set_original_values(self):
        """Set original tax values from reference document"""
        if self.reference_doctype and self.reference_name:
            doc = frappe.get_doc(self.reference_doctype, self.reference_name)
            
            if self.reference_doctype == "SPT Summary":
                if "PPN" in doc.jenis_spt:
                    self.original_tax_base = doc.jumlah_dpp_penjualan
                    self.original_tax_amount = doc.jumlah_ppn_penjualan
                elif "PPh 21" in doc.jenis_spt:
                    self.original_tax_base = doc.jumlah_penghasilan_bruto_21
                    self.original_tax_amount = doc.jumlah_pph_21
                elif "PPh 23" in doc.jenis_spt:
                    self.original_tax_base = doc.jumlah_penghasilan_bruto_23
                    self.original_tax_amount = doc.jumlah_pph_23
                elif "PPh 26" in doc.jenis_spt:
                    self.original_tax_base = doc.jumlah_penghasilan_bruto_26
                    self.original_tax_amount = doc.jumlah_pph_26
            
            elif self.reference_doctype == "Efaktur Document":
                self.original_tax_base = doc.jumlah_dpp
                self.original_tax_amount = doc.jumlah_ppn
            
            elif self.reference_doctype == "Ebupot Document":
                self.original_tax_base = doc.penghasilan_bruto
                self.original_tax_amount = doc.pph_dipotong
            
            elif self.reference_doctype == "Salary Slip":
                self.original_tax_base = doc.gross_pay
                self.original_tax_amount = doc.total_tax_deducted
            
            elif self.reference_doctype == "Penyelesaian Pajak":
                self.original_tax_base = doc.tax_base_amount
                self.original_tax_amount = doc.tax_amount
    
    def calculate_final_values(self):
        """Calculate final values and difference amount"""
        if self.adjustment_type == "Addition":
            self.final_tax_base = flt(self.original_tax_base) + flt(self.adjustment_tax_base)
            self.final_tax_amount = flt(self.original_tax_amount) + flt(self.adjustment_tax_amount)
        else:  # Reduction
            self.final_tax_base = flt(self.original_tax_base) - flt(self.adjustment_tax_base)
            self.final_tax_amount = flt(self.original_tax_amount) - flt(self.adjustment_tax_amount)
        
        self.difference_amount = flt(self.final_tax_amount) - flt(self.original_tax_amount)
    
    def validate_accounts(self):
        """Validate GL accounts"""
        for account in [self.adjustment_account, self.tax_account]:
            if not frappe.db.exists("Account", account):
                frappe.throw(_("Account {0} does not exist").format(account))
            
            # Check if account belongs to company
            company = frappe.db.get_value("Account", account, "company")
            if company != self.company:
                frappe.throw(_("Account {0} does not belong to company {1}").format(
                    account, self.company))
    
    def on_submit(self):
        """Create GL entries on submission"""
        self.make_gl_entries()
        self.update_reference_document()
    
    def on_cancel(self):
        """Reverse GL entries on cancellation"""
        self.make_gl_entries(cancel=True)
        self.update_reference_document(cancel=True)
    
    def make_gl_entries(self, cancel=False):
        """Create GL entries for tax adjustment"""
        gl_entries = []
        
        # Calculate amount based on adjustment type
        amount = flt(self.difference_amount)
        if cancel:
            amount = -amount
        
        if amount > 0:
            # Debit adjustment account
            gl_entries.append({
                "account": self.adjustment_account,
                "debit": amount,
                "credit": 0,
                "against": self.tax_account,
                "posting_date": self.posting_date,
                "cost_center": frappe.db.get_value("Company", self.company, "cost_center"),
                "remarks": self.remarks or _("Tax adjustment against {0} {1}").format(
                    self.reference_doctype, self.reference_name)
            })
            
            # Credit tax account
            gl_entries.append({
                "account": self.tax_account,
                "debit": 0,
                "credit": amount,
                "against": self.adjustment_account,
                "posting_date": self.posting_date,
                "cost_center": frappe.db.get_value("Company", self.company, "cost_center"),
                "remarks": self.remarks or _("Tax adjustment against {0} {1}").format(
                    self.reference_doctype, self.reference_name)
            })
        else:
            # Debit tax account
            gl_entries.append({
                "account": self.tax_account,
                "debit": abs(amount),
                "credit": 0,
                "against": self.adjustment_account,
                "posting_date": self.posting_date,
                "cost_center": frappe.db.get_value("Company", self.company, "cost_center"),
                "remarks": self.remarks or _("Tax adjustment against {0} {1}").format(
                    self.reference_doctype, self.reference_name)
            })
            
            # Credit adjustment account
            gl_entries.append({
                "account": self.adjustment_account,
                "debit": 0,
                "credit": abs(amount),
                "against": self.tax_account,
                "posting_date": self.posting_date,
                "cost_center": frappe.db.get_value("Company", self.company, "cost_center"),
                "remarks": self.remarks or _("Tax adjustment against {0} {1}").format(
                    self.reference_doctype, self.reference_name)
            })
        
        # Make GL entries
        if gl_entries:
            make_gl_entries(gl_entries, cancel=cancel)
    
    def update_reference_document(self, cancel=False):
        """Update reference document with adjustment info"""
        if self.reference_doctype and self.reference_name:
            adjustment_info = {
                "adjusted_by": None if cancel else self.name,
                "adjusted_amount": 0 if cancel else self.difference_amount,
                "adjusted_date": None if cancel else self.posting_date
            }
            
            frappe.db.set_value(self.reference_doctype, self.reference_name, adjustment_info)