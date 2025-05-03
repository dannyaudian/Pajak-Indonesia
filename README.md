# Pajak Indonesia

ERPNext app for Indonesian Tax Management (PPh 21/23/26 & PPN)

## Features

- E-Faktur Integration (PPN)
- E-Bupot Integration (PPh 21/23/26)
- Tax Filing Management
- Tax Payment Processing
- Tax Reports & Dashboard

## Installation

1. Get app from GitHub:
```bash
bench get-app pajak_indonesia https://github.com/your-org/pajak-indonesia
Install on your site:
Bash
Run
bench --site your-site install-app pajak_indonesia
Load fixtures:
Bash
Run
bench --site your-site migrate
bench --site your-site set-config enable_app_fixtures 1
bench --site your-site install-fixtures pajak_indonesia
Setup
Create Tax Categories:

PPN (11%)
PPh 21
PPh 23 (2%)
PPh 26 (20%)
Configure Accounts:

PPN Keluaran (Output VAT)
PPN Masukan (Input VAT)
PPh 21/23/26 Payable
Set Tax Manager:

Create user with "Tax Manager" role
Assign tax module permissions
Usage
Sales Tax (PPN):

Create Sales Invoice
E-Faktur auto-generated on submit
Monitor in Tax Filing Summary
Withholding Tax (PPh):

Create Purchase Invoice
E-Bupot auto-generated for PPh
Process tax payments
Tax Reporting:

Use "Pelaporan Pajak" page
Generate monthly tax filings
Track payment & reporting status
API Endpoints
Tax data can be accessed via:


Apply
/api/method/pajak_indonesia.api.get_tax_data
/api/method/pajak_indonesia.api.submit_tax_filing
License
MIT