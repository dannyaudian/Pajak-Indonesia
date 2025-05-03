import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def generate_adjustment_entry(tax_filing_id):
    """
    Generate Tax Adjustment Entry for Tax Filing Summary with Lebih Bayar.
    
    Args:
        tax_filing_id: ID of the Tax Filing Summary
        
    Returns:
        dict: Result with status and adjustment_entry_id
    """
    try:
        # Get Tax Filing Summary
        filing = frappe.get_doc("Tax Filing Summary", tax_filing_id)
        
        # Validate filing
        if not filing.docstatus == 1:
            return {
                "status": "error",
                "message": _("Tax Filing must be submitted before generating adjustment")
            }
        
        # Check if adjustment already exists
        if filing.adjustment_entry:
            return {
                "status": "error",
                "message": _("Adjustment Entry already exists: {0}").format(filing.adjustment_entry)
            }
        
        # Check if this is a Lebih Bayar case
        tax_amount = get_tax_due_amount(filing)
        if tax_amount >= 0:
            return {
                "status": "error",
                "message": _("Adjustment Entry can only be created for Lebih Bayar filings with negative amount")
            }
        
        # Get accounts
        company = filing.company
        adjustment_account = get_adjustment_account(company)
        tax_account = get_tax_account(company, filing.jenis_pelaporan)
        
        if not adjustment_account:
            return {
                "status": "error",
                "message": _("No adjustment account found for {0}").format(company)
            }
        
        if not tax_account:
            return {
                "status": "error",
                "message": _("No tax account found for {0} and {1}").format(
                    company, filing.jenis_pelaporan
                )
            }
        
        # Create adjustment entry
        compensation_amount = abs(tax_amount)  # Convert negative to positive
        
        adjustment = frappe.new_doc("Tax Adjustment Entry")
        adjustment.update({
            "company": company,
            "posting_date": nowdate(),
            "jenis_pajak": get_tax_type_code(filing.jenis_pelaporan),
            "jenis_penyesuaian": "Kompensasi Lebih Bayar",
            "adjustment_type": "Addition",  # For compensation, we're adding a credit
            "reason": _("Tax compensation from {0} for {1} {2}/{3}").format(
                filing.name,
                filing.jenis_pelaporan,
                filing.masa_pajak,
                filing.tahun_pajak
            ),
            "masa_pajak": filing.masa_pajak,
            "tahun_pajak": filing.tahun_pajak,
            "reference_doctype": "Tax Filing Summary",
            "reference_name": filing.name,
            "original_tax_base": 0,  # Will be calculated based on tax rate
            "original_tax_amount": 0,
            "adjustment_tax_base": compensation_amount * 100 / 11,  # Assuming 11% for PPN, should be configurable
            "adjustment_tax_amount": compensation_amount,
            "adjustment_account": adjustment_account,
            "tax_account": tax_account,
            "nominal_kompensasi": compensation_amount,
            "kompensasi_type": "Dikompensasikan ke Masa Pajak Berikutnya",
            "kompensasi_source": filing.name,
            "remarks": _("Tax compensation from {0} {1}/{2}").format(
                filing.jenis_pelaporan,
                filing.masa_pajak,
                filing.tahun_pajak
            )
        })
        
        # Save adjustment entry
        adjustment.insert()
        
        # Update Tax Filing Summary
        filing.adjustment_entry = adjustment.name
        filing.adjustment_status = "Kompensasi"
        filing.adjustment_date = nowdate()
        filing.save()
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Tax Adjustment Entry {0} has been created").format(adjustment.name),
            "adjustment_entry_id": adjustment.name
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            message=f"Failed to create Tax Adjustment Entry for Tax Filing {tax_filing_id}: {str(e)}",
            title="Tax Adjustment Creation Error"
        )
        return {
            "status": "error",
            "message": _("Failed to create Tax Adjustment Entry: {0}").format(str(e))
        }

def get_adjustment_account(company):
    """
    Get account for tax adjustment entries.
    
    Args:
        company: Company name
        
    Returns:
        str: Adjustment account code
    """
    # Try to get a specific tax adjustment account
    adjustment_accounts = frappe.get_list(
        "Account",
        filters={
            "company": company,
            "account_type": ["in", ["Temporary", "Expense", "Income"]],
            "is_group": 0
        },
        or_filters={
            "account_name": ["like", "%tax%adjustment%"],
            "account_name": ["like", "%pajak%penyesuaian%"],
            "account_name": ["like", "%kompensasi%pajak%"]
        },
        fields=["name"],
        limit=1
    )
    
    if adjustment_accounts:
        return adjustment_accounts[0].name
    
    # Fallback to a general temporary account
    temp_accounts = frappe.get_list(
        "Account",
        filters={
            "company": company,
            "account_type": ["in", ["Temporary", "Expense"]],
            "is_group": 0
        },
        fields=["name"],
        limit=1
    )
    
    if temp_accounts:
        return temp_accounts[0].name
    
    # Last resort: use Temporary Opening account
    return frappe.db.get_value("Company", company, "temporary_account") or \
           frappe.db.get_value("Company", company, "default_expense_account")

def get_tax_type_code(jenis_pelaporan):
    """
    Convert reporting type to tax type code.
    
    Args:
        jenis_pelaporan: Tax filing type
        
    Returns:
        str: Tax type code
    """
    tax_type_map = {
        "SPT Masa PPN": "PPN",
        "SPT Masa PPh 21": "PPh 21",
        "SPT Masa PPh 23": "PPh 23",
        "SPT Masa PPh 26": "PPh 26",
        "SPT Masa PPh 4(2)": "PPh 4(2)"
    }
    
    return tax_type_map.get(jenis_pelaporan, "PPN")

@frappe.whitelist()
def generate_payment_entry(tax_filing_id):
    """
    Generate Payment Entry for Tax Filing Summary.
    
    Args:
        tax_filing_id: ID of the Tax Filing Summary
        
    Returns:
        dict: Result with status and payment_entry_id
    """
    try:
        # Get Tax Filing Summary
        filing = frappe.get_doc("Tax Filing Summary", tax_filing_id)
        
        # Validate filing
        if not filing.docstatus == 1:
            return {
                "status": "error",
                "message": _("Tax Filing must be submitted before generating payment")
            }
        
        # Check if payment already exists
        if filing.payment_entry:
            return {
                "status": "error",
                "message": _("Payment Entry already exists: {0}").format(filing.payment_entry)
            }
        
        # Check if this is a Kurang Bayar case
        tax_due_amount = get_tax_due_amount(filing)
        if tax_due_amount <= 0:
            return {
                "status": "error",
                "message": _("Payment Entry can only be created for Kurang Bayar filings with positive amount")
            }
        
        # Get bank and tax accounts
        company = filing.company
        bank_account = get_default_bank_account(company)
        tax_account = get_tax_account(company, filing.jenis_pelaporan)
        
        if not bank_account:
            return {
                "status": "error",
                "message": _("No default bank account found for {0}").format(company)
            }
        
        if not tax_account:
            return {
                "status": "error",
                "message": _("No tax account found for {0} and {1}").format(
                    company, filing.jenis_pelaporan
                )
            }
        
        # Create Payment Entry
        payment_entry = frappe.new_doc("Payment Entry")
        payment_entry.update({
            "payment_type": "Pay",
            "posting_date": nowdate(),
            "company": company,
            "mode_of_payment": "Bank Draft",  # Can be configured as needed
            "party_type": "Supplier",  # Tax office is treated as supplier
            "party": get_tax_office_supplier(company),
            "paid_from": bank_account,
            "paid_to": tax_account,
            "paid_amount": tax_due_amount,
            "received_amount": tax_due_amount,
            "reference_no": filing.name,
            "reference_date": nowdate(),
            "remarks": _("Tax payment for {0} {1}/{2}").format(
                filing.jenis_pelaporan, filing.masa_pajak, filing.tahun_pajak
            )
        })
        
        # Add custom fields for tax filing reference
        payment_entry.tax_filing_reference = filing.name
        payment_entry.tax_filing_type = filing.jenis_pelaporan
        
        # Save Payment Entry
        payment_entry.insert()
        
        # Update Tax Filing Summary
        filing.payment_entry = payment_entry.name
        filing.payment_status = "Sudah Dibayar"
        filing.payment_date = nowdate()
        filing.save()
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": _("Payment Entry {0} has been created").format(payment_entry.name),
            "payment_entry_id": payment_entry.name
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            message=f"Failed to create Payment Entry for Tax Filing {tax_filing_id}: {str(e)}",
            title="Tax Payment Creation Error"
        )
        return {
            "status": "error",
            "message": _("Failed to create Payment Entry: {0}").format(str(e))
        }

def get_tax_due_amount(filing):
    """
    Calculate tax due amount from Tax Filing Summary.
    
    Args:
        filing: Tax Filing Summary document
        
    Returns:
        float: Tax due amount
    """
    if filing.status_spt == "Kurang Bayar":
        # Sum up amounts from source documents based on filing type
        total_amount = 0
        
        if filing.jenis_pelaporan == "SPT Masa PPN":
            # For PPN, calculate output - input
            for doc in filing.source_documents:
                if doc.document_type == "Efaktur Document":
                    total_amount += flt(doc.amount)
                elif doc.document_type == "SPT Summary":
                    # If using SPT Summary, it already has net amount
                    total_amount += flt(doc.amount)
        
        elif "PPh" in filing.jenis_pelaporan:
            # For PPh, sum all amounts
            for doc in filing.source_documents:
                total_amount += flt(doc.amount)
        
        return total_amount
    
    return 0

def get_default_bank_account(company):
    """
    Get default bank account for company.
    
    Args:
        company: Company name
        
    Returns:
        str: Bank account code
    """
    # Try to get default account from Company
    default_bank = frappe.db.get_value("Company", company, "default_bank_account")
    if default_bank:
        return default_bank
    
    # If not found, get first Bank account
    bank_accounts = frappe.get_list(
        "Account",
        filters={
            "company": company,
            "account_type": "Bank",
            "is_group": 0
        },
        limit=1
    )
    
    if bank_accounts:
        return bank_accounts[0].name
    
    return None

def get_tax_account(company, tax_type):
    """
    Get appropriate tax account based on tax type.
    
    Args:
        company: Company name
        tax_type: Type of tax filing
        
    Returns:
        str: Tax account code
    """
    if "PPN" in tax_type:
        # For PPN, use PPN Output liability account
        return get_ppn_output_account(company)
    
    elif "PPh 21" in tax_type:
        # For PPh 21, use PPh 21 liability account
        return get_pph_account(company, "21")
    
    elif "PPh 23" in tax_type:
        return get_pph_account(company, "23")
    
    elif "PPh 26" in tax_type:
        return get_pph_account(company, "26")
    
    elif "PPh 4(2)" in tax_type:
        return get_pph_account(company, "4(2)")
    
    return None

def get_tax_office_supplier(company):
    """
    Get tax office supplier for company.
    
    Args:
        company: Company name
        
    Returns:
        str: Tax office supplier name
    """
    # Try to find supplier with "tax office" or "kantor pajak" in name
    tax_office_suppliers = frappe.get_list(
        "Supplier",
        filters={
            "disabled": 0
        },
        or_filters={
            "supplier_name": ["like", "%tax office%"],
            "supplier_name": ["like", "%kantor pajak%"],
            "supplier_name": ["like", "%direktorat jenderal pajak%"],
            "supplier_name": ["like", "%djp%"],
            "supplier_group": ["like", "%tax%"]
        },
        limit=1
    )
    
    if tax_office_suppliers:
        return tax_office_suppliers[0].name
    
    # If not found, create a new supplier
    try:
        supplier = frappe.new_doc("Supplier")
        supplier.supplier_name = "Direktorat Jenderal Pajak"
        supplier.supplier_group = "Tax Office"
        supplier.supplier_type = "Government"
        supplier.country = "Indonesia"
        supplier.insert(ignore_permissions=True)
        return supplier.name
    except:
        # If creation fails, return a default name
        return "Direktorat Jenderal Pajak"

# ... implement tax account retrieval functions ...
def get_ppn_output_account(company):
    """Get PPN Output account for company."""
    # First try to get from Tax Category
    ppn_account = frappe.db.get_value(
        "Tax Category Account",
        {"parent": "PPN", "company": company, "account_type": "Output"},
        "account"
    )
    
    # If not found, try to get from Account with PPN Output patterns
    if not ppn_account:
        ppn_accounts = frappe.get_list(
            "Account",
            filters={
                "company": company,
                "account_type": ["in", ["Tax", "Liability"]],
                "is_group": 0
            },
            or_filters={
                "account_name": ["like", "%ppn%out%"],
                "account_name": ["like", "%ppn%output%"],
                "account_name": ["like", "%vat%out%"],
                "account_name": ["like", "%pajak%keluar%"]
            },
            fields=["name"],
            limit=1
        )
        
        if ppn_accounts:
            ppn_account = ppn_accounts[0].name
    
    return ppn_account

def get_pph_account(company, pph_type):
    """Get PPh account for company by type."""
    # First try to get from Tax Category
    tax_category = f"PPh {pph_type}"
    pph_account = frappe.db.get_value(
        "Tax Category Account",
        {"parent": tax_category, "company": company},
        "account"
    )
    
    # If not found, try to get from Account with matching pattern
    if not pph_account:
        pattern = pph_type.replace("(", "\\(").replace(")", "\\)")
        search_patterns = [
            f"%pph%{pattern}%",
            f"%withholding%{pattern}%",
            f"%pajak%{pattern}%"
        ]
        
        or_filters = {}
        for i, pattern in enumerate(search_patterns):
            or_filters[f"account_name{i}"] = ["like", pattern]
            or_filters[f"name{i}"] = ["like", pattern]
        
        pph_accounts = frappe.get_list(
            "Account",
            filters={
                "company": company,
                "account_type": ["in", ["Tax", "Liability", "Payable"]],
                "is_group": 0
            },
            or_filters=or_filters,
            fields=["name"],
            limit=1
        )
        
        if pph_accounts:
            pph_account = pph_accounts[0].name
    
    return pph_account

class TaxFilingSummary(Document):
    def validate(self):
        self.validate_dates()
        self.validate_documents()
        self.update_document_details()
        self.validate_attachments()
    
    def validate_dates(self):
        """Validate posting and filing dates"""
        if self.tanggal_pelaporan and getdate(self.posting_date) > getdate(self.tanggal_pelaporan):
            frappe.throw("Filing Date cannot be before Posting Date")
    
    def validate_documents(self):
        """Validate source and payment documents"""
        if not self.source_documents:
            frappe.throw("At least one source document is required")
            
        if self.status_spt == "Kurang Bayar" and not self.payment_documents:
            frappe.throw("Payment documents are required for Kurang Bayar status")
    
    def update_document_details(self):
        """Update status and amount from source documents"""
        for doc in self.source_documents:
            if doc.document_type and doc.document_name:
                source = frappe.get_doc(doc.document_type, doc.document_name)
                
                # Update status
                doc.status = source.status if hasattr(source, 'status') else 'No Status'
                
                # Update amount based on document type
                if doc.document_type == "SPT Summary":
                    if "PPN" in self.jenis_pelaporan:
                        doc.amount = source.jumlah_ppn_penjualan - source.jumlah_ppn_pembelian
                    elif "PPh 21" in self.jenis_pelaporan:
                        doc.amount = source.jumlah_pph_21
                    elif "PPh 23" in self.jenis_pelaporan:
                        doc.amount = source.jumlah_pph_23
                    elif "PPh 26" in self.jenis_pelaporan:
                        doc.amount = source.jumlah_pph_26
                elif doc.document_type == "Efaktur Document":
                    doc.amount = source.jumlah_ppn
                elif doc.document_type == "Ebupot Document":
                    doc.amount = source.pph_dipotong
                elif doc.document_type == "Salary Slip":
                    doc.amount = source.total_tax_deducted
    
    def validate_attachments(self):
        """Validate required attachments"""
        if self.docstatus == 1:
            # Check for Tanda Terima attachment
            has_tanda_terima = False
            for attachment in (self.attachments or []):
                if attachment.attachment_type == "Tanda Terima":
                    has_tanda_terima = True
                    break
            
            if not has_tanda_terima:
                frappe.throw("Tanda Terima attachment is required for submission")
    
    def on_submit(self):
        """Update source documents on submission"""
        for doc in self.source_documents:
            if doc.document_type and doc.document_name:
                frappe.db.set_value(doc.document_type, doc.document_name, {
                    "status": "Filed",
                    "filing_reference": self.name,
                    "filing_date": self.tanggal_pelaporan
                })
    
    def on_cancel(self):
        """Revert source documents on cancellation"""
        for doc in self.source_documents:
            if doc.document_type and doc.document_name:
                frappe.db.set_value(doc.document_type, doc.document_name, {
                    "status": "Submitted",
                    "filing_reference": None,
                    "filing_date": None
                })