from typing import Optional
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt, get_datetime

def create_document(doc: Document, method: Optional[str] = None) -> Optional[Document]:
    """
    Create Efaktur document from Sales Invoice on submission.
    
    Args:
        doc: The submitted Sales Invoice document
        method: The triggered method name (e.g. 'on_submit')
    
    Returns:
        Optional[Document]: The created Efaktur Document or None if skipped
        
    Example:
        doc_events = {
            "Sales Invoice": {
                "on_submit": "pajak_indonesia.efaktur.utils.create_document"
            }
        }
    """
    # Check if valid Sales Invoice
    if not doc.doctype == "Sales Invoice" or doc.docstatus != 1:
        return None
        
    # Skip if e-Faktur already exists
    if doc.get("has_generated_efaktur"):
        frappe.msgprint(_("E-Faktur already generated for this invoice"))
        return None
    
    # Skip if no taxes
    if not doc.taxes:
        frappe.msgprint(_("No taxes found in invoice. Skipping e-Faktur generation."))
        return None
    
    # Find PPN in taxes
    ppn_amount = 0
    ppn_account = get_ppn_account(doc.company)
    
    for tax in doc.taxes:
        if tax.account_head == ppn_account:
            ppn_amount = tax.tax_amount
            break
    
    # Skip if no PPN found
    if not ppn_amount:
        frappe.msgprint(_("No PPN tax found in invoice. Skipping e-Faktur generation."))
        return None
    
    try:
        # Get next available nomor faktur
        nomor_faktur = get_next_nomor_faktur(doc.company)
        if not nomor_faktur:
            frappe.msgprint(_("No available faktur number. Please update Efaktur Config."))
            return None
        
        # Extract fiscal period
        posting_date = getdate(doc.posting_date)
        masa_pajak = posting_date.strftime("%m")
        tahun_pajak = posting_date.strftime("%Y")
        
        # Get customer details
        customer_doc = frappe.get_doc("Customer", doc.customer)
        npwp = customer_doc.get("tax_id") or "000000000000000"
        
        # Create Efaktur Document
        efaktur = frappe.new_doc("Efaktur Document")
        efaktur.update({
            "kode_jenis_transaksi": "01",  # Default to standard sale
            "fg_pengganti": "0",           # Default to not replacement
            "nomor_faktur": nomor_faktur,
            "masa_pajak": masa_pajak,
            "tahun_pajak": tahun_pajak,
            "tanggal_faktur": doc.posting_date,
            "npwp": npwp,
            "nama": doc.customer_name,
            "alamat_lengkap": doc.address_display or customer_doc.get("address") or "Indonesia",
            "referensi": doc.name,
            "fg_uang_muka": "0"            # Default to not advance payment
        })
        
        # Set DPP and PPN details
        base_grand_total = doc.base_grand_total - ppn_amount
        
        # Add invoice items
        for item in doc.items:
            # Calculate item's contribution to total
            item_ratio = flt(item.base_amount) / flt(doc.base_net_total) if doc.base_net_total else 0
            
            # Calculate item's share of DPP and PPN
            item_dpp = flt(base_grand_total) * item_ratio
            item_ppn = flt(ppn_amount) * item_ratio
            
            efaktur.append("items", {
                "nama_barang": item.item_name or item.item_code,
                "harga_satuan": item.base_rate,
                "jumlah_barang": item.qty,
                "harga_total": item.base_amount,
                "dpp": item_dpp,
                "ppn": item_ppn
            })
        
        # Set document links
        efaktur.reference_doctype = doc.doctype
        efaktur.reference_name = doc.name
        
        # Save and submit document
        efaktur.insert()
        
        # Update original invoice
        frappe.db.set_value("Sales Invoice", doc.name, "has_generated_efaktur", 1)
        frappe.db.commit()
        
        frappe.msgprint(_("E-Faktur document {0} has been created").format(
            frappe.bold(efaktur.name)))
        
        return efaktur
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create E-Faktur document for {doc.name}: {str(e)}",
            title="E-Faktur Creation Error"
        )
        frappe.msgprint(_("Failed to create E-Faktur document: {0}").format(str(e)))
        return None

def get_ppn_account(company: str) -> Optional[str]:
    """
    Get PPN Output account for company.
    
    Args:
        company: Company name
        
    Returns:
        Optional[str]: Account head for PPN Output or None if not found
    """
    # First try to get from Tax Category
    ppn_account = frappe.db.get_value(
        "Tax Category Account",
        {"parent": "PPN", "company": company},
        "account"
    )
    
    # If not found, try to get from Account with 'ppn_out' in account_name or account_number
    if not ppn_account:
        ppn_accounts = frappe.get_list(
            "Account",
            filters={
                "company": company,
                "account_type": "Tax",
                "is_group": 0
            },
            or_filters={
                "account_name": ["like", "%ppn%out%"],
                "account_name": ["like", "%ppn%output%"],
                "account_name": ["like", "%vat%out%"],
                "account_name": ["like", "%pajak%keluar%"],
                "name": ["like", "%ppn%out%"]
            },
            fields=["name"],
            limit=1
        )
        
        if ppn_accounts:
            ppn_account = ppn_accounts[0].name
    
    return ppn_account

def get_next_nomor_faktur(company: str) -> Optional[str]:
    """
    Get next available faktur number from Efaktur Config.
    
    Args:
        company: Company name
        
    Returns:
        Optional[str]: Next available faktur number or None if not available
    """
    # Get config for the company
    config = frappe.get_all(
        "Efaktur Config",
        filters={"company": company, "is_active": 1},
        fields=["name", "current_prefix", "current_start", "current_end", "next_number"],
        limit=1
    )
    
    if not config:
        return None
    
    config = config[0]
    
    # Check if numbers are still available
    if int(config.next_number) > int(config.current_end):
        return None
    
    # Format faktur number according to DJP standard (with dots and dash)
    prefix = config.current_prefix
    next_number = config.next_number.zfill(8)
    nomor_faktur = f"{prefix}.{next_number[:3]}.{next_number[3:6]}.{next_number[6:]}"
    
    # Update next number
    next_number_int = int(config.next_number) + 1
    frappe.db.set_value(
        "Efaktur Config",
        config.name,
        "next_number",
        str(next_number_int).zfill(8)
    )
    
    return nomor_faktur