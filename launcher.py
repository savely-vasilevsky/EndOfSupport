#!/usr/bin/env python
"""Launcher script for PyInstaller executable.

This script handles imports properly when running as a frozen executable.
"""

import sys
import os

# When running as a PyInstaller bundle, add the bundle directory to path
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    bundle_dir = sys._MEIPASS
    sys.path.insert(0, bundle_dir)
else:
    # Running as script
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# Now import and run the GUI using absolute imports
# We need to import the modules directly since relative imports won't work
import importlib.util

def load_module(name, path):
    """Load a module from a specific path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

if __name__ == "__main__":
    # Determine the source directory
    if getattr(sys, 'frozen', False):
        src_dir = os.path.join(bundle_dir, 'src')
    else:
        src_dir = os.path.join(bundle_dir, 'src')
    
    # Load modules in dependency order
    models = load_module('models', os.path.join(src_dir, 'models.py'))
    parser = load_module('parser', os.path.join(src_dir, 'parser.py'))
    classifier = load_module('classifier', os.path.join(src_dir, 'classifier.py'))
    generator = load_module('generator', os.path.join(src_dir, 'generator.py'))
    formatters = load_module('formatters', os.path.join(src_dir, 'formatters.py'))
    
    # Now load and run GUI
    gui = load_module('gui', os.path.join(src_dir, 'gui.py'))
    gui.main()
