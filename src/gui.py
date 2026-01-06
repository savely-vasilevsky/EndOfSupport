"""Cross-platform GUI for EndOfSupportTool.

Provides a graphical interface for analyzing AWS resource inventory CSV files
and generating support status reports.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, List

from .classifier import ResourceClassifier
from .formatters import TextFormatter, CSVFormatter, JSONFormatter, ExcelFormatter, EXCEL_AVAILABLE, WIN32COM_AVAILABLE, TEMPLATE_DIR
from .generator import ReportGenerator
from .models import ReportFilters, SupportStatus
from .parser import CSVParser, CSVParseError


class EndOfSupportGUI:
    """Main GUI application for EndOfSupportTool."""
    
    def __init__(self):
        """Initialize the GUI application."""
        self.root = tk.Tk()
        self.root.title("AWS End-of-Support Tool")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Variables
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.output_format = tk.StringVar(value="text")
        self.days_threshold = tk.IntVar(value=90)
        
        # Status filter checkboxes
        self.filter_supported = tk.BooleanVar(value=False)
        self.filter_approaching = tk.BooleanVar(value=False)
        self.filter_extended = tk.BooleanVar(value=False)
        self.filter_oos = tk.BooleanVar(value=False)
        
        # Excel options
        self.include_pivot = tk.BooleanVar(value=True)
        self.pivot_method = tk.StringVar(value="auto")
        self.pivot_per_account = tk.BooleanVar(value=False)
        
        # Build UI
        self._create_widgets()
        self._configure_grid()
        
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Input file section
        input_frame = ttk.LabelFrame(main_frame, text="Input", padding="5")
        input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(input_frame, text="CSV File:").grid(row=0, column=0, sticky="w")
        ttk.Entry(input_frame, textvariable=self.input_file, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(input_frame, text="Browse...", command=self._browse_input).grid(row=0, column=2)
        
        # Output section
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="5")
        output_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(output_frame, text="Format:").grid(row=0, column=0, sticky="w")
        format_combo = ttk.Combobox(output_frame, textvariable=self.output_format, 
                                     values=["text", "csv", "json", "excel"], state="readonly", width=15)
        format_combo.grid(row=0, column=1, sticky="w", padx=5)
        format_combo.bind("<<ComboboxSelected>>", self._on_format_change)
        
        ttk.Label(output_frame, text="Output File:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Entry(output_frame, textvariable=self.output_file, width=60).grid(row=1, column=1, padx=5, pady=(5, 0))
        ttk.Button(output_frame, text="Browse...", command=self._browse_output).grid(row=1, column=2, pady=(5, 0))
        
        # Excel options (shown only when Excel format is selected)
        self.excel_options_frame = ttk.LabelFrame(main_frame, text="Excel Options", padding="5")
        self.excel_options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        # Include pivot checkbox
        self.pivot_checkbox = ttk.Checkbutton(
            self.excel_options_frame, 
            text="Include Pivot Table", 
            variable=self.include_pivot,
            command=self._on_pivot_toggle
        )
        self.pivot_checkbox.grid(row=0, column=0, sticky="w")
        
        # Pivot method selection
        ttk.Label(self.excel_options_frame, text="Pivot Method:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        self.pivot_method_combo = ttk.Combobox(
            self.excel_options_frame, 
            textvariable=self.pivot_method,
            values=["auto", "windows", "cross-platform"],
            state="readonly",
            width=15
        )
        self.pivot_method_combo.grid(row=1, column=1, sticky="w", padx=5, pady=(5, 0))
        self.pivot_method_combo.bind("<<ComboboxSelected>>", self._on_pivot_method_change)
        
        # Pivot method info label
        self.pivot_method_info = ttk.Label(self.excel_options_frame, text="", foreground="gray")
        self.pivot_method_info.grid(row=1, column=2, sticky="w", padx=(5, 0), pady=(5, 0))
        self._update_pivot_method_info()
        
        # Pivot per account checkbox
        self.pivot_per_account_checkbox = ttk.Checkbutton(
            self.excel_options_frame,
            text="Create Pivot per Account",
            variable=self.pivot_per_account
        )
        self.pivot_per_account_checkbox.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))
        
        # Initially hide Excel options
        self.excel_options_frame.grid_remove()
        
        # Filters section
        filter_frame = ttk.LabelFrame(main_frame, text="Filters", padding="5")
        filter_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(filter_frame, text="Status Filters (leave unchecked for all):").grid(row=0, column=0, columnspan=4, sticky="w")
        
        ttk.Checkbutton(filter_frame, text="Supported", variable=self.filter_supported).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(filter_frame, text="Approaching EOS", variable=self.filter_approaching).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(filter_frame, text="Extended Support", variable=self.filter_extended).grid(row=1, column=2, sticky="w")
        ttk.Checkbutton(filter_frame, text="Out of Support", variable=self.filter_oos).grid(row=1, column=3, sticky="w")
        
        ttk.Label(filter_frame, text="Days Threshold:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(filter_frame, from_=1, to=365, textvariable=self.days_threshold, width=10).grid(row=2, column=1, sticky="w", pady=(10, 0))
        ttk.Label(filter_frame, text="(days before EOS to mark as 'Approaching')").grid(row=2, column=2, columnspan=2, sticky="w", pady=(10, 0))
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, pady=10)
        
        self.generate_btn = ttk.Button(button_frame, text="Generate Report", command=self._generate_report)
        self.generate_btn.grid(row=0, column=0, padx=5)
        
        ttk.Button(button_frame, text="Clear", command=self._clear_form).grid(row=0, column=1, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Results / Preview", padding="5")
        results_frame.grid(row=6, column=0, sticky="nsew", pady=(0, 10))
        
        # Text widget with scrollbar
        self.results_text = tk.Text(results_frame, wrap=tk.NONE, height=15)
        scrollbar_y = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_text.yview)
        scrollbar_x = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_text.xview)
        self.results_text.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.results_text.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.grid(row=7, column=0, sticky="ew")
        
        # Configure main frame grid
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
    def _configure_grid(self):
        """Configure root window grid."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def _browse_input(self):
        """Open file dialog for input CSV file."""
        filename = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
            
    def _browse_output(self):
        """Open file dialog for output file."""
        fmt = self.output_format.get()
        extensions = {
            "text": [("Text files", "*.txt"), ("All files", "*.*")],
            "csv": [("CSV files", "*.csv"), ("All files", "*.*")],
            "json": [("JSON files", "*.json"), ("All files", "*.*")],
            "excel": [("Excel files", "*.xlsx"), ("All files", "*.*")],
        }
        default_ext = {"text": ".txt", "csv": ".csv", "json": ".json", "excel": ".xlsx"}
        
        filename = filedialog.asksaveasfilename(
            title="Save Report As",
            filetypes=extensions.get(fmt, [("All files", "*.*")]),
            defaultextension=default_ext.get(fmt, "")
        )
        if filename:
            self.output_file.set(filename)
            
    def _on_format_change(self, event=None):
        """Handle output format change."""
        fmt = self.output_format.get()
        if fmt == "excel":
            if not EXCEL_AVAILABLE:
                messagebox.showwarning(
                    "Excel Support",
                    "Excel output requires openpyxl. Install with: pip install openpyxl"
                )
            # Show Excel options
            self.excel_options_frame.grid()
        else:
            # Hide Excel options
            self.excel_options_frame.grid_remove()
    
    def _on_pivot_toggle(self):
        """Handle pivot checkbox toggle."""
        if self.include_pivot.get():
            self.pivot_method_combo.configure(state="readonly")
            self.pivot_per_account_checkbox.configure(state="normal")
        else:
            self.pivot_method_combo.configure(state="disabled")
            self.pivot_per_account_checkbox.configure(state="disabled")
    
    def _on_pivot_method_change(self, event=None):
        """Handle pivot method selection change."""
        self._update_pivot_method_info()
    
    def _update_pivot_method_info(self):
        """Update the pivot method info label based on selection."""
        method = self.pivot_method.get()
        if method == "auto":
            if WIN32COM_AVAILABLE:
                info = "(Will use Windows Excel COM)"
            else:
                template_path = os.path.join(TEMPLATE_DIR, "pivot_template.xlsx")
                if os.path.exists(template_path):
                    info = "(Will use template)"
                else:
                    info = "(Will use styled summary)"
        elif method == "windows":
            if WIN32COM_AVAILABLE:
                info = "(Excel COM - real pivot)"
            else:
                info = "(Not available - Excel not installed)"
        else:  # cross-platform
            template_path = os.path.join(TEMPLATE_DIR, "pivot_template.xlsx")
            if os.path.exists(template_path):
                info = "(Template - refreshes on open)"
            else:
                info = "(Styled summary - no template)"
        
        self.pivot_method_info.configure(text=info)
    
    def _get_pivot_info(self) -> str:
        """Get information about pivot table support on current platform."""
        if WIN32COM_AVAILABLE:
            return "(Real pivot table - Windows with Excel)"
        else:
            template_path = os.path.join(TEMPLATE_DIR, "pivot_template.xlsx")
            if os.path.exists(template_path):
                return "(Real pivot table from template - refreshes on open)"
            else:
                return "(Styled summary - no template found)"
            
    def _clear_form(self):
        """Clear all form fields."""
        self.input_file.set("")
        self.output_file.set("")
        self.output_format.set("text")
        self.days_threshold.set(90)
        self.filter_supported.set(False)
        self.filter_approaching.set(False)
        self.filter_extended.set(False)
        self.filter_oos.set(False)
        self.include_pivot.set(True)
        self.pivot_method.set("auto")
        self.pivot_per_account.set(False)
        self.pivot_method_combo.configure(state="readonly")
        self.pivot_per_account_checkbox.configure(state="normal")
        self._update_pivot_method_info()
        self.results_text.delete("1.0", tk.END)
        self.status_var.set("Ready")
        # Hide Excel options
        self.excel_options_frame.grid_remove()
        
    def _get_status_filters(self) -> Optional[List[SupportStatus]]:
        """Get selected status filters."""
        filters = []
        if self.filter_supported.get():
            filters.append(SupportStatus.SUPPORTED)
        if self.filter_approaching.get():
            filters.append(SupportStatus.APPROACHING_EOS)
        if self.filter_extended.get():
            filters.append(SupportStatus.EXTENDED_SUPPORT)
        if self.filter_oos.get():
            filters.append(SupportStatus.OUT_OF_SUPPORT)
        return filters if filters else None
        
    def _generate_report(self):
        """Generate the report in a background thread."""
        # Validate input
        input_path = self.input_file.get().strip()
        if not input_path:
            messagebox.showerror("Error", "Please select an input CSV file.")
            return
            
        if not os.path.exists(input_path):
            messagebox.showerror("Error", f"Input file not found: {input_path}")
            return
            
        output_path = self.output_file.get().strip()
        fmt = self.output_format.get()
        
        if fmt == "excel" and not output_path:
            messagebox.showerror("Error", "Excel format requires an output file path.")
            return
            
        # Disable button and start progress
        self.generate_btn.configure(state="disabled")
        self.progress.start()
        self.status_var.set("Generating report...")
        self.results_text.delete("1.0", tk.END)
        
        # Run in background thread
        thread = threading.Thread(target=self._run_generation, args=(input_path, output_path, fmt))
        thread.daemon = True
        thread.start()
        
    def _run_generation(self, input_path: str, output_path: str, fmt: str):
        """Run report generation in background thread."""
        try:
            # Parse CSV
            self._update_status("Parsing CSV file...")
            parser = CSVParser(input_path)
            resources = parser.parse()
            
            # Get filters
            status_filters = self._get_status_filters()
            filters = None
            if status_filters:
                filters = ReportFilters(statuses=status_filters)
                
            # Classify and generate
            self._update_status(f"Classifying {len(resources)} resources...")
            classifier = ResourceClassifier(days_threshold=self.days_threshold.get())
            generator = ReportGenerator(resources, classifier)
            report = generator.generate(filters=filters)
            
            # Format output
            self._update_status("Formatting report...")
            if fmt == "excel":
                formatter = ExcelFormatter()
                include_pivot = self.include_pivot.get()
                pivot_method = self.pivot_method.get() if include_pivot else None
                pivot_per_account = self.pivot_per_account.get() if include_pivot else False
                formatter.format_to_file(
                    report, 
                    output_path, 
                    include_pivot=include_pivot, 
                    pivot_method=pivot_method,
                    pivot_per_account=pivot_per_account
                )
                output_text = f"Excel report saved to: {output_path}\n\n"
                if include_pivot:
                    output_text += self._get_pivot_status(pivot_method, pivot_per_account) + "\n\n"
                output_text += self._get_summary(report)
            else:
                formatters = {
                    "text": TextFormatter(),
                    "csv": CSVFormatter(),
                    "json": JSONFormatter(),
                }
                formatter = formatters[fmt]
                output_text = formatter.format(report)
                
                # Save to file if specified
                if output_path:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(output_text)
                        
            # Update UI
            self._show_results(output_text, report, output_path)
            
        except CSVParseError as e:
            self._show_error(f"CSV Parse Error: {e}")
        except Exception as e:
            self._show_error(f"Error: {e}")
        finally:
            self._finish_generation()
            
    def _get_summary(self, report) -> str:
        """Get a text summary of the report."""
        lines = [
            "=" * 50,
            "REPORT SUMMARY",
            "=" * 50,
            f"Total resources: {report.total_resources}",
            "",
        ]
        for status in SupportStatus:
            count = report.total_counts.get(status, 0)
            if count > 0:
                lines.append(f"  {status.value}: {count}")
        lines.append("=" * 50)
        return "\n".join(lines)
    
    def _get_pivot_status(self, pivot_method: str = "auto", pivot_per_account: bool = False) -> str:
        """Get status message about pivot table creation."""
        mode_suffix = " (per account)" if pivot_per_account else ""
        
        if pivot_method == "windows" or (pivot_method == "auto" and WIN32COM_AVAILABLE):
            if WIN32COM_AVAILABLE:
                return f"Pivot Table: Created using Excel COM automation (Windows){mode_suffix}"
            else:
                return "Pivot Table: Windows method not available (Excel not installed)"
        else:
            template_path = os.path.join(TEMPLATE_DIR, "pivot_template.xlsx")
            if os.path.exists(template_path):
                return f"Pivot Table: Created from template (will refresh when opened in Excel){mode_suffix}"
            else:
                return f"Pivot Table: Styled summary (template not found for real pivot){mode_suffix}"
        
    def _update_status(self, message: str):
        """Update status bar from background thread."""
        self.root.after(0, lambda: self.status_var.set(message))
        
    def _show_results(self, text: str, report, output_path: str):
        """Show results in the text widget."""
        def update():
            self.results_text.delete("1.0", tk.END)
            # Limit preview for large outputs
            if len(text) > 50000:
                self.results_text.insert("1.0", text[:50000] + "\n\n... (truncated for preview)")
            else:
                self.results_text.insert("1.0", text)
                
            if output_path:
                self.status_var.set(f"Report saved to: {output_path}")
            else:
                self.status_var.set(f"Generated report with {report.total_resources} resources")
                
        self.root.after(0, update)
        
    def _show_error(self, message: str):
        """Show error message."""
        def update():
            messagebox.showerror("Error", message)
            self.status_var.set("Error occurred")
        self.root.after(0, update)
        
    def _finish_generation(self):
        """Re-enable UI after generation."""
        def update():
            self.progress.stop()
            self.generate_btn.configure(state="normal")
        self.root.after(0, update)
        
    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


def main():
    """Entry point for GUI application."""
    app = EndOfSupportGUI()
    app.run()


if __name__ == "__main__":
    main()
