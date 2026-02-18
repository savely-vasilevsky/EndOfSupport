"""Cross-platform GUI for EndOfSupportTool.

Provides a wizard-style graphical interface for analyzing AWS resource inventory
and generating support status reports.

Wizard Steps:
1. Data Source Selection - Choose between CSV file or AWS Fetch
2. Output Configuration - Configure report format and options
"""

import logging
import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from typing import Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Version
try:
    from . import __version__
except ImportError:
    __version__ = "2.4.3"

# Handle imports for both package and frozen executable modes
try:
    from .classifier import ResourceClassifier
    from .formatters import TextFormatter, CSVFormatter, JSONFormatter, ExcelFormatter, EXCEL_AVAILABLE, WIN32COM_AVAILABLE, TEMPLATE_DIR
    from .html_formatter import HTMLFormatter
    from .generator import ReportGenerator
    from .models import ReportFilters, SupportStatus, GenerationParameters
    from .parser import CSVParser, CSVParseError
except ImportError:
    from classifier import ResourceClassifier
    from formatters import TextFormatter, CSVFormatter, JSONFormatter, ExcelFormatter, EXCEL_AVAILABLE, WIN32COM_AVAILABLE, TEMPLATE_DIR
    from html_formatter import HTMLFormatter
    from generator import ReportGenerator
    from models import ReportFilters, SupportStatus, GenerationParameters
    from parser import CSVParser, CSVParseError


class EndOfSupportGUI:
    """Main GUI application for EndOfSupportTool with wizard-style interface."""
    
    def __init__(self):
        """Initialize the GUI application."""
        self.root = tk.Tk()
        self.root.title(f"AWS End-of-Support Tool v{__version__}")
        self.root.geometry("850x700")
        self.root.minsize(750, 600)
        
        # Wizard state
        self.current_step = 1
        self.data_source = tk.StringVar(value="csv")  # "csv" or "fetch"
        
        # CSV input variables
        self.input_file = tk.StringVar()
        
        # AWS Fetch variables
        self.aws_profile = tk.StringVar()
        self.aws_regions = tk.StringVar()
        self.include_costs = tk.BooleanVar(value=True)
        self.fetch_workers = tk.IntVar(value=10)
        
        # Output variables
        self.output_file = tk.StringVar()
        self.output_format = tk.StringVar(value="html")
        self.days_threshold = tk.IntVar(value=90)
        
        # Status filter checkboxes
        self.filter_supported = tk.BooleanVar(value=False)
        self.filter_approaching = tk.BooleanVar(value=True)
        self.filter_extended_year_1 = tk.BooleanVar(value=True)
        self.filter_extended_year_2 = tk.BooleanVar(value=True)
        self.filter_extended_year_3 = tk.BooleanVar(value=True)
        self.filter_oos = tk.BooleanVar(value=True)
        
        # Excel options
        self.include_pivot = tk.BooleanVar(value=True)
        self.pivot_method = tk.StringVar(value="auto")
        self.pivot_per_account = tk.BooleanVar(value=False)
        self.include_timeline = tk.BooleanVar(value=True)
        self.include_version_details = tk.BooleanVar(value=False)
        
        # Fetched resources (stored after fetch)
        self.fetched_resources = None
        self.fetched_csv_path = None
        
        # Build UI
        self._create_widgets()
        self._configure_grid()
        self._show_step(1)
        
        # Bind keyboard shortcuts
        self.root.bind("<F1>", lambda e: self._show_help())
        
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Header with step indicator
        self._create_header()
        
        # Step containers (we'll show/hide these)
        self._create_step1_frame()
        self._create_step2_frame()
        
        # Navigation buttons
        self._create_navigation()
        
        # Progress bar
        self.progress = ttk.Progressbar(self.main_frame, mode="indeterminate")
        self.progress.grid(row=4, column=0, sticky="ew", pady=(10, 5))
        
        # Results section
        self._create_results_section()
        
        # Status bar (clickable when showing file path)
        self.status_var = tk.StringVar(value="Ready - Select data source")
        self.last_output_path = None  # Store the last output path for clicking
        
        self.status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief="sunken", anchor="w")
        self.status_bar.grid(row=6, column=0, sticky="ew")
        self.status_bar.bind("<Button-1>", self._on_status_click)
        self.status_bar.bind("<Enter>", self._on_status_hover_enter)
        self.status_bar.bind("<Leave>", self._on_status_hover_leave)
        
        # Configure main frame grid
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(5, weight=1)
        
    def _create_header(self):
        """Create the wizard header with step indicator."""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Title
        title_label = ttk.Label(header_frame, text=f"AWS End-of-Support Tool v{__version__}", 
                                font=("Helvetica", 14, "bold"))
        title_label.grid(row=0, column=0, sticky="w")
        
        # Step indicator frame
        step_frame = ttk.Frame(header_frame)
        step_frame.grid(row=0, column=1, sticky="e")
        
        self.step1_label = ttk.Label(step_frame, text="① Data Source", font=("Helvetica", 10, "bold"))
        self.step1_label.grid(row=0, column=0, padx=10)
        
        ttk.Label(step_frame, text="→").grid(row=0, column=1)
        
        self.step2_label = ttk.Label(step_frame, text="② Output Options", font=("Helvetica", 10))
        self.step2_label.grid(row=0, column=2, padx=10)
        
        header_frame.columnconfigure(0, weight=1)

    def _create_step1_frame(self):
        """Create Step 1: Data Source Selection."""
        self.step1_frame = ttk.LabelFrame(self.main_frame, text="Step 1: Select Data Source", padding="10")
        self.step1_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        # Radio buttons for data source selection
        source_frame = ttk.Frame(self.step1_frame)
        source_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Radiobutton(source_frame, text="Load from CSV File", variable=self.data_source, 
                        value="csv", command=self._on_source_change).grid(row=0, column=0, sticky="w", padx=(0, 20))
        ttk.Radiobutton(source_frame, text="Fetch from AWS", variable=self.data_source,
                        value="fetch", command=self._on_source_change).grid(row=0, column=1, sticky="w")
        
        # CSV Input Frame
        self.csv_frame = ttk.LabelFrame(self.step1_frame, text="CSV File Input", padding="5")
        self.csv_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(self.csv_frame, text="CSV File:").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.csv_frame, textvariable=self.input_file, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(self.csv_frame, text="Browse...", command=self._browse_input).grid(row=0, column=2)
        
        csv_info = ttk.Label(self.csv_frame, text="Select a CSV file exported from AWS Command Center or the fetch script",
                            foreground="gray", font=("Helvetica", 9))
        csv_info.grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))
        
        # AWS Fetch Frame
        self.fetch_frame = ttk.LabelFrame(self.step1_frame, text="AWS Fetch Configuration", padding="5")
        self.fetch_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        # Profile
        ttk.Label(self.fetch_frame, text="AWS Profile:").grid(row=0, column=0, sticky="w")
        profile_entry = ttk.Entry(self.fetch_frame, textvariable=self.aws_profile, width=30)
        profile_entry.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(self.fetch_frame, text="(leave empty for default)", foreground="gray").grid(row=0, column=2, sticky="w")
        
        # Regions
        ttk.Label(self.fetch_frame, text="Regions:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        regions_entry = ttk.Entry(self.fetch_frame, textvariable=self.aws_regions, width=50)
        regions_entry.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=(5, 0))
        ttk.Label(self.fetch_frame, text="Comma-separated (e.g., us-east-1,eu-west-1) or leave empty for all",
                 foreground="gray", font=("Helvetica", 9)).grid(row=2, column=1, columnspan=2, sticky="w", padx=5)
        
        # Workers
        ttk.Label(self.fetch_frame, text="Parallel Workers:").grid(row=3, column=0, sticky="w", pady=(5, 0))
        ttk.Spinbox(self.fetch_frame, from_=1, to=20, textvariable=self.fetch_workers, width=10).grid(row=3, column=1, sticky="w", padx=5, pady=(5, 0))
        
        # Include costs
        ttk.Checkbutton(self.fetch_frame, text="Include Extended Support Cost Estimates", 
                       variable=self.include_costs).grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))
        
        # Services info
        services_info = ttk.Label(self.fetch_frame, 
            text="Services: Lambda, EKS, RDS, Aurora, DocumentDB, Neptune, ElastiCache, OpenSearch, MSK, Amazon MQ",
            foreground="gray", font=("Helvetica", 9))
        services_info.grid(row=5, column=0, columnspan=3, sticky="w", pady=(10, 0))
        
        # Initially hide fetch frame
        self.fetch_frame.grid_remove()
        
        self.step1_frame.columnconfigure(0, weight=1)

    def _create_step2_frame(self):
        """Create Step 2: Output Configuration."""
        self.step2_frame = ttk.LabelFrame(self.main_frame, text="Step 2: Configure Output", padding="10")
        self.step2_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        
        # Output section
        output_frame = ttk.LabelFrame(self.step2_frame, text="Output", padding="5")
        output_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(output_frame, text="Format:").grid(row=0, column=0, sticky="w")
        format_combo = ttk.Combobox(output_frame, textvariable=self.output_format, 
                                     values=["html", "excel", "text", "csv", "json"], state="readonly", width=15)
        format_combo.grid(row=0, column=1, sticky="w", padx=5)
        format_combo.bind("<<ComboboxSelected>>", self._on_format_change)
        
        ttk.Label(output_frame, text="Output File:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Entry(output_frame, textvariable=self.output_file, width=60).grid(row=1, column=1, padx=5, pady=(5, 0))
        ttk.Button(output_frame, text="Browse...", command=self._browse_output).grid(row=1, column=2, pady=(5, 0))
        
        output_frame.columnconfigure(1, weight=1)
        
        # Excel options
        self.excel_options_frame = ttk.LabelFrame(self.step2_frame, text="Excel Options", padding="5")
        self.excel_options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        self.pivot_checkbox = ttk.Checkbutton(self.excel_options_frame, text="Include Pivot Table", 
                                              variable=self.include_pivot, command=self._on_pivot_toggle)
        self.pivot_checkbox.grid(row=0, column=0, sticky="w")
        
        ttk.Label(self.excel_options_frame, text="Pivot Method:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.pivot_method_combo = ttk.Combobox(self.excel_options_frame, textvariable=self.pivot_method,
                                               values=["auto", "windows", "cross-platform"], state="readonly", width=15)
        self.pivot_method_combo.grid(row=1, column=1, sticky="w", padx=5, pady=(5, 0))
        self.pivot_method_combo.bind("<<ComboboxSelected>>", self._on_pivot_method_change)
        
        self.pivot_method_info = ttk.Label(self.excel_options_frame, text="", foreground="gray")
        self.pivot_method_info.grid(row=1, column=2, sticky="w", padx=(5, 0), pady=(5, 0))
        self._update_pivot_method_info()
        
        self.pivot_per_account_checkbox = ttk.Checkbutton(self.excel_options_frame, text="Create Pivot per Account",
                                                          variable=self.pivot_per_account)
        self.pivot_per_account_checkbox.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))
        
        self.timeline_checkbox = ttk.Checkbutton(self.excel_options_frame, text="Include Timeline View",
                                                 variable=self.include_timeline)
        self.timeline_checkbox.grid(row=3, column=0, columnspan=2, sticky="w", pady=(5, 0))
        
        self.version_details_checkbox = ttk.Checkbutton(self.excel_options_frame, text="Include Version Details",
                                                        variable=self.include_version_details)
        self.version_details_checkbox.grid(row=4, column=0, columnspan=2, sticky="w", pady=(5, 0))
        
        self.excel_options_frame.grid_remove()
        
        # Filters section
        filter_frame = ttk.LabelFrame(self.step2_frame, text="Filters", padding="5")
        filter_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(filter_frame, text="Status Filters (leave unchecked for all):").grid(row=0, column=0, columnspan=6, sticky="w")
        
        ttk.Checkbutton(filter_frame, text="Regular Support", variable=self.filter_supported).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(filter_frame, text="Approaching EOS", variable=self.filter_approaching).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(filter_frame, text="Ext Sup Yr 1", variable=self.filter_extended_year_1).grid(row=1, column=2, sticky="w")
        ttk.Checkbutton(filter_frame, text="Ext Sup Yr 2", variable=self.filter_extended_year_2).grid(row=1, column=3, sticky="w")
        ttk.Checkbutton(filter_frame, text="Ext Sup Yr 3", variable=self.filter_extended_year_3).grid(row=1, column=4, sticky="w")
        ttk.Checkbutton(filter_frame, text="Out of Support", variable=self.filter_oos).grid(row=1, column=5, sticky="w")
        
        ttk.Label(filter_frame, text="Days Threshold:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(filter_frame, from_=1, to=365, textvariable=self.days_threshold, width=10).grid(row=2, column=1, sticky="w", pady=(10, 0))
        ttk.Label(filter_frame, text="(days before EOS to mark as 'Approaching')").grid(row=2, column=2, columnspan=3, sticky="w", pady=(10, 0))
        
        self.step2_frame.columnconfigure(0, weight=1)
        self.step2_frame.grid_remove()

    def _create_navigation(self):
        """Create navigation buttons."""
        self.nav_frame = ttk.Frame(self.main_frame)
        self.nav_frame.grid(row=3, column=0, pady=10)
        
        self.back_btn = ttk.Button(self.nav_frame, text="← Back", command=self._go_back)
        self.back_btn.grid(row=0, column=0, padx=5)
        
        self.next_btn = ttk.Button(self.nav_frame, text="Next →", command=self._go_next)
        self.next_btn.grid(row=0, column=1, padx=5)
        
        self.generate_btn = ttk.Button(self.nav_frame, text="Generate Report", command=self._generate_report)
        self.generate_btn.grid(row=0, column=2, padx=5)
        
        ttk.Button(self.nav_frame, text="Clear", command=self._clear_form).grid(row=0, column=3, padx=5)
        ttk.Button(self.nav_frame, text="Help", command=self._show_help).grid(row=0, column=4, padx=5)
        
    def _create_results_section(self):
        """Create the results/preview section."""
        results_frame = ttk.LabelFrame(self.main_frame, text="Results / Preview", padding="5")
        results_frame.grid(row=5, column=0, sticky="nsew", pady=(0, 10))
        
        self.results_text = tk.Text(results_frame, wrap=tk.NONE, height=12)
        scrollbar_y = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_text.yview)
        scrollbar_x = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_text.xview)
        self.results_text.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.results_text.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
    def _configure_grid(self):
        """Configure root window grid."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def _show_step(self, step: int):
        """Show the specified wizard step."""
        self.current_step = step
        
        # Update step indicator
        if step == 1:
            self.step1_label.configure(font=("Helvetica", 10, "bold"))
            self.step2_label.configure(font=("Helvetica", 10))
            self.step1_frame.grid()
            self.step2_frame.grid_remove()
            self.back_btn.configure(state="disabled")
            self.next_btn.configure(state="normal")
            self.generate_btn.configure(state="disabled")
            self.status_var.set("Step 1: Select your data source")
        else:
            self.step1_label.configure(font=("Helvetica", 10))
            self.step2_label.configure(font=("Helvetica", 10, "bold"))
            self.step1_frame.grid_remove()
            self.step2_frame.grid()
            self.back_btn.configure(state="normal")
            self.next_btn.configure(state="disabled")
            self.generate_btn.configure(state="normal")
            self.status_var.set("Step 2: Configure output options and generate report")
            
    def _go_back(self):
        """Go to previous step."""
        if self.current_step > 1:
            self._show_step(self.current_step - 1)
            
    def _go_next(self):
        """Go to next step with validation."""
        if self.current_step == 1:
            # Validate step 1
            if self.data_source.get() == "csv":
                input_path = self.input_file.get().strip()
                if not input_path:
                    messagebox.showerror("Error", "Please select an input CSV file.")
                    return
                if not os.path.exists(input_path):
                    messagebox.showerror("Error", f"Input file not found: {input_path}")
                    return
                self._show_step(2)
            else:
                # For fetch, we need to fetch first
                self._fetch_aws_resources()
                
    def _on_source_change(self):
        """Handle data source radio button change."""
        if self.data_source.get() == "csv":
            self.csv_frame.grid()
            self.fetch_frame.grid_remove()
        else:
            self.csv_frame.grid_remove()
            self.fetch_frame.grid()

    def _fetch_aws_resources(self):
        """Fetch AWS resources in background thread."""
        self.next_btn.configure(state="disabled")
        self.progress.start()
        self.status_var.set("Fetching AWS resources...")
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", "Fetching AWS resources...\n\n")
        
        thread = threading.Thread(target=self._run_fetch)
        thread.daemon = True
        thread.start()
        
    def _run_fetch(self):
        """Run AWS fetch in background thread."""
        try:
            # Import the fetcher
            import tempfile
            scripts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
            sys.path.insert(0, scripts_dir)
            
            from fetch_aws_resources import AWSResourceFetcher
            
            # Get parameters
            profile = self.aws_profile.get().strip() or None
            regions_str = self.aws_regions.get().strip()
            regions = regions_str.split(',') if regions_str else None
            regions = [r.strip() for r in regions] if regions else None
            workers = self.fetch_workers.get()
            include_costs = self.include_costs.get()
            
            self._update_status(f"Connecting to AWS...")
            self._append_result(f"Profile: {profile or 'default'}\n")
            self._append_result(f"Regions: {', '.join(regions) if regions else 'all'}\n")
            self._append_result(f"Workers: {workers}\n")
            self._append_result(f"Include costs: {include_costs}\n\n")
            
            # Create fetcher
            fetcher = AWSResourceFetcher(
                profile=profile,
                regions=regions,
                include_costs=include_costs
            )
            
            self._update_status(f"Fetching from {len(fetcher.regions)} regions...")
            self._append_result(f"Account: {fetcher.account_id} ({fetcher.account_alias})\n")
            self._append_result(f"Fetching from {len(fetcher.regions)} regions...\n\n")
            
            # Fetch all resources
            fetcher.fetch_all(max_workers=workers)
            
            self._append_result(f"\nTotal resources found: {len(fetcher.resources)}\n")
            
            if not fetcher.resources:
                self._update_status("No resources found")
                self._append_result("\nNo resources found. Check your AWS credentials and permissions.\n")
                self._finish_fetch(success=False)
                return
            
            # Save to temp CSV file
            temp_dir = tempfile.gettempdir()
            temp_csv = os.path.join(temp_dir, f"aws_inventory_{fetcher.account_id}.csv")
            fetcher.to_csv(temp_csv)
            
            self.fetched_csv_path = temp_csv
            self._append_result(f"\nSaved to: {temp_csv}\n")
            
            # Show summary
            self._append_result("\n" + "=" * 50 + "\n")
            self._append_result("FETCH COMPLETE\n")
            self._append_result("=" * 50 + "\n")
            self._append_result(f"Resources: {len(fetcher.resources)}\n")
            
            # Count by service
            service_counts = {}
            for r in fetcher.resources:
                svc = r.get("Service", "Unknown")
                service_counts[svc] = service_counts.get(svc, 0) + 1
            
            self._append_result("\nBy Service:\n")
            for svc, count in sorted(service_counts.items()):
                self._append_result(f"  {svc}: {count}\n")
            
            self._update_status(f"Fetched {len(fetcher.resources)} resources")
            self._finish_fetch(success=True)
            
        except ImportError as e:
            self._show_error(f"Could not import fetch module: {e}\n\nMake sure boto3 is installed: pip install boto3")
            self._finish_fetch(success=False)
        except Exception as e:
            logger.error(f"Fetch error: {e}", exc_info=True)
            self._show_error(f"Fetch error: {e}")
            self._finish_fetch(success=False)
            
    def _finish_fetch(self, success: bool):
        """Finish fetch operation."""
        def update():
            self.progress.stop()
            self.next_btn.configure(state="normal")
            if success and self.fetched_csv_path:
                self.input_file.set(self.fetched_csv_path)
                self._show_step(2)
        self.root.after(0, update)
        
    def _append_result(self, text: str):
        """Append text to results."""
        def update():
            self.results_text.insert(tk.END, text)
            self.results_text.see(tk.END)
        self.root.after(0, update)

    def _browse_input(self):
        """Open file dialog for input CSV file."""
        filename = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=os.getcwd()
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
            "html": [("HTML files", "*.html"), ("All files", "*.*")],
        }
        default_ext = {"text": ".txt", "csv": ".csv", "json": ".json", "excel": ".xlsx", "html": ".html"}
        
        initial_dir = None
        input_path = self.input_file.get().strip()
        if input_path and os.path.exists(input_path):
            initial_dir = os.path.dirname(input_path)
        if not initial_dir:
            initial_dir = os.getcwd()
        
        filename = filedialog.asksaveasfilename(
            title="Save Report As",
            filetypes=extensions.get(fmt, [("All files", "*.*")]),
            defaultextension=default_ext.get(fmt, ""),
            initialdir=initial_dir
        )
        if filename:
            self.output_file.set(filename)
            
    def _on_format_change(self, event=None):
        """Handle output format change."""
        fmt = self.output_format.get()
        if fmt == "excel":
            if not EXCEL_AVAILABLE:
                messagebox.showwarning("Excel Support", "Excel output requires openpyxl. Install with: pip install openpyxl")
            self.excel_options_frame.grid()
        else:
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
        """Update the pivot method info label."""
        method = self.pivot_method.get()
        if method == "auto":
            if WIN32COM_AVAILABLE:
                info = "(Will use Windows Excel COM)"
            else:
                template_path = os.path.join(TEMPLATE_DIR, "pivot_template.xlsx")
                info = "(Will use template)" if os.path.exists(template_path) else "(Will use styled summary)"
        elif method == "windows":
            info = "(Excel COM - real pivot)" if WIN32COM_AVAILABLE else "(Not available - Excel not installed)"
        else:
            template_path = os.path.join(TEMPLATE_DIR, "pivot_template.xlsx")
            info = "(Template - refreshes on open)" if os.path.exists(template_path) else "(Styled summary - no template)"
        self.pivot_method_info.configure(text=info)
            
    def _clear_form(self):
        """Clear all form fields."""
        self.data_source.set("csv")
        self.input_file.set("")
        self.aws_profile.set("")
        self.aws_regions.set("")
        self.include_costs.set(True)
        self.fetch_workers.set(10)
        self.output_file.set("")
        self.output_format.set("html")
        self.days_threshold.set(90)
        self.filter_supported.set(False)
        self.filter_approaching.set(True)
        self.filter_extended_year_1.set(True)
        self.filter_extended_year_2.set(True)
        self.filter_extended_year_3.set(True)
        self.filter_oos.set(True)
        self.include_pivot.set(True)
        self.pivot_method.set("auto")
        self.pivot_per_account.set(False)
        self.include_timeline.set(True)
        self.include_version_details.set(False)
        self.pivot_method_combo.configure(state="readonly")
        self.pivot_per_account_checkbox.configure(state="normal")
        self._update_pivot_method_info()
        self.results_text.delete("1.0", tk.END)
        self.fetched_csv_path = None
        self.last_output_path = None  # Clear clickable path
        self._on_source_change()
        self.excel_options_frame.grid_remove()
        self._show_step(1)
        
    def _get_status_filters(self) -> Optional[List[SupportStatus]]:
        """Get selected status filters."""
        filters = []
        if self.filter_supported.get():
            filters.append(SupportStatus.SUPPORTED)
        if self.filter_approaching.get():
            filters.append(SupportStatus.APPROACHING_EOS)
        if self.filter_extended_year_1.get():
            filters.append(SupportStatus.EXTENDED_SUPPORT_YEAR_1)
        if self.filter_extended_year_2.get():
            filters.append(SupportStatus.EXTENDED_SUPPORT_YEAR_2)
        if self.filter_extended_year_3.get():
            filters.append(SupportStatus.EXTENDED_SUPPORT_YEAR_3)
        if self.filter_oos.get():
            filters.append(SupportStatus.OUT_OF_SUPPORT)
        return filters if filters else None

    def _generate_report(self):
        """Generate the report in a background thread."""
        input_path = self.input_file.get().strip()
        if not input_path:
            messagebox.showerror("Error", "No input file specified.")
            return
            
        if not os.path.exists(input_path):
            messagebox.showerror("Error", f"Input file not found: {input_path}")
            return
            
        output_path = self.output_file.get().strip()
        fmt = self.output_format.get()
        
        if fmt == "excel" and not output_path:
            messagebox.showerror("Error", "Excel format requires an output file path.")
            return
            
        self.generate_btn.configure(state="disabled")
        self.back_btn.configure(state="disabled")
        self.progress.start()
        self.status_var.set("Generating report...")
        self.results_text.delete("1.0", tk.END)
        
        thread = threading.Thread(target=self._run_generation, args=(input_path, output_path, fmt))
        thread.daemon = True
        thread.start()
        
    def _run_generation(self, input_path: str, output_path: str, fmt: str):
        """Run report generation in background thread."""
        try:
            self._update_status("Parsing CSV file...")
            logger.info(f"Parsing CSV file: {input_path}")
            parser = CSVParser(input_path)
            resources = parser.parse()
            logger.info(f"Parsed {len(resources)} resources")
            
            status_filters = self._get_status_filters()
            filters = ReportFilters(statuses=status_filters) if status_filters else None
                
            self._update_status(f"Classifying {len(resources)} resources...")
            classifier = ResourceClassifier(days_threshold=self.days_threshold.get())
            generator = ReportGenerator(resources, classifier)
            report = generator.generate(filters=filters)
            
            report.generation_params = GenerationParameters(
                input_file=os.path.basename(input_path),
                output_format=fmt,
                days_threshold=self.days_threshold.get(),
                status_filters=[s.value for s in status_filters] if status_filters else None,
            )
            
            self._update_status("Formatting report...")
            if fmt == "excel":
                formatter = ExcelFormatter()
                include_pivot = self.include_pivot.get()
                pivot_method = self.pivot_method.get() if include_pivot else None
                pivot_per_account = self.pivot_per_account.get() if include_pivot else False
                include_timeline = self.include_timeline.get()
                include_version_details = self.include_version_details.get()
                
                formatter.format_to_file(
                    report, output_path, 
                    include_pivot=include_pivot, 
                    pivot_method=pivot_method,
                    pivot_per_account=pivot_per_account,
                    include_timeline=include_timeline,
                    include_version_details=include_version_details
                )
                
                output_text = f"Excel report saved to: {output_path}\n\n"
                if include_pivot:
                    output_text += self._get_pivot_status(pivot_method, pivot_per_account) + "\n"
                    try:
                        from openpyxl import load_workbook
                        verify_wb = load_workbook(output_path, read_only=True)
                        sheets = verify_wb.sheetnames
                        verify_wb.close()
                        output_text += f"Sheets: {', '.join(sheets)}\n\n"
                    except Exception as e:
                        output_text += f"Could not verify file: {e}\n\n"
                output_text += self._get_summary(report)
            else:
                formatters = {
                    "text": TextFormatter(),
                    "csv": CSVFormatter(),
                    "json": JSONFormatter(),
                    "html": HTMLFormatter(),
                }
                formatter = formatters[fmt]
                output_text = formatter.format(report)
                
                if output_path:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(output_text)
                        
            self._show_results(output_text, report, output_path)
            
        except CSVParseError as e:
            logger.error(f"CSV Parse Error: {e}", exc_info=True)
            self._show_error(f"CSV Parse Error: {e}")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            self._show_error(f"Error: {e}")
        finally:
            self._finish_generation()
            
    def _get_summary(self, report) -> str:
        """Get a text summary of the report."""
        lines = ["=" * 50, "REPORT SUMMARY", "=" * 50, f"Total resources: {report.total_resources}", ""]
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
            return "Pivot Table: Windows method not available (Excel not installed)"
        template_path = os.path.join(TEMPLATE_DIR, "pivot_template.xlsx")
        if os.path.exists(template_path):
            return f"Pivot Table: Created from template (will refresh when opened in Excel){mode_suffix}"
        return f"Pivot Table: Styled summary (template not found for real pivot){mode_suffix}"
        
    def _update_status(self, message: str):
        """Update status bar from background thread."""
        def update():
            self.status_var.set(message)
            self.last_output_path = None  # Clear clickable path for regular status updates
        self.root.after(0, update)
        
    def _show_results(self, text: str, report, output_path: str):
        """Show results in the text widget."""
        def update():
            self.results_text.delete("1.0", tk.END)
            if len(text) > 50000:
                self.results_text.insert("1.0", text[:50000] + "\n\n... (truncated for preview)")
            else:
                self.results_text.insert("1.0", text)
            if output_path:
                self.last_output_path = output_path  # Store for clicking
                self.status_var.set(f"✓ Report saved to: {output_path} (click to open)")
            else:
                self.last_output_path = None
                self.status_var.set(f"Generated report with {report.total_resources} resources")
        self.root.after(0, update)
    
    def _on_status_click(self, event):
        """Handle click on status bar to open the output file."""
        if self.last_output_path and os.path.exists(self.last_output_path):
            try:
                if sys.platform == "win32":
                    os.startfile(self.last_output_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", self.last_output_path], check=True)
                else:
                    subprocess.run(["xdg-open", self.last_output_path], check=True)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
    
    def _on_status_hover_enter(self, event):
        """Change cursor when hovering over clickable status."""
        if self.last_output_path:
            self.status_bar.configure(cursor="hand2")
    
    def _on_status_hover_leave(self, event):
        """Reset cursor when leaving status bar."""
        self.status_bar.configure(cursor="")
        
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
            self.back_btn.configure(state="normal")
        self.root.after(0, update)

    def _show_help(self):
        """Show quick help dialog."""
        help_text = f"""AWS End-of-Support Tool v{__version__} - Quick Help

WIZARD STEPS:

Step 1 - Data Source:
  • CSV File: Load from existing CSV (from AWS Command Center or fetch script)
  • Fetch from AWS: Connect directly to AWS and fetch resource inventory

Step 2 - Output Options:
  • Choose output format (HTML, Excel, Text, CSV, JSON)
  • Configure filters and options
  • Generate the report

AWS FETCH OPTIONS:
  • Profile: AWS CLI profile name (leave empty for default)
  • Regions: Comma-separated list or empty for all regions
  • Workers: Number of parallel fetch threads
  • Include Costs: Calculate extended support cost estimates

SERVICES FETCHED:
  Lambda, EKS, RDS, Aurora, DocumentDB, Neptune,
  ElastiCache, OpenSearch, MSK, Amazon MQ

OUTPUT FORMATS:
  • HTML: Interactive web report with charts & filters (recommended)
  • Excel: Professional report with pivot tables & timeline
  • Text: Human-readable console output
  • CSV: Flat table for spreadsheets
  • JSON: Structured data format

SUPPORT STATUS:
  🟢 Regular Support - No action needed
  🟡 Approaching EOS - Plan upgrades
  🔵 Extended Support Y1/Y2/Y3 - May incur costs
  🔴 Out of Support - Immediate action needed

COST ESTIMATES:
  • Costs marked with * (star) indicate future charges
    that will apply if the component is not upgraded
    before the End-of-Support date.
  • These costs are in addition to regular service pricing.

KEYBOARD SHORTCUTS:
  F1 - Show this help
"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - AWS End-of-Support Tool")
        help_window.geometry("500x500")
        help_window.transient(self.root)
        help_window.grab_set()
        
        frame = ttk.Frame(help_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(frame, wrap=tk.WORD, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget.insert("1.0", help_text)
        text_widget.configure(state="disabled")
        
        button_frame = ttk.Frame(help_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Open Detailed Guide", 
                  command=lambda: [help_window.destroy(), self._open_detailed_guide()]).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=help_window.destroy).pack(side=tk.LEFT, padx=5)
        
        help_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - help_window.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - help_window.winfo_height()) // 2
        help_window.geometry(f"+{x}+{y}")
    
    def _open_detailed_guide(self):
        """Open the detailed user guide."""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        html_guide_path = os.path.join(base_path, "docs", "USERGUIDE.html")
        
        if not os.path.exists(html_guide_path):
            alt_paths = [
                os.path.join(os.path.dirname(__file__), "..", "docs", "USERGUIDE.html"),
                os.path.join(os.getcwd(), "docs", "USERGUIDE.html"),
            ]
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    html_guide_path = os.path.abspath(alt_path)
                    break
        
        if os.path.exists(html_guide_path):
            try:
                webbrowser.open(f"file:///{html_guide_path}")
                return
            except Exception:
                pass
        
        messagebox.showwarning("User Guide Not Found", f"The user guide could not be found.\nSearched in: {base_path}")
        
    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


def main():
    """Entry point for GUI application."""
    app = EndOfSupportGUI()
    app.run()


if __name__ == "__main__":
    main()
