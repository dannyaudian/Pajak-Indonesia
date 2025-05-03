import unittest
import frappe
from frappe.utils import today, add_days, add_months
from frappe.tests.utils import FrappeTestCase

class TestTaxFilingReconciliation(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test dependencies"""
        super().setUpClass()
        # Create test company if not exists
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
        # Create test documents
        self.create_test_documents()
    
    def tearDown(self):
        """Clean up test data after each test"""
        frappe.set_user("Administrator")
    
    def test_filing_creation(self):
        """Test basic Tax Filing Summary creation"""
        filing = frappe.get_doc({
            "doctype": "Tax Filing Summary",
            "company": "_Test Company IDN",
            "posting_date": today(),
            "jenis_pelaporan": "SPT Masa PPN",
            "masa_pajak": "01",
            "tahun_pajak": "2024",
            "status_spt": "Nihil"
        })
        filing.insert()
        self.assertEqual(filing.docstatus, 0)
    
    def test_filing_validation(self):
        """Test Tax Filing Summary validation rules"""
        with self.assertRaises(frappe.ValidationError):
            # Should fail without required fields
            filing = frappe.get_doc({
                "doctype": "Tax Filing Summary"
            }).insert()
    
    def test_document_linking(self):
        """Test linking source documents to filing"""
        filing = create_test_filing()
        
        # Add source document
        filing.append("source_documents", {
            "document_type": "Efaktur Document",
            "document_name": self.test_efaktur.name
        })
        filing.save()
        
        # Check if document is properly linked
        self.assertEqual(len(filing.source_documents), 1)
    
    def test_filing_reconciliation(self):
        """Test tax filing reconciliation process"""
        filing = create_test_filing()
        
        # Add source documents
        filing.extend("source_documents", [
            {
                "document_type": "Efaktur Document",
                "document_name": self.test_efaktur.name
            },
            {
                "document_type": "Penyelesaian Pajak",
                "document_name": self.test_payment.name
            }
        ])
        filing.save()
        
        # Test reconciliation
        # TODO: Implement reconciliation testing
        pass
    
    def create_test_documents(self):
        """Create test documents for filing"""
        # Create test e-Faktur
        self.test_efaktur = frappe.get_doc({
            "doctype": "Efaktur Document",
            "company": "_Test Company IDN",
            "posting_date": today(),
            "kode_jenis_transaksi": "01",
            "masa_pajak": "01",
            "tahun_pajak": "2024"
        }).insert()
        
        # Create test Payment
        self.test_payment = frappe.get_doc({
            "doctype": "Penyelesaian Pajak",
            "company": "_Test Company IDN",
            "posting_date": today(),
            "jenis_pajak": "PPN",
            "masa_pajak": "01",
            "tahun_pajak": "2024"
        }).insert()

def create_test_filing():
    """Helper function to create test Tax Filing Summary"""
    return frappe.get_doc({
        "doctype": "Tax Filing Summary",
        "company": "_Test Company IDN",
        "posting_date": today(),
        "jenis_pelaporan": "SPT Masa PPN",
        "masa_pajak": "01",
        "tahun_pajak": "2024",
        "status_spt": "Nihil"
    }).insert()