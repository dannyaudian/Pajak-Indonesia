import frappe
from frappe.model.document import Document
from frappe.utils import flt

class EbupotDocument(Document):
    def validate(self):
        self.calculate_item_values()
        self.calculate_totals()
    
    def calculate_item_values(self):
        for item in self.items:
            # Calculate PPh for each item
            item.pph_dipotong = flt(item.dasar_pengenaan_pajak) * (flt(item.tarif) / 100)
    
    def calculate_totals(self):
        # Calculate total PPh
        self.penghasilan_bruto = sum(flt(item.dasar_pengenaan_pajak) for item in self.items)
        
        # Use fasilitas tarif if available
        tarif = flt(self.tarif_fasilitas) if self.tarif_fasilitas else flt(self.tarif)
        self.pph_dipotong = flt(self.penghasilan_bruto) * (tarif / 100)