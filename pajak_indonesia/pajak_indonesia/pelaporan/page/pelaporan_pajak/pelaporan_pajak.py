import frappe
from frappe import _
from frappe.utils import getdate, flt, now, add_months
from frappe.utils import getdate, flt, add_months, get_last_day, format_date

@frappe.whitelist()
def get_tax_reporting_data(tahun, masa_pajak, pajak_type, company):
    """
    Get tax reporting data for the specified filters
    
    Args:
        tahun (str): Tax year
        masa_pajak (str): Tax month (01-12)
        pajak_type (str): Tax type (PPN, PPh 21, etc.)
        company (str): Company name
        
    Returns:
        dict: Data containing summary and documents
    """
    try:
        # Input validation
        if not all([tahun, masa_pajak, pajak_type, company]):
            frappe.throw(_("All filter parameters are required"))
            
        # Initialize return structure
        data = {
            "summary": {
                "status": _("Belum Lapor"),
                "tax_balance": 0
            },
            "documents": []
        }
        
        # Get period dates
        from_date, to_date = get_period_dates(tahun, masa_pajak)
        
        # Get existing Tax Filing Summary if any
        filing = get_existing_filing(tahun, masa_pajak, pajak_type, company)
        if filing:
            data["summary"]["filing_id"] = filing.name
            data["summary"]["status"] = filing.status_spt
            data["summary"]["payment_id"] = filing.payment_entry
            data["summary"]["adjustment_id"] = filing.adjustment_entry
        
        # Get documents and compute summary based on tax type
        tax_handler = TaxDataHandler.get_handler(pajak_type)
        if tax_handler:
            data = tax_handler.get_data(from_date, to_date, company, data)
        
        return data
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Tax Reporting Data Error: {str(e)}")
        return {
            "summary": {"error": str(e)},
            "documents": []
        }

def get_period_dates(tahun, masa_pajak):
    """
    Get start and end dates for the tax period
    
    Args:
        tahun (str): Year
        masa_pajak (str): Month (01-12)
        
    Returns:
        tuple: (from_date, to_date)
    """
    from_date = f"{tahun}-{masa_pajak}-01"
    to_date = get_last_day(from_date)
    return from_date, to_date

def get_existing_filing(tahun, masa_pajak, pajak_type, company):
    """
    Get existing Tax Filing Summary document if any
    
    Args:
        tahun (str): Year
        masa_pajak (str): Month
        pajak_type (str): Tax type
        company (str): Company name
        
    Returns:
        dict: Filing document if found, else None
    """
    filing_type = f"SPT Masa {pajak_type}"
    
    filings = frappe.get_all(
        "Tax Filing Summary",
        filters={
            "company": company,
            "jenis_pelaporan": filing_type,
            "masa_pajak": masa_pajak,
            "tahun_pajak": tahun,
            "docstatus": 1
        },
        fields=["name", "status_spt", "payment_entry", "adjustment_entry"],
        limit=1
    )
    
    return filings[0] if filings else None

@frappe.whitelist()
def generate_tax_filing(tahun, masa_pajak, pajak_type, company):
    """
    Create a new Tax Filing Summary
    
    Args:
        tahun (str): Year
        masa_pajak (str): Month
        pajak_type (str): Tax type
        company (str): Company name
        
    Returns:
        dict: Result with filing_id
    """
    try:
        # Check if filing already exists
        existing = get_existing_filing(tahun, masa_pajak, pajak_type, company)
        if existing:
            return {"status": "exists", "filing_id": existing.name}
        
        # Get tax data
        data = get_tax_reporting_data(tahun, masa_pajak, pajak_type, company)
        
        # Create new Tax Filing Summary
        filing = frappe.new_doc("Tax Filing Summary")
        filing.company = company
        filing.posting_date = getdate()
        filing.jenis_pelaporan = f"SPT Masa {pajak_type}"
        filing.masa_pajak = masa_pajak
        filing.tahun_pajak = tahun
        
        # Set status based on tax balance
        tax_balance = data["summary"].get("tax_balance", 0)
        if tax_balance > 0:
            filing.status_spt = "Kurang Bayar"
        elif tax_balance < 0:
            filing.status_spt = "Lebih Bayar"
        else:
            filing.status_spt = "Nihil"
        
        # Add source documents
        for doc in data["documents"]:
            filing.append("source_documents", {
                "document_type": doc["doctype"],
                "document_name": doc["docname"],
                "status": doc["status"],
                "amount": doc["tax_amount"]
            })
        
        # Save and submit
        filing.insert()
        filing.submit()
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "filing_id": filing.name
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), f"Tax Filing Generation Error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

# Tax Data Handler base class and implementations
class TaxDataHandler:
    @staticmethod
    def get_handler(tax_type):
        """Factory method to get appropriate tax handler"""
        handlers = {
            "PPN": PPNDataHandler(),
            "PPh 21": PPh21DataHandler(),
            "PPh 23": PPh23DataHandler(),
            "PPh 26": PPh26DataHandler()
        }
        return handlers.get(tax_type)
    
    def get_data(self, from_date, to_date, company, data):
        """Abstract method to be implemented by subclasses"""
        raise NotImplementedError

class PPNDataHandler(TaxDataHandler):
    def get_data(self, from_date, to_date, company, data):
        """Get PPN data for the specified period"""
        # Get PPN Output data
        ppn_out_amount = self.get_ppn_out_amount(from_date, to_date, company)
        data["summary"]["ppn_out"] = ppn_out_amount
        
        # Get PPN Input data
        ppn_in_amount = self.get_ppn_in_amount(from_date, to_date, company)
        data["summary"]["ppn_in"] = ppn_in_amount
        
        # Calculate tax balance (Kurang/Lebih Bayar)
        data["summary"]["tax_balance"] = ppn_out_amount - ppn_in_amount
        
        # Get documents
        data["documents"] = self.get_ppn_documents(from_date, to_date, company)
        
        return data
    
    def get_ppn_out_amount(self, from_date, to_date, company):
        """Get total PPN Output amount for the period"""
        # First try to get from GL Entries with tax_type=PPN_OUT
        ppn_amount = self.get_tax_gl_sum("PPN_OUT", from_date, to_date, company)
        
        # If no amount from GL, try from Sales Invoices
        if ppn_amount == 0:
            sales_taxes = frappe.db.sql("""
                SELECT SUM(tax.tax_amount) as tax_amount
                FROM `tabSales Invoice` si
                JOIN `tabSales Taxes and Charges` tax ON tax.parent = si.name
                WHERE si.posting_date BETWEEN %s AND %s
                AND si.company = %s
                AND si.docstatus = 1
                AND (
                    tax.account_head LIKE %s OR
                    tax.account_head LIKE %s OR
                    tax.account_head LIKE %s
                )
            """, (from_date, to_date, company, '%PPN%', '%Output%', '%Keluaran%'), as_dict=1)
            
            if sales_taxes and sales_taxes[0].tax_amount:
                ppn_amount = flt(sales_taxes[0].tax_amount)
        
        return ppn_amount
    
    def get_ppn_in_amount(self, from_date, to_date, company):
        """Get total PPN Input amount for the period"""
        # First try to get from GL Entries with tax_type=PPN_IN
        ppn_amount = self.get_tax_gl_sum("PPN_IN", from_date, to_date, company)
        
        # If no amount from GL, try from Purchase Invoices
        if ppn_amount == 0:
            purchase_taxes = frappe.db.sql("""
                SELECT SUM(tax.tax_amount) as tax_amount
                FROM `tabPurchase Invoice` pi
                JOIN `tabPurchase Taxes and Charges` tax ON tax.parent = pi.name
                WHERE pi.posting_date BETWEEN %s AND %s
                AND pi.company = %s
                AND pi.docstatus = 1
                AND (
                    tax.account_head LIKE %s OR
                    tax.account_head LIKE %s OR
                    tax.account_head LIKE %s
                )
            """, (from_date, to_date, company, '%PPN%', '%Input%', '%Masukan%'), as_dict=1)
            
            if purchase_taxes and purchase_taxes[0].tax_amount:
                ppn_amount = flt(purchase_taxes[0].tax_amount)
        
        return ppn_amount
    
    def get_tax_gl_sum(self, tax_type, from_date, to_date, company):
        """Get sum of tax amounts from GL entries"""
        gl_entries = frappe.db.sql("""
            SELECT 
                SUM(credit) as credit,
                SUM(debit) as debit
            FROM `tabGL Entry`
            WHERE posting_date BETWEEN %s AND %s
            AND company = %s
            AND tax_type = %s
            AND is_cancelled = 0
        """, (from_date, to_date, company, tax_type), as_dict=1)
        
        if not gl_entries or not gl_entries[0]:
            return 0
            
        if tax_type == "PPN_OUT":
            return flt(gl_entries[0].credit)
        else:
            return flt(gl_entries[0].debit)
    
    def get_ppn_documents(self, from_date, to_date, company):
        """Get PPN-related documents for the period"""
        documents = []
        
        # Get E-Faktur documents
        efaktur_docs = frappe.get_all(
            "Efaktur Document",
            filters={
                "company": company,
                "tanggal_faktur": ["between", [from_date, to_date]],
                "docstatus": 1
            },
            fields=[
                "name as docname", 
                "'Efaktur Document' as doctype",
                "tanggal_faktur as posting_date",
                "status",
                "jumlah_dpp as base_amount",
                "jumlah_ppn as tax_amount",
                "nama as party"
            ]
        )
        documents.extend(efaktur_docs)
        
        # Get Sales Invoices with PPN
        sales_invoices = frappe.db.sql("""
            SELECT 
                si.name as docname,
                'Sales Invoice' as doctype,
                si.posting_date,
                si.status,
                si.base_net_total as base_amount,
                SUM(tax.tax_amount) as tax_amount,
                si.customer as party
            FROM `tabSales Invoice` si
            JOIN `tabSales Taxes and Charges` tax ON tax.parent = si.name
            WHERE si.posting_date BETWEEN %s AND %s
            AND si.company = %s
            AND si.docstatus = 1
            AND (
                tax.account_head LIKE %s OR
                tax.account_head LIKE %s OR
                tax.account_head LIKE %s
            )
            GROUP BY si.name
        """, (from_date, to_date, company, '%PPN%', '%Output%', '%Keluaran%'), as_dict=1)
        
        # Only add sales invoices not already covered by e-faktur
        efaktur_refs = [d.get('reference_name') for d in frappe.get_all(
            "Efaktur Document", 
            filters={"reference_doctype": "Sales Invoice"},
            fields=["reference_name"]
        )]
        
        for si in sales_invoices:
            if si.docname not in efaktur_refs:
                documents.append(si)
        
        # Get Purchase Invoices with PPN
        purchase_invoices = frappe.db.sql("""
            SELECT 
                pi.name as docname,
                'Purchase Invoice' as doctype,
                pi.posting_date,
                pi.status,
                pi.base_net_total as base_amount,
                SUM(tax.tax_amount) as tax_amount,
                pi.supplier as party
            FROM `tabPurchase Invoice` pi
            JOIN `tabPurchase Taxes and Charges` tax ON tax.parent = pi.name
            WHERE pi.posting_date BETWEEN %s AND %s
            AND pi.company = %s
            AND pi.docstatus = 1
            AND (
                tax.account_head LIKE %s OR
                tax.account_head LIKE %s OR
                tax.account_head LIKE %s
            )
            GROUP BY pi.name
        """, (from_date, to_date, company, '%PPN%', '%Input%', '%Masukan%'), as_dict=1)
        documents.extend(purchase_invoices)
        
        return documents

class PPh21DataHandler(TaxDataHandler):
    def get_data(self, from_date, to_date, company, data):
        """Get PPh 21 data for the specified period"""
        # Get Salary Slips with PPh 21
        salary_slips = frappe.get_all(
            "Salary Slip",
            filters={
                "company": company,
                "posting_date": ["between", [from_date, to_date]],
                "docstatus": 1,
                "total_tax_deducted": [">", 0]
            },
            fields=[
                "name as docname", 
                "'Salary Slip' as doctype",
                "posting_date",
                "status",
                "gross_pay as base_amount",
                "total_tax_deducted as tax_amount",
                "employee_name as party"
            ]
        )
        
        # Compute summary
        total_income = sum(flt(slip.base_amount) for slip in salary_slips)
        total_tax = sum(flt(slip.tax_amount) for slip in salary_slips)
        
        data["summary"]["income_amount"] = total_income
        data["summary"]["tax_amount"] = total_tax
        data["summary"]["tax_balance"] = total_tax  # For PPh 21, balance is just the tax amount
        data["summary"]["document_count"] = len(salary_slips)
        data["documents"] = salary_slips
        
        return data

class PPh23DataHandler(TaxDataHandler):
    def get_data(self, from_date, to_date, company, data):
        """Get PPh 23 data for the specified period"""
        # Get E-Bupot documents for PPh 23
        ebupot_docs = frappe.get_all(
            "Ebupot Document",
            filters={
                "company": company,
                "jenis_pajak": "23",
                "tandatangan_date": ["between", [from_date, to_date]],
                "docstatus": 1
            },
            fields=[
                "name as docname", 
                "'Ebupot Document' as doctype",
                "tandatangan_date as posting_date",
                "status",
                "penghasilan_bruto as base_amount",
                "pph_dipotong as tax_amount",
                "nama_terpotong as party"
            ]
        )
        
        # Compute summary
        total_income = sum(flt(doc.base_amount) for doc in ebupot_docs)
        total_tax = sum(flt(doc.tax_amount) for doc in ebupot_docs)
        
        data["summary"]["income_amount"] = total_income
        data["summary"]["tax_amount"] = total_tax
        data["summary"]["tax_balance"] = total_tax
        data["summary"]["document_count"] = len(ebupot_docs)
        data["documents"] = ebupot_docs
        
        return data

class PPh26DataHandler(TaxDataHandler):
    def get_data(self, from_date, to_date, company, data):
        """Get PPh 26 data for the specified period"""
        # Get E-Bupot documents for PPh 26
        ebupot_docs = frappe.get_all(
            "Ebupot Document",
            filters={
                "company": company,
                "jenis_pajak": "26",
                "tandatangan_date": ["between", [from_date, to_date]],
                "docstatus": 1
            },
            fields=[
                "name as docname", 
                "'Ebupot Document' as doctype",
                "tandatangan_date as posting_date",
                "status",
                "penghasilan_bruto as base_amount",
                "pph_dipotong as tax_amount",
                "nama_terpotong as party"
            ]
        )
        
        # Compute summary
        total_income = sum(flt(doc.base_amount) for doc in ebupot_docs)
        total_tax = sum(flt(doc.tax_amount) for doc in ebupot_docs)
        
        data["summary"]["income_amount"] = total_income
        data["summary"]["tax_amount"] = total_tax
        data["summary"]["tax_balance"] = total_tax
        data["summary"]["document_count"] = len(ebupot_docs)
        data["documents"] = ebupot_docs
        
        return data
