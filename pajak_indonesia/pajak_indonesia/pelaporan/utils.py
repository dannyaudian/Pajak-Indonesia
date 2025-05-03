from typing import Optional, Dict, Any, List
import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, cint
from frappe import _

class GLEntryTaxTagger:
    """Handles tax-related tagging of GL Entries"""
    
    def __init__(self, company: str):
        self.company = company
        self._ppn_out_account = None
        self._ppn_in_account = None
    
    @property
    def ppn_out_account(self) -> Optional[str]:
        """Get cached or fetch PPN Output account"""
        if self._ppn_out_account is None:
            self._ppn_out_account = get_ppn_output_account(self.company)
        return self._ppn_out_account
    
    @property
    def ppn_in_account(self) -> Optional[str]:
        """Get cached or fetch PPN Input account"""
        if self._ppn_in_account is None:
            self._ppn_in_account = get_ppn_input_account(self.company)
        return self._ppn_in_account
    
    def tag_gl_entry(self, gl_entry: Dict[str, Any], source_doc: Optional[Document] = None) -> None:
        """Tag GL Entry with tax information based on account"""
        try:
            # Skip if no valid accounts found
            if not (self.ppn_out_account or self.ppn_in_account):
                return
            
            tax_type = self._determine_tax_type(gl_entry)
            if not tax_type:
                return
            
            # Set tax information
            gl_entry['tax_type'] = tax_type
            
            # Add source document reference if available
            if source_doc and hasattr(source_doc, 'doctype') and hasattr(source_doc, 'name'):
                gl_entry['tax_source_type'] = source_doc.doctype
                gl_entry['tax_source'] = source_doc.name
            
            if frappe.conf.get('developer_mode'):
                frappe.logger().debug(f"Tagged GL Entry with {tax_type}")
                
        except Exception as e:
            self._log_error("GL Entry tagging failed", e)
    
    def _determine_tax_type(self, gl_entry: Dict[str, Any]) -> Optional[str]:
        """Determine tax type based on account and entry type"""
        account = gl_entry.get('account')
        credit = flt(gl_entry.get('credit', 0))
        debit = flt(gl_entry.get('debit', 0))
        
        if account == self.ppn_out_account and credit > 0:
            return "PPN_OUT"
        elif account == self.ppn_in_account and debit > 0:
            return "PPN_IN"
        
        return None
    
    def _log_error(self, message: str, exception: Exception) -> None:
        """Log error with context"""
        error_msg = f"{message} for company {self.company}: {str(exception)}"
        frappe.log_error(message=error_msg, title="Tax Tagging Error")

def tag_ppn_out_gl(gl_entry: Dict[str, Any], doc: Document) -> None:
    """Tag PPN Output GL entries during creation"""
    if not gl_entry or not doc:
        return
    
    company = gl_entry.get('company') or getattr(doc, 'company', None)
    if not company:
        return
    
    tagger = GLEntryTaxTagger(company)
    tagger.tag_gl_entry(gl_entry, doc)

def auto_tag_gl_entry(doc: Document, method: Optional[str] = None) -> None:
    """Auto-tag GL Entry after creation"""
    if not doc or doc.doctype != "GL Entry" or cint(doc.is_cancelled):
        return
    
    if not doc.company:
        return
    
    tagger = GLEntryTaxTagger(doc.company)
    tagger.tag_gl_entry(doc.as_dict(), None)

def gl_entry_naming_override(doc: Document, method: Optional[str] = None) -> None:
    """Override GL Entry naming"""
    doc.name = make_autoname('ACC-GLI-.YYYY.-.#####', '', doc)

class TaxAccountFinder:
    """Handles tax account lookup with caching"""
    
    CACHE_TIMEOUT = 3600  # 1 hour
    
    @classmethod
    def get_ppn_account(cls, company: str, account_type: str) -> Optional[str]:
        """Get PPN account with caching"""
        cache_key = f"ppn_{account_type.lower()}_account_{company}"
        
        # Try cache first
        account = frappe.cache().get_value(cache_key)
        if account:
            return account
        
        # Get from database
        account = cls._find_ppn_account(company, account_type)
        
        # Cache if found
        if account:
            frappe.cache().set_value(cache_key, account, expires_in_sec=cls.CACHE_TIMEOUT)
        
        return account
    
    @staticmethod
    def _find_ppn_account(company: str, account_type: str) -> Optional[str]:
        """Find PPN account from database"""
        # Try tax category first
        account = frappe.db.get_value(
            "Tax Category Account",
            {
                "parent": "PPN",
                "company": company,
                "account_type": account_type
            },
            "account"
        )
        
        if not account:
            # Try account naming patterns
            patterns = cls._get_account_patterns(account_type)
            account = cls._find_account_by_patterns(company, patterns)
        
        return account
    
    @staticmethod
    def _get_account_patterns(account_type: str) -> List[str]:
        """Get account naming patterns based on type"""
        if account_type.lower() == "output":
            return [
                "%ppn%out%",
                "%ppn%output%",
                "%vat%out%",
                "%pajak%keluar%"
            ]
        else:  # Input
            return [
                "%ppn%in%",
                "%ppn%input%",
                "%vat%in%",
                "%pajak%masukan%"
            ]
    
    @staticmethod
    def _find_account_by_patterns(company: str, patterns: List[str]) -> Optional[str]:
        """Find account matching patterns"""
        or_filters = {}
        for i, pattern in enumerate(patterns):
            or_filters[f"account_name{i}"] = ["like", pattern]
            or_filters[f"name{i}"] = ["like", pattern]
        
        accounts = frappe.get_list(
            "Account",
            filters={
                "company": company,
                "account_type": "Tax",
                "is_group": 0
            },
            or_filters=or_filters,
            fields=["name"],
            limit=1
        )
        
        return accounts[0].name if accounts else None

def get_ppn_output_account(company: str) -> Optional[str]:
    """Get PPN Output account for company"""
    return TaxAccountFinder.get_ppn_account(company, "Output")

def get_ppn_input_account(company: str) -> Optional[str]:
    """Get PPN Input account for company"""
    return TaxAccountFinder.get_ppn_account(company, "Input")

def setup_custom_fields_for_gl_entry() -> None:
    """Setup custom fields for GL Entry tax tracking"""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    
    custom_fields = {
        "GL Entry": [
            {
                "fieldname": "tax_type",
                "label": "Tax Type",
                "fieldtype": "Data",
                "insert_after": "against",
                "translatable": 0,
                "search_index": 1
            },
            {
                "fieldname": "tax_source_type",
                "label": "Tax Source Type",
                "fieldtype": "Data",
                "insert_after": "tax_type",
                "translatable": 0
            },
            {
                "fieldname": "tax_source",
                "label": "Tax Source",
                "fieldtype": "Dynamic Link",
                "options": "tax_source_type",
                "insert_after": "tax_source_type",
                "translatable": 0
            }
        ]
    }
    
    create_custom_fields(custom_fields)