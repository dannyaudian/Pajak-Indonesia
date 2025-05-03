import frappe
from frappe import _
import json
import csv
import io
from frappe.utils import getdate, flt, add_months, formatdate

def get_dashboard_data(filters=None):
    """
    Get data for the Pajak Indonesia dashboard
    
    Args:
        filters: Optional filter parameters
        
    Returns:
        dict: Dashboard data including charts and report data
    """
    if not filters:
        filters = {}
    
    company = filters.get('company') or frappe.defaults.get_user_default('Company')
    year = filters.get('year') or getdate().year
    
    return {
        "charts": [
            get_ppn_comparison_chart(company, year),
            get_filing_status_chart(company, year),
            get_monthly_tax_chart(company, year)
        ],
        "number_cards": get_number_cards(company, year),
        "shortcuts": get_shortcuts(),
        "export_functions": get_export_functions()
    }

def get_ppn_comparison_chart(company, year):
    """
    Get PPN In vs PPN Out bar chart
    
    Args:
        company: Company name
        year: Year for data
        
    Returns:
        dict: Chart configuration
    """
    # Get monthly PPN data
    months = []
    ppn_out_data = []
    ppn_in_data = []
    
    for month in range(1, 13):
        # Format month for display
        month_str = formatdate(f"{year}-{month:02d}-01", "MMM")
        months.append(month_str)
        
        # Get PPN Out for the month
        from_date = f"{year}-{month:02d}-01"
        to_date = add_months(getdate(from_date), 1)
        
        ppn_out = get_ppn_amount(company, from_date, to_date, "out")
        ppn_in = get_ppn_amount(company, from_date, to_date, "in")
        
        ppn_out_data.append(ppn_out)
        ppn_in_data.append(ppn_in)
    
    return {
        "name": "ppn_comparison_chart",
        "chart_name": _("PPN Comparison"),
        "chart_type": "bar",
        "data": {
            "labels": months,
            "datasets": [
                {
                    "name": _("PPN Keluaran"),
                    "values": ppn_out_data
                },
                {
                    "name": _("PPN Masukan"),
                    "values": ppn_in_data
                }
            ]
        },
        "colors": ["#ff5858", "#5858ff"],
        "type": "axis-mixed",
        "height": 300
    }

def get_filing_status_chart(company, year):
    """
    Get Pie chart of tax filing status
    
    Args:
        company: Company name
        year: Year for data
        
    Returns:
        dict: Chart configuration
    """
    # Get filing status counts
    filings = frappe.db.sql("""
        SELECT 
            status_spt, 
            COUNT(*) as count
        FROM `tabTax Filing Summary`
        WHERE company = %s
        AND tahun_pajak = %s
        AND docstatus = 1
        GROUP BY status_spt
    """, (company, str(year)), as_dict=1)
    
    # Prepare data for pie chart
    labels = []
    values = []
    
    # Default status categories
    status_map = {
        "Nihil": 0,
        "Kurang Bayar": 0,
        "Lebih Bayar": 0
    }
    
    # Update with actual counts
    for filing in filings:
        status = filing.status_spt or "Lainnya"
        if status in status_map:
            status_map[status] = filing.count
        else:
            status_map[status] = filing.count
    
    # Convert to lists for chart
    for status, count in status_map.items():
        labels.append(_(status))
        values.append(count)
    
    return {
        "name": "filing_status_chart",
        "chart_name": _("Filing Status"),
        "chart_type": "pie",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "values": values
                }
            ]
        },
        "colors": ["#28a745", "#ff5858", "#5858ff"],
        "height": 300
    }

def get_monthly_tax_chart(company, year):
    """
    Get monthly tax amounts line chart
    
    Args:
        company: Company name
        year: Year for data
        
    Returns:
        dict: Chart configuration
    """
    # Get monthly tax data for various tax types
    months = []
    ppn_data = []
    pph21_data = []
    pph23_data = []
    
    for month in range(1, 13):
        # Format month for display
        month_str = formatdate(f"{year}-{month:02d}-01", "MMM")
        months.append(month_str)
        
        # Get tax amounts for each type
        from_date = f"{year}-{month:02d}-01"
        to_date = add_months(getdate(from_date), 1)
        
        # PPN (Out - In)
        ppn_out = get_ppn_amount(company, from_date, to_date, "out")
        ppn_in = get_ppn_amount(company, from_date, to_date, "in")
        ppn_net = ppn_out - ppn_in
        ppn_data.append(ppn_net)
        
        # PPh 21
        pph21 = get_pph_amount(company, from_date, to_date, "21")
        pph21_data.append(pph21)
        
        # PPh 23
        pph23 = get_pph_amount(company, from_date, to_date, "23")
        pph23_data.append(pph23)
    
    return {
        "name": "monthly_tax_chart",
        "chart_name": _("Monthly Tax Amounts"),
        "chart_type": "line",
        "data": {
            "labels": months,
            "datasets": [
                {
                    "name": _("PPN"),
                    "values": ppn_data
                },
                {
                    "name": _("PPh 21"),
                    "values": pph21_data
                },
                {
                    "name": _("PPh 23"),
                    "values": pph23_data
                }
            ]
        },
        "colors": ["#ff5858", "#5858ff", "#58ff58"],
        "type": "axis-mixed",
        "height": 300
    }

def get_number_cards(company, year):
    """
    Get number cards for the dashboard
    
    Args:
        company: Company name
        year: Year for data
        
    Returns:
        list: Number card configurations
    """
    # Get current month
    current_month = getdate().month
    from_date = f"{year}-01-01"
    to_date = f"{year}-12-31"
    
    # Get YTD tax amounts
    ppn_out_ytd = get_ppn_amount(company, from_date, to_date, "out")
    ppn_in_ytd = get_ppn_amount(company, from_date, to_date, "in")
    ppn_net_ytd = ppn_out_ytd - ppn_in_ytd
    
    pph21_ytd = get_pph_amount(company, from_date, to_date, "21")
    pph23_ytd = get_pph_amount(company, from_date, to_date, "23")
    
    # Count documents
    efaktur_count = frappe.db.count("Efaktur Document", {
        "company": company,
        "tahun_pajak": str(year),
        "docstatus": 1
    })
    
    ebupot_count = frappe.db.count("Ebupot Document", {
        "company": company,
        "tahun_pajak": str(year),
        "docstatus": 1
    })
    
    return [
        {
            "name": "ppn_ytd",
            "label": _("PPN YTD"),
            "value": ppn_net_ytd,
            "indicator": "blue",
            "suffix": frappe.defaults.get_user_default("currency")
        },
        {
            "name": "pph21_ytd",
            "label": _("PPh 21 YTD"),
            "value": pph21_ytd,
            "indicator": "blue",
            "suffix": frappe.defaults.get_user_default("currency")
        },
        {
            "name": "pph23_ytd",
            "label": _("PPh 23 YTD"),
            "value": pph23_ytd,
            "indicator": "blue",
            "suffix": frappe.defaults.get_user_default("currency")
        },
        {
            "name": "efaktur_count",
            "label": _("E-Faktur Count"),
            "value": efaktur_count,
            "indicator": "green"
        },
        {
            "name": "ebupot_count",
            "label": _("E-Bupot Count"),
            "value": ebupot_count,
            "indicator": "green"
        }
    ]

def get_shortcuts():
    """
    Get shortcuts for the dashboard
    
    Returns:
        list: Shortcut configurations
    """
    return [
        {
            "label": _("Tax Filing Summary"),
            "icon": "tax",
            "route": "List/Tax Filing Summary/List",
            "description": _("View Tax Filing Summaries")
        },
        {
            "label": _("E-Faktur"),
            "icon": "invoice",
            "route": "List/Efaktur Document/List",
            "description": _("Manage E-Faktur documents")
        },
        {
            "label": _("E-Bupot"),
            "icon": "note",
            "route": "List/Ebupot Document/List",
            "description": _("Manage E-Bupot documents")
        },
        {
            "label": _("Pelaporan Pajak"),
            "icon": "report",
            "route": "pelaporan-pajak",
            "description": _("Tax reporting tool")
        }
    ]

def get_export_functions():
    """
    Get export function configurations
    
    Returns:
        list: Export function configurations
    """
    return [
        {
            "label": _("Export E-Faktur"),
            "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.make_csv_efaktur",
            "icon": "download"
        },
        {
            "label": _("Export E-Bupot"),
            "function": "pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.make_csv_ebupot",
            "icon": "download"
        }
    ]

@frappe.whitelist()
def make_csv_efaktur(filters=None):
    """
    Generate CSV export of E-Faktur data
    
    Args:
        filters: Filter parameters
        
    Returns:
        str: CSV file content as string
    """
    if not filters:
        filters = {}
    
    # Parse filters if provided as string
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    company = filters.get('company') or frappe.defaults.get_user_default('Company')
    year = filters.get('year') or getdate().year
    month = filters.get('month')
    
    # Build query filters
    query_filters = {
        "company": company,
        "tahun_pajak": str(year),
        "docstatus": 1
    }
    
    if month:
        query_filters["masa_pajak"] = month
    
    # Get E-Faktur documents
    efaktur_docs = frappe.get_all(
        "Efaktur Document",
        filters=query_filters,
        fields=[
            "name", "kode_jenis_transaksi", "nomor_faktur", 
            "masa_pajak", "tahun_pajak", "tanggal_faktur",
            "npwp", "nama", "jumlah_dpp", "jumlah_ppn"
        ]
    )
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Kode Jenis Transaksi", "Nomor Faktur", "Masa Pajak",
        "Tahun Pajak", "Tanggal Faktur", "NPWP", "Nama",
        "Jumlah DPP", "Jumlah PPN", "Referensi"
    ])
    
    # Write data rows
    for doc in efaktur_docs:
        writer.writerow([
            doc.kode_jenis_transaksi,
            doc.nomor_faktur,
            doc.masa_pajak,
            doc.tahun_pajak,
            formatdate(doc.tanggal_faktur, "dd-MM-yyyy"),
            doc.npwp,
            doc.nama,
            flt(doc.jumlah_dpp, 2),
            flt(doc.jumlah_ppn, 2),
            doc.name
        ])
    
    # Return the CSV content
    csv_content = output.getvalue()
    output.close()
    
    return {
        "csv_data": csv_content,
        "filename": f"efaktur_{company}_{year}{month or ''}.csv"
    }

@frappe.whitelist()
def make_csv_ebupot(filters=None):
    """
    Generate CSV export of E-Bupot data
    
    Args:
        filters: Filter parameters
        
    Returns:
        str: CSV file content as string
    """
    if not filters:
        filters = {}
    
    # Parse filters if provided as string
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    company = filters.get('company') or frappe.defaults.get_user_default('Company')
    year = filters.get('year') or getdate().year
    month = filters.get('month')
    tax_type = filters.get('tax_type') or "23"
    
    # Build query filters
    query_filters = {
        "company": company,
        "tahun_pajak": str(year),
        "jenis_pajak": tax_type,
        "docstatus": 1
    }
    
    if month:
        query_filters["masa_pajak"] = month
    
    # Get E-Bupot documents
    ebupot_docs = frappe.get_all(
        "Ebupot Document",
        filters=query_filters,
        fields=[
            "name", "jenis_pajak", "masa_pajak", "tahun_pajak",
            "npwp_terpotong", "nama_terpotong", "penghasilan_bruto", 
            "tarif", "pph_dipotong"
        ]
    )
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Jenis Pajak", "Masa Pajak", "Tahun Pajak",
        "NPWP Terpotong", "Nama Terpotong", "Penghasilan Bruto",
        "Tarif", "PPh Dipotong", "Referensi"
    ])
    
    # Write data rows
    for doc in ebupot_docs:
        writer.writerow([
            doc.jenis_pajak,
            doc.masa_pajak,
            doc.tahun_pajak,
            doc.npwp_terpotong,
            doc.nama_terpotong,
            flt(doc.penghasilan_bruto, 2),
            flt(doc.tarif, 2),
            flt(doc.pph_dipotong, 2),
            doc.name
        ])
    
    # Return the CSV content
    csv_content = output.getvalue()
    output.close()
    
    return {
        "csv_data": csv_content,
        "filename": f"ebupot_{tax_type}_{company}_{year}{month or ''}.csv"
    }

def get_ppn_amount(company, from_date, to_date, ppn_type):
    """
    Get PPN amount for a period
    
    Args:
        company: Company name
        from_date: Start date
        to_date: End date
        ppn_type: 'in' or 'out'
        
    Returns:
        float: PPN amount
    """
    tax_type = "PPN_OUT" if ppn_type == "out" else "PPN_IN"
    
    # Get from GL Entries
    gl_entries = frappe.db.sql("""
        SELECT 
            SUM(credit) as credit,
            SUM(debit) as debit
        FROM `tabGL Entry`
        WHERE company = %s
        AND posting_date BETWEEN %s AND %s
        AND tax_type = %s
        AND is_cancelled = 0
    """, (company, from_date, to_date, tax_type), as_dict=1)
    
    if gl_entries and gl_entries[0]:
        if ppn_type == "out":
            return flt(gl_entries[0].credit)
        else:
            return flt(gl_entries[0].debit)
    
    return 0

def get_pph_amount(company, from_date, to_date, pph_type):
    """
    Get PPh amount for a period
    
    Args:
        company: Company name
        from_date: Start date
        to_date: End date
        pph_type: '21', '23', etc.
        
    Returns:
        float: PPh amount
    """
    # Get from Ebupot document for PPh 23/26
    if pph_type in ["23", "26"]:
        pph_docs = frappe.db.sql("""
            SELECT 
                SUM(pph_dipotong) as amount
            FROM `tabEbupot Document`
            WHERE company = %s
            AND tandatangan_date BETWEEN %s AND %s
            AND jenis_pajak = %s
            AND docstatus = 1
        """, (company, from_date, to_date, pph_type), as_dict=1)
        
        if pph_docs and pph_docs[0].amount:
            return flt(pph_docs[0].amount)
    
    # Get from Salary Slip for PPh 21
    elif pph_type == "21":
        pph_amounts = frappe.db.sql("""
            SELECT 
                SUM(total_tax_deducted) as amount
            FROM `tabSalary Slip`
            WHERE company = %s
            AND posting_date BETWEEN %s AND %s
            AND docstatus = 1
        """, (company, from_date, to_date), as_dict=1)
        
        if pph_amounts and pph_amounts[0].amount:
            return flt(pph_amounts[0].amount)
    
    return 0