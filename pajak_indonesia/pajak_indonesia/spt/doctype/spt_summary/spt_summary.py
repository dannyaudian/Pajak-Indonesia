import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate

class SPTSummary(Document):
    def validate(self):
        self.validate_period()
        self.calculate_summary()
    
    def validate_period(self):
        """Validate masa and tahun pajak"""
        # Check if year is valid
        try:
            year = int(self.tahun_pajak)
            if year < 2000 or year > 2099:
                frappe.throw("Tahun Pajak harus antara 2000-2099")
        except ValueError:
            frappe.throw("Format Tahun Pajak tidak valid")
    
    def calculate_summary(self):
        """Calculate summary based on jenis_spt"""
        if self.jenis_spt == "PPN":
            self.calculate_ppn_summary()
        elif self.jenis_spt == "PPh 21":
            self.calculate_pph21_summary()
        elif self.jenis_spt == "PPh 23":
            self.calculate_pph23_summary()
        elif self.jenis_spt == "PPh 26":
            self.calculate_pph26_summary()
    
    def calculate_ppn_summary(self):
        """Calculate PPN summary from E-Faktur documents"""
        filters = {
            "docstatus": 1,
            "masa_pajak": self.masa_pajak,
            "tahun_pajak": self.tahun_pajak,
            "company": self.company
        }
        
        # Get sales invoices (penjualan)
        penjualan = frappe.get_all("Efaktur Document",
            filters=filters,
            fields=["jumlah_dpp", "jumlah_ppn", "jumlah_ppnbm"]
        )
        
        self.jumlah_dpp_penjualan = sum(p.jumlah_dpp for p in penjualan)
        self.jumlah_ppn_penjualan = sum(p.jumlah_ppn for p in penjualan)
        self.jumlah_ppnbm_penjualan = sum(p.jumlah_ppnbm for p in penjualan)
        
        # Get purchase invoices (pembelian)
        # Logic for pembelian calculation...
    
    def calculate_pph21_summary(self):
        """Calculate PPh 21 summary from Salary Slips"""
        filters = {
            "docstatus": 1,
            "posting_date": ["between", [
                f"{self.tahun_pajak}-{self.masa_pajak}-01",
                f"{self.tahun_pajak}-{self.masa_pajak}-31"
            ]],
            "company": self.company
        }
        
        salary_slips = frappe.get_all("Salary Slip",
            filters=filters,
            fields=["gross_pay", "total_tax_deducted"]
        )
        
        self.jumlah_penghasilan_bruto_21 = sum(ss.gross_pay for ss in salary_slips)
        self.jumlah_pph_21 = sum(ss.total_tax_deducted for ss in salary_slips)
    
    def calculate_pph23_summary(self):
        """Calculate PPh 23 summary from E-Bupot documents"""
        filters = {
            "docstatus": 1,
            "jenis_pajak": "23",
            "masa_pajak": self.masa_pajak,
            "tahun_pajak": self.tahun_pajak,
            "company": self.company
        }
        
        bupot_23 = frappe.get_all("Ebupot Document",
            filters=filters,
            fields=["penghasilan_bruto", "pph_dipotong"]
        )
        
        self.jumlah_penghasilan_bruto_23 = sum(b.penghasilan_bruto for b in bupot_23)
        self.jumlah_pph_23 = sum(b.pph_dipotong for b in bupot_23)
    
    def calculate_pph26_summary(self):
        """Calculate PPh 26 summary from E-Bupot documents"""
        filters = {
            "docstatus": 1,
            "jenis_pajak": "26",
            "masa_pajak": self.masa_pajak,
            "tahun_pajak": self.tahun_pajak,
            "company": self.company
        }
        
        bupot_26 = frappe.get_all("Ebupot Document",
            filters=filters,
            fields=["penghasilan_bruto", "pph_dipotong"]
        )
        
        self.jumlah_penghasilan_bruto_26 = sum(b.penghasilan_bruto for b in bupot_26)
        self.jumlah_pph_26 = sum(b.pph_dipotong for b in bupot_26)