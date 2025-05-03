import unittest
import frappe
from frappe.utils import today, add_days
from frappe.tests.utils import FrappeTestCase

class TestEfakturBasic(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test dependencies"""
        super().setUpClass()
        # Create test company
        if not frappe.db.exists("Company", "_Test Company IDN"):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": "_Test Company IDN",
                "country": "Indonesia",
                "default_currency": "IDR",
                "tax_id": "01.234.567.8-123.000"
            }).insert()
    
    def setUp(self):
        """Set up test data before each test"""
        # Create test customer
        if not frappe.db.exists("Customer", "_Test Customer IDN"):
            frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "_Test Customer IDN",
                "tax_id": "02.345.678.9-234.000"
            }).insert()
            
    def tearDown(self):
        """Clean up test data after each test"""
        frappe.set_user("Administrator")
    
    def test_efaktur_creation(self):
        """Test basic e-Faktur document creation"""
        efaktur = frappe.get_doc({
            "doctype": "Efaktur Document",
            "company": "_Test Company IDN",
            "posting_date": today(),
            "kode_jenis_transaksi": "01",
            "fg_pengganti": "0",
            "masa_pajak": "01",
            "tahun_pajak": "2024",
            "npwp": "02.345.678.9-234.000",
            "nama": "_Test Customer IDN"
        })
        efaktur.insert()
        self.assertEqual(efaktur.docstatus, 0)
    
    def test_efaktur_validation(self):
        """Test e-Faktur document validation rules"""
        with self.assertRaises(frappe.ValidationError):
            # Should fail without required fields
            efaktur = frappe.get_doc({
                "doctype": "Efaktur Document"
            }).insert()
    
    def test_efaktur_calculation(self):
        """Test e-Faktur tax calculations"""
        efaktur = frappe.get_doc({
            "doctype": "Efaktur Document",
            "company": "_Test Company IDN",
            "posting_date": today(),
            "kode_jenis_transaksi": "01",
            "fg_pengganti": "0",
            "masa_pajak": "01",
            "tahun_pajak": "2024",
            "npwp": "02.345.678.9-234.000",
            "nama": "_Test Customer IDN",
            "items": [
                {
                    "nama_barang": "_Test Item",
                    "harga_satuan": 1000000,
                    "jumlah_barang": 1
                }
            ]
        })
        efaktur.insert()
        
        # Test automatic calculations
        self.assertEqual(efaktur.items[0].harga_total, 1000000)
        self.assertEqual(efaktur.items[0].ppn, 110000)  # 11% PPN
    
    def test_efaktur_from_invoice(self):
        """Test e-Faktur creation from Sales Invoice"""
        # Create test Sales Invoice
        si = create_test_sales_invoice()
        si.submit()
        
        # Check if e-Faktur was created
        efaktur = frappe.get_list("Efaktur Document", 
                                 filters={"reference_name": si.name})
        self.assertTrue(len(efaktur) > 0)

def create_test_sales_invoice():
    """Helper function to create test Sales Invoice"""
    return frappe.get_doc({
        "doctype": "Sales Invoice",
        "company": "_Test Company IDN",
        "posting_date": today(),
        "customer": "_Test Customer IDN",
        "items": [
            {
                "item_code": "_Test Item",
                "qty": 1,
                "rate": 1000000
            }
        ]
    }).insert()