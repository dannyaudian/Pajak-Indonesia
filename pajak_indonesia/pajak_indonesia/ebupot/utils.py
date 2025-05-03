from typing import Optional, List, Dict, Any
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, flt, cstr, add_months

def create_document_if_pph(doc: Document, method: Optional[str] = None) -> Optional[Document]:
    if not doc.doctype == "Purchase Invoice":
        return None
    if doc.docstatus == 0 or doc.docstatus == 2:
        return None
    existing_ebupot = frappe.get_all(
        "Ebupot Document",
        filters={"reference_doctype": doc.doctype, "reference_name": doc.name},
        limit=1
    )
    if existing_ebupot:
        frappe.msgprint(_("E-Bupot document already exists for this invoice"))
        return None
    pph_taxes = get_pph_taxes(doc)
    if not pph_taxes:
        return None
    try:
        created_docs = []
        for pph_type, tax_details in pph_taxes.items():
            ebupot_doc = create_ebupot_document(doc, pph_type, tax_details)
            if ebupot_doc:
                created_docs.append(ebupot_doc)
        if created_docs:
            msg = _("E-Bupot document(s) created: {0}").format(
                ", ".join([f'<a href="/app/ebupot-document/{d.name}">{d.name}</a>' for d in created_docs])
            )
            frappe.msgprint(msg, title=_("E-Bupot Created"), indicator="green")
            return created_docs[0]
        return None
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create E-Bupot document for {doc.name}: {str(e)}",
            title="E-Bupot Creation Error"
        )
        frappe.msgprint(_("Failed to create E-Bupot document: {0}").format(str(e)))
        return None

def get_pph_taxes(doc: Document) -> Dict[str, Dict[str, Any]]:
    result = {}
    if not doc.taxes:
        return result
    pph23_account = get_pph_account(doc.company, "23")
    pph26_account = get_pph_account(doc.company, "26")
    for tax in doc.taxes:
        tax_amount = flt(tax.tax_amount)
        base_amount = flt(doc.base_net_total)
        if tax_amount >= 0:
            continue
        if pph23_account and tax.account_head == pph23_account:
            tax_rate = abs(flt(tax_amount) * 100 / base_amount) if base_amount else 0
            result["23"] = {
                "account": tax.account_head,
                "rate": tax_rate,
                "amount": abs(tax_amount),
                "base_amount": base_amount,
                "description": tax.description or "PPh 23"
            }
        elif pph26_account and tax.account_head == pph26_account:
            tax_rate = abs(flt(tax_amount) * 100 / base_amount) if base_amount else 0
            result["26"] = {
                "account": tax.account_head,
                "rate": tax_rate,
                "amount": abs(tax_amount),
                "base_amount": base_amount,
                "description": tax.description or "PPh 26"
            }
        elif tax.description and ("pph 23" in tax.description.lower() or "withholding" in tax.description.lower()):
            tax_rate = abs(flt(tax_amount) * 100 / base_amount) if base_amount else 0
            result["23"] = {
                "account": tax.account_head,
                "rate": tax_rate,
                "amount": abs(tax_amount),
                "base_amount": base_amount,
                "description": tax.description
            }
        elif tax.description and "pph 26" in tax.description.lower():
            tax_rate = abs(flt(tax_amount) * 100 / base_amount) if base_amount else 0
            result["26"] = {
                "account": tax.account_head,
                "rate": tax_rate,
                "amount": abs(tax_amount),
                "base_amount": base_amount,
                "description": tax.description
            }
    return result

def get_pph_account(company: str, pph_type: str) -> Optional[str]:
    tax_category = f"PPh {pph_type}"
    pph_account = frappe.db.get_value(
        "Tax Category Account",
        {"parent": tax_category, "company": company},
        "account"
    )
    if not pph_account:
        search_patterns = [
            f"%pph%{pph_type}%",
            f"%withholding%{pph_type}%",
            f"%pajak%{pph_type}%"
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

def create_ebupot_document(doc: Document, pph_type: str, tax_details: Dict[str, Any]) -> Optional[Document]:
    supplier_doc = frappe.get_doc("Supplier", doc.supplier)
    npwp = supplier_doc.get("tax_id") or "000000000000000"
    posting_date = getdate(doc.posting_date)
    masa_pajak = posting_date.strftime("%m")
    tahun_pajak = posting_date.strftime("%Y")
    ebupot = frappe.new_doc("Ebupot Document")
    ebupot.update({
        "jenis_pajak": pph_type,
        "jenis_daftar": "0 - Normal",
        "masa_pajak": masa_pajak,
        "tahun_pajak": tahun_pajak,
        "tandatangan_date": posting_date,
        "npwp_pemotong": frappe.db.get_value("Company", doc.company, "tax_id") or "000000000000000",
        "nama_pemotong": doc.company,
        "alamat_pemotong": get_company_address(doc.company),
        "npwp_terpotong": npwp,
        "nama_terpotong": doc.supplier_name or doc.supplier,
        "alamat_terpotong": doc.address_display or get_supplier_address(doc.supplier),
        "tin": "" if pph_type == "23" else (supplier_doc.get("tax_id") or ""),
        "negara_domisili": "" if pph_type == "23" else (supplier_doc.get("country") or ""),
        "penghasilan_bruto": tax_details["base_amount"],
        "tarif": tax_details["rate"],
        "pph_dipotong": tax_details["amount"],
        "status": "Draft",
        "reference_doctype": doc.doctype,
        "reference_name": doc.name
    })
    add_income_types(ebupot, doc, pph_type, tax_details)
    ebupot.insert()
    return ebupot

def add_income_types(ebupot: Document, doc: Document, pph_type: str, tax_details: Dict[str, Any]) -> None:
    default_code = get_default_object_code(pph_type)
    if len(doc.items) == 1:
        item = doc.items[0]
        item_description = item.description or item.item_name or item.item_code
        ebupot.append("items", {
            "kode_objek_pajak": default_code,
            "jenis_penghasilan": item_description[:100],
            "dasar_pengenaan_pajak": tax_details["base_amount"],
            "tarif": tax_details["rate"],
            "pph_dipotong": tax_details["amount"]
        })
    else:
        is_service = any(item.get("is_service_item", 0) for item in doc.items)
        description = "Jasa" if is_service else "Barang"
        if pph_type == "23":
            description += " (PPh 23)"
        else:
            description += " (PPh 26)"
        ebupot.append("items", {
            "kode_objek_pajak": default_code,
            "jenis_penghasilan": description,
            "dasar_pengenaan_pajak": tax_details["base_amount"],
            "tarif": tax_details["rate"],
            "pph_dipotong": tax_details["amount"]
        })

def get_default_object_code(pph_type: str) -> str:
    if pph_type == "23":
        return "23-100-01"
    else:
        return "26-100-01"
def get_company_address(company: str) -> str:
    address = frappe.db.get_value("Company", company, "address")
    if not address:
        address = "Indonesia"
    return address

def get_supplier_address(supplier: str) -> str:
    address_name = frappe.db.get_value(
        "Dynamic Link",
        {"link_doctype": "Supplier", "link_name": supplier, "parenttype": "Address"},
        "parent"
    )
    if address_name:
        address = frappe.get_doc("Address", address_name)
        return address.get_display()
    return "Indonesia"

def link_deduction_to_bupot(doc: Document, method: Optional[str] = None) -> None:
    if not doc.doctype == "Payment Entry":
        return
    if doc.party_type != "Supplier":
        return
    if not doc.deductions or len(doc.deductions) == 0:
        return
    for deduction in doc.deductions:
        if deduction.get("ebupot_document"):
            continue
        if is_pph_account(deduction.account, doc.company):
            ebupot_doc = find_matching_ebupot(doc, deduction)
            if ebupot_doc:
                deduction.ebupot_document = ebupot_doc.name
                if doc.docstatus == 1 and not ebupot_doc.payment_entry:
                    frappe.db.set_value("Ebupot Document", ebupot_doc.name, {
                        "payment_entry": doc.name,
                        "payment_date": doc.posting_date,
                        "status": "Paid"
                    })
                    frappe.msgprint(_("Payment linked to E-Bupot document {0}").format(
                        frappe.bold(ebupot_doc.name)))
            else:
                frappe.log_error(
                    message=f"Could not find matching E-Bupot document for Payment Entry {doc.name}, "
                            f"Supplier: {doc.party}, Amount: {deduction.amount}",
                    title="E-Bupot Payment Linking Warning"
                )

def is_pph_account(account: str, company: str) -> bool:
    pph23_account = get_pph_account(company, "23")
    pph26_account = get_pph_account(company, "26")
    pph21_account = get_pph_account(company, "21")
    if account in [pph23_account, pph26_account, pph21_account]:
        return True
    account_name = frappe.db.get_value("Account", account, "account_name") or ""
    lower_name = account_name.lower()
    pph_keywords = ["pph", "withholding", "pajak penghasilan"]
    has_pph_keyword = any(keyword in lower_name for keyword in pph_keywords)
    pph_types = ["23", "26", "21", "pasal 23", "pasal 26", "pasal 21"]
    has_pph_type = any(pph_type in lower_name for pph_type in pph_types)
    return has_pph_keyword and has_pph_type

def find_matching_ebupot(payment_entry: Document, deduction: Dict[str, Any]) -> Optional[Document]:
    references = []
    if hasattr(payment_entry, 'references') and payment_entry.references:
        for ref in payment_entry.references:
            if ref.reference_doctype == "Purchase Invoice":
                references.append(ref.reference_name)
    if references:
        ebupot_docs = frappe.get_all(
            "Ebupot Document",
            filters={
                "reference_doctype": "Purchase Invoice",
                "reference_name": ["in", references],
                "docstatus": 1
            },
            fields=["name", "pph_dipotong", "payment_entry"],
            order_by="modified desc"
        )
        if ebupot_docs:
            for ebupot in ebupot_docs:
                if abs(flt(ebupot.pph_dipotong) - flt(deduction.amount)) < 1.0:
                    return frappe.get_doc("Ebupot Document", ebupot.name)
    supplier = payment_entry.party
    amount = flt(deduction.amount)
    posting_date = getdate(payment_entry.posting_date)
    month = posting_date.strftime("%m")
    year = posting_date.strftime("%Y")
    ebupot_docs = frappe.get_all(
        "Ebupot Document",
        filters={
            "nama_terpotong": ["like", f"%{supplier}%"],
            "masa_pajak": month,
            "tahun_pajak": year,
            "docstatus": 1,
            "payment_entry": ["in", ["", None]]
        },
        fields=["name", "pph_dipotong", "npwp_terpotong", "payment_entry"],
        order_by="modified desc"
    )
    for ebupot in ebupot_docs:
        if abs(flt(ebupot.pph_dipotong) - amount) < 1.0:
            return frappe.get_doc("Ebupot Document", ebupot.name)
    date_from = add_months(posting_date, -3)
    date_to = add_months(posting_date, 3)
    months_range = []
    current_date = date_from
    while current_date <= date_to:
        months_range.append(current_date.strftime("%m"))
        current_date = add_months(current_date, 1)
    years_range = [str(date_from.year), str(posting_date.year)]
    if date_to.year not in years_range:
        years_range.append(str(date_to.year))
    ebupot_docs = frappe.get_all(
        "Ebupot Document",
        filters={
            "nama_terpotong": ["like", f"%{supplier}%"],
            "masa_pajak": ["in", months_range],
            "tahun_pajak": ["in", years_range],
            "docstatus": 1,
            "payment_entry": ["in", ["", None]]
        },
        fields=["name", "pph_dipotong", "npwp_terpotong", "payment_entry"],
        order_by="modified desc"
    )
    for ebupot in ebupot_docs:
        if abs(flt(ebupot.pph_dipotong) - amount) < 1.0:
            return frappe.get_doc("Ebupot Document", ebupot.name)
    return None
    pph26_account = get_pph_account(company, "26")
    pph21_account = get_pph_account(company, "21")
    if account in [pph23_account, pph26_account, pph21_account]:
        return True
    account_name = frappe.db.get_value("Account", account, "account_name") or ""
    lower_name = account_name.lower()
    pph_keywords = ["pph", "withholding", "pajak penghasilan"]
