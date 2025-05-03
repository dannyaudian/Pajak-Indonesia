frappe.pages['pelaporan-pajak'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Pelaporan Pajak'),
        single_column: true
    });

    // Initialize the PelaporanPajak class
    new pajak_indonesia.PelaporanPajak(page);
}

frappe.pages['pelaporan-pajak'].on_page_show = function(wrapper) {
    // Refresh filters when page is shown
    if (wrapper.pelaporan_pajak) {
        wrapper.pelaporan_pajak.refresh();
    }
}

pajak_indonesia.PelaporanPajak = class PelaporanPajak {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.filters = {};
        
        // Set the page as a property of the wrapper for later access
        page.parent.pelaporan_pajak = this;
        
        // Initialize components
        this.setup_page();
    }
    
    setup_page() {
        this.setup_filters();
        this.setup_summary_section();
        this.setup_details_section();
        
        // Initial data load
        this.refresh();
    }
    
    setup_filters() {
        const filter_area = $('<div class="filter-area">').appendTo(this.wrapper);
        
        // Initialize year filter
        this.page.add_field({
            fieldtype: 'Select',
            fieldname: 'tahun',
            label: __('Tahun Pajak'),
            default: moment().format('YYYY'),
            options: this.get_year_options(),
            change: () => this.refresh()
        });
        
        // Initialize month filter
        this.page.add_field({
            fieldtype: 'Select',
            fieldname: 'masa_pajak',
            label: __('Masa Pajak'),
            default: moment().subtract(1, 'month').format('MM'), // Previous month
            options: this.get_month_options(),
            change: () => this.refresh()
        });
        
        // Initialize tax type filter
        this.page.add_field({
            fieldtype: 'Select',
            fieldname: 'pajak_type',
            label: __('Jenis Pajak'),
            default: 'PPN',
            options: [
                { value: 'PPN', label: __('PPN') },
                { value: 'PPh 21', label: __('PPh 21') },
                { value: 'PPh 23', label: __('PPh 23') },
                { value: 'PPh 26', label: __('PPh 26') }
            ],
            change: () => this.refresh()
        });
        
        // Initialize company filter
        this.page.add_field({
            fieldtype: 'Link',
            fieldname: 'company',
            label: __('Company'),
            options: 'Company',
            default: frappe.defaults.get_user_default('Company'),
            reqd: 1,
            change: () => this.refresh()
        });
        
        // Add refresh button
        this.page.add_inner_button(__('Refresh'), () => this.refresh());
        
        // Set permissions for action buttons based on role
        this.set_button_permissions();
    }
    
    get_year_options() {
        const years = [];
        const current_year = moment().year();
        
        for (let i = current_year - 5; i <= current_year + 1; i++) {
            years.push({ value: i.toString(), label: i.toString() });
        }
        
        return years;
    }
    
    get_month_options() {
        return [
            { value: '01', label: __('Januari') },
            { value: '02', label: __('Februari') },
            { value: '03', label: __('Maret') },
            { value: '04', label: __('April') },
            { value: '05', label: __('Mei') },
            { value: '06', label: __('Juni') },
            { value: '07', label: __('Juli') },
            { value: '08', label: __('Agustus') },
            { value: '09', label: __('September') },
            { value: '10', label: __('Oktober') },
            { value: '11', label: __('November') },
            { value: '12', label: __('Desember') }
        ];
    }
    
    set_button_permissions() {
        // Check user roles
        this.is_tax_manager = frappe.user.has_role('Tax Manager');
        this.is_accounts_manager = frappe.user.has_role('Accounts Manager');
        this.is_system_manager = frappe.user.has_role('System Manager');
        
        // Action buttons will be added in the refresh method
    }
    
    setup_summary_section() {
        // Create summary section
        this.summary_section = $(`
            <div class="summary-section">
                <div class="section-header">
                    <h5>${__('Summary')}</h5>
                </div>
                <div class="summary-cards">
                    <div class="row"></div>
                </div>
            </div>
        `).appendTo(this.wrapper);
    }
    
    setup_details_section() {
        // Create details section
        this.details_section = $(`
            <div class="details-section">
                <div class="section-header">
                    <h5>${__('Documents')}</h5>
                </div>
                <div class="details-table"></div>
            </div>
        `).appendTo(this.wrapper);
    }
    
    refresh() {
        // Get filter values
        this.filters = {
            tahun: this.page.fields_dict.tahun.get_value(),
            masa_pajak: this.page.fields_dict.masa_pajak.get_value(),
            pajak_type: this.page.fields_dict.pajak_type.get_value(),
            company: this.page.fields_dict.company.get_value()
        };
        
        if (!this.filters.company) {
            this.show_empty_state();
            return;
        }
        
        // Show loading state
        this.show_loading();
        
        // Fetch data
        this.fetch_data()
            .then(data => {
                this.render_summary_cards(data.summary);
                this.render_details_table(data.documents);
                this.update_action_buttons(data);
            })
            .catch(err => {
                this.show_error(err);
            });
    }
    
    show_loading() {
        this.summary_section.find('.summary-cards .row').html(`
            <div class="col-md-12 text-center">
                <div class="padding-top-lg">
                    <div class="frappe-ajax-loading-wrap">
                        <div class="frappe-ajax-loading"></div>
                    </div>
                </div>
            </div>
        `);
        
        this.details_section.find('.details-table').html(`
            <div class="text-center">
                <div class="padding-top-lg">
                    <div class="frappe-ajax-loading-wrap">
                        <div class="frappe-ajax-loading"></div>
                    </div>
                </div>
            </div>
        `);
    }
    
    show_empty_state() {
        this.summary_section.find('.summary-cards .row').html(`
            <div class="col-md-12 text-center">
                <div class="padding-top-lg text-muted">
                    ${__('Select a company to view tax reporting data')}
                </div>
            </div>
        `);
        
        this.details_section.find('.details-table').html('');
    }
    
    show_error(err) {
        console.error(err);
        frappe.msgprint({
            title: __('Error'),
            indicator: 'red',
            message: __('Failed to load tax reporting data. Please try again.')
        });
    }
    
    fetch_data() {
        return new Promise((resolve, reject) => {
            frappe.call({
                method: 'pajak_indonesia.pelaporan.page.pelaporan_pajak.pelaporan_pajak.get_tax_reporting_data',
                args: this.filters,
                callback: function(r) {
                    if (r.exc) {
                        reject(r.exc);
                    } else {
                        resolve(r.message);
                    }
                }
            });
        });
    }
    
    render_summary_cards(summary) {
        let cards_html = '';
        
        // Format the summary cards based on tax type
        if (this.filters.pajak_type === 'PPN') {
            cards_html = `
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-subtitle text-muted">${__('PPN Keluaran')}</h6>
                            <h4 class="card-title">${format_currency(summary.ppn_out || 0)}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-subtitle text-muted">${__('PPN Masukan')}</h6>
                            <h4 class="card-title">${format_currency(summary.ppn_in || 0)}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-subtitle text-muted">${__('Kurang/Lebih Bayar')}</h6>
                            <h4 class="card-title ${summary.tax_balance < 0 ? 'text-danger' : 'text-success'}">${format_currency(summary.tax_balance || 0)}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-subtitle text-muted">${__('Status')}</h6>
                            <h4 class="card-title">${summary.status || __('Belum Lapor')}</h4>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // For PPh taxes
            cards_html = `
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-subtitle text-muted">${__('Jumlah Penghasilan')}</h6>
                            <h4 class="card-title">${format_currency(summary.income_amount || 0)}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-subtitle text-muted">${__('Jumlah Pajak')}</h6>
                            <h4 class="card-title">${format_currency(summary.tax_amount || 0)}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-subtitle text-muted">${__('Jumlah Dokumen')}</h6>
                            <h4 class="card-title">${summary.document_count || 0}</h4>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-subtitle text-muted">${__('Status')}</h6>
                            <h4 class="card-title">${summary.status || __('Belum Lapor')}</h4>
                        </div>
                    </div>
                </div>
            `;
        }
        
        this.summary_section.find('.summary-cards .row').html(cards_html);
    }
    
    render_details_table(documents) {
        if (!documents || documents.length === 0) {
            this.details_section.find('.details-table').html(`
                <div class="text-center text-muted padding-lg">
                    ${__('No documents found for the selected filters')}
                </div>
            `);
            return;
        }
        
        // Create datatable
        if (this.datatable) {
            this.datatable.destroy();
        }
        
        const container = this.details_section.find('.details-table');
        container.empty();
        
        // Define columns based on tax type
        let columns = this.get_columns_for_tax_type();
        
        // Initialize DataTable
        this.datatable = new frappe.DataTable(container[0], {
            columns: columns,
            data: documents,
            layout: 'fixed',
            inlineFilters: true,
            dynamicRowHeight: true,
            checkboxColumn: true,
            cellHeight: 40
        });
        
        // Attach row actions
        this.datatable.on('click', (e, column, rowIndex, cell) => {
            if (column.name === 'Actions') {
                const row = this.datatable.datamanager.getRow(rowIndex);
                this.show_row_actions(row, cell);
            }
        });
    }
    
    get_columns_for_tax_type() {
        // Base columns that are common to all tax types
        const base_columns = [
            {
                name: 'doctype',
                id: 'doctype',
                content: __('Document Type'),
                width: 120
            },
            {
                name: 'docname',
                id: 'docname',
                content: __('Document ID'),
                width: 180,
                format: (value, row) => `<a href="/app/${frappe.router.slug(row.doctype)}/${row.docname}">${row.docname}</a>`
            },
            {
                name: 'posting_date',
                id: 'posting_date',
                content: __('Posting Date'),
                width: 100,
                format: (value) => frappe.datetime.str_to_user(value)
            },
            {
                name: 'status',
                id: 'status',
                content: __('Status'),
                width: 100
            }
        ];
        
        // Add tax-type specific columns
        if (this.filters.pajak_type === 'PPN') {
            return [
                ...base_columns,
                {
                    name: 'base_amount',
                    id: 'base_amount',
                    content: __('DPP'),
                    width: 120,
                    format: (value) => format_currency(value)
                },
                {
                    name: 'tax_amount',
                    id: 'tax_amount',
                    content: __('PPN'),
                    width: 120,
                    format: (value) => format_currency(value)
                },
                {
                    name: 'Actions',
                    id: 'actions',
                    content: __('Actions'),
                    width: 100,
                    format: () => `<button class="btn btn-xs btn-actions">...</button>`
                }
            ];
        } else {
            return [
                ...base_columns,
                {
                    name: 'party',
                    id: 'party',
                    content: __('Party'),
                    width: 150
                },
                {
                    name: 'base_amount',
                    id: 'base_amount',
                    content: __('Penghasilan'),
                    width: 120,
                    format: (value) => format_currency(value)
                },
                {
                    name: 'tax_amount',
                    id: 'tax_amount',
                    content: __('Pajak'),
                    width: 120,
                    format: (value) => format_currency(value)
                },
                {
                    name: 'Actions',
                    id: 'actions',
                    content: __('Actions'),
                    width: 100,
                    format: () => `<button class="btn btn-xs btn-actions">...</button>`
                }
            ];
        }
    }
    
    show_row_actions(row, cell) {
        const actions = [];
        
        // View action for all users
        actions.push({
            label: __('View Document'),
            action: () => frappe.set_route('Form', row.doctype, row.docname)
        });
        
        // Edit action for tax managers
        if (this.is_tax_manager || this.is_system_manager) {
            actions.push({
                label: __('Edit Document'),
                action: () => frappe.set_route('Form', row.doctype, row.docname, { edit: 1 })
            });
        }
        
        frappe.ui.menu.generate_actions(actions, $(cell));
    }
    
    update_action_buttons(data) {
        // Clear existing buttons
        this.page.clear_inner_toolbar();
        this.page.add_inner_button(__('Refresh'), () => this.refresh());
        
        // Check if filing exists
        const filing_exists = data.summary && data.summary.filing_id;
        
        // Generate Tax Filing button
        if (!filing_exists && (this.is_tax_manager || this.is_system_manager)) {
            this.page.add_inner_button(__('Generate Tax Filing'), () => {
                this.generate_tax_filing();
            }, __('Create'));
        }
        
        if (filing_exists) {
            // View Tax Filing button for all users
            this.page.add_inner_button(__('View Tax Filing'), () => {
                frappe.set_route('Form', 'Tax Filing Summary', data.summary.filing_id);
            }, __('View'));
            
            // Payment button for accounts and tax managers
            if (data.summary.tax_balance > 0 && !data.summary.payment_id && 
                (this.is_accounts_manager || this.is_tax_manager || this.is_system_manager)) {
                this.page.add_inner_button(__('Generate Payment'), () => {
                    this.generate_payment(data.summary.filing_id);
                }, __('Create'));
            }
            
            // Adjustment button for tax managers
            if (data.summary.tax_balance < 0 && !data.summary.adjustment_id && 
                (this.is_tax_manager || this.is_system_manager)) {
                this.page.add_inner_button(__('Generate Adjustment'), () => {
                    this.generate_adjustment(data.summary.filing_id);
                }, __('Create'));
            }
        }
    }
    
    generate_tax_filing() {
        frappe.call({
            method: 'pajak_indonesia.pelaporan.page.pelaporan_pajak.pelaporan_pajak.generate_tax_filing',
            args: this.filters,
            callback: (r) => {
                if (r.message && r.message.filing_id) {
                    frappe.show_alert({
                        message: __('Tax Filing generated successfully'),
                        indicator: 'green'
                    });
                    frappe.set_route('Form', 'Tax Filing Summary', r.message.filing_id);
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        indicator: 'red',
                        message: __('Failed to generate Tax Filing')
                    });
                }
            }
        });
    }
    
    generate_payment(filing_id) {
        frappe.call({
            method: 'pajak_indonesia.pelaporan.doctype.tax_filing_summary.tax_filing_summary.generate_payment_entry',
            args: {
                tax_filing_id: filing_id
            },
            callback: (r) => {
                if (r.message && r.message.status === 'success') {
                    frappe.show_alert({
                        message: r.message.message,
                        indicator: 'green'
                    });
                    
                    if (r.message.payment_entry_id) {
                        frappe.set_route('Form', 'Payment Entry', r.message.payment_entry_id);
                    } else {
                        this.refresh();
                    }
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        indicator: 'red',
                        message: r.message.message || __('Failed to generate Payment Entry')
                    });
                }
            }
        });
    }
    
    generate_adjustment(filing_id) {
        frappe.call({
            method: 'pajak_indonesia.pelaporan.doctype.tax_filing_summary.tax_filing_summary.generate_adjustment_entry',
            args: {
                tax_filing_id: filing_id
            },
            callback: (r) => {
                if (r.message && r.message.status === 'success') {
                    frappe.show_alert({
                        message: r.message.message,
                        indicator: 'green'
                    });
                    
                    if (r.message.adjustment_entry_id) {
                        frappe.set_route('Form', 'Tax Adjustment Entry', r.message.adjustment_entry_id);
                    } else {
                        this.refresh();
                    }
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        indicator: 'red',
                        message: r.message.message || __('Failed to generate Adjustment Entry')
                    });
                }
            }
        });
    }
};