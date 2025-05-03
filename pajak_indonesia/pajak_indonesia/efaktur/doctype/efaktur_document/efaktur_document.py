import frappe
from frappe.model.document import Document
from frappe.utils import flt

class EfakturDocument(Document):
    def validate(self):
        self.calculate_item_values()
        self.calculate_totals()
    
    def calculate_item_values(self):
        for item in self.items:
            # Calculate harga_total
            item.harga_total = flt(item.harga_satuan) * flt(item.jumlah_barang)
            
            # Calculate DPP (after discount)
            item.dpp = flt(item.harga_total) - flt(item.diskon)
            
            # Calculate PPN (11% of DPP)
            item.ppn = flt(item.dpp) * 0.11
            
            # Calculate PPnBM if applicable
            if flt(item.tarif_ppnbm) > 0:
                item.ppnbm = flt(item.dpp) * (flt(item.tarif_ppnbm) / 100)
            else:
                item.ppnbm = 0
    
    def calculate_totals(self):
        self.jumlah_dpp = sum(flt(item.dpp) for item in self.items)
        self.jumlah_ppn = sum(flt(item.ppn) for item in self.items)
        self.jumlah_ppnbm = sum(flt(item.ppnbm) for item in self.items)