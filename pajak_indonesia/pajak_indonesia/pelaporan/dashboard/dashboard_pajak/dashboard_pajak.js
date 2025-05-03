frappe.provide('pajak_indonesia.dashboard');

pajak_indonesia.dashboard.Dashboard = class DashboardPajak {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.filters = {
            company: frappe.defaults.get_user_default('Company'),
            year: moment().year(),
            month: moment().format('MM'),
            tax_type: '23'
        };
        
        this.make();
    }
    
    make() {
        // Create the dashboard structure
        this.make_filters();
        this.make_export_buttons();
        
        // Load initial data
        this.refresh();
    }
    
    make_filters() {
        // Create filter controls
        this.filter_wrapper = $('<div class="dashboard-filter-container">').appendTo(this.wrapper);
        
        this.company_filter = frappe.ui.form.make_control({
            parent: this.filter_wrapper,
            df: {
                fieldtype: 'Link',
                fieldname: 'company',
                label: __('Company'),
                options: 'Company',
                default: this.filters.company,
                onchange: () => this.refresh()
            },
            render_input: true
        });
        
        this.year_filter = frappe.ui.form.make_control({
            parent: this.filter_wrapper,
            df: {
                fieldtype: 'Select',
                fieldname: 'year',
                label: __('Year'),
                options: this.get_year_options(),
                default: this.filters.year,
                onchange: () => this.refresh()
            },
            render_input: true
        });
    }
    
    get_year_options() {
        const current_year = moment().year();
        const years = [];
        
        for (let i = current_year - 3; i <= current_year + 1; i++) {
            years.push({ value: i, label: i });
        }
        
        return years;
    }
    
    make_export_buttons() {
        // Create export button container
        this.export_wrapper = $('<div class="dashboard-export-container">').appendTo(this.wrapper);
        
        // E-Faktur export button
        this.efaktur_export_btn = $(`
            <button class="btn btn-sm btn-default">
                <i class="fa fa-download"></i> ${__('Export E-Faktur')}
            </button>
        `).appendTo(this.export_wrapper);
        
        this.efaktur_export_btn.on('click', () => this.export_efaktur());
        
        // E-Bupot export button
        this.ebupot_export_btn = $(`
            <button class="btn btn-sm btn-default">
                <i class="fa fa-download"></i> ${__('Export E-Bupot')}
            </button>
        `).appendTo(this.export_wrapper);
        
        this.ebupot_export_btn.on('click', () => this.export_ebupot());
    }
    
    refresh() {
        // Update filters
        this.filters.company = this.company_filter.get_value();
        this.filters.year = this.year_filter.get_value();
        
        // Refresh dashboard (will be handled by Frappe Dashboard)
        if (window.cur_dashboard) {
            window.cur_dashboard.refresh();
        }
    }
    
    export_efaktur() {
        frappe.call({
            method: 'pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.make_csv_efaktur',
            args: {
                filters: this.filters
            },
            callback: (r) => {
                if (r.message) {
                    this.download_csv(r.message.csv_data, r.message.filename);
                }
            }
        });
    }
    
    export_ebupot() {
        // Show dialog to select additional filters
        const dialog = new frappe.ui.Dialog({
            title: __('Export E-Bupot'),
            fields: [
                {
                    fieldtype: 'Select',
                    fieldname: 'tax_type',
                    label: __('Tax Type'),
                    options: [
                        { value: '23', label: __('PPh 23') },
                        { value: '26', label: __('PPh 26') }
                    ],
                    default: '23'
                },
                {
                    fieldtype: 'Select',
                    fieldname: 'month',
                    label: __('Month (Optional)'),
                    options: [
                        { value: '', label: __('All Months') },
                        { value: '01', label: __('January') },
                        { value: '02', label: __('February') },
                        { value: '03', label: __('March') },
                        { value: '04', label: __('April') },
                        { value: '05', label: __('May') },
                        { value: '06', label: __('June') },
                        { value: '07', label: __('July') },
                        { value: '08', label: __('August') },
                        { value: '09', label: __('September') },
                        { value: '10', label: __('October') },
                        { value: '11', label: __('November') },
                        { value: '12', label: __('December') }
                    ],
                    default: ''
                }
            ],
            primary_action_label: __('Export'),
            primary_action: (values) => {
                const export_filters = {
                    ...this.filters,
                    tax_type: values.tax_type,
                    month: values.month
                };
                
                frappe.call({
                    method: 'pajak_indonesia.pelaporan.dashboard.dashboard_pajak.dashboard_pajak.make_csv_ebupot',
                    args: {
                        filters: export_filters
                    },
                    callback: (r) => {
                        if (r.message) {
                            this.download_csv(r.message.csv_data, r.message.filename);
                            dialog.hide();
                        }
                    }
                });
            }
        });
        
        dialog.show();
    }
    
    download_csv(csv_data, filename) {
        const blob = new Blob([csv_data], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
};

frappe.pages['pajak-dashboard'].on_page_load = function(wrapper) {
    frappe.dashboard_pajak = new pajak_indonesia.dashboard.Dashboard(wrapper);
};