"""Wrapper script for PyInstaller bundling."""

if __name__ == "__main__":
    import sys
    import os

    # When running as PyInstaller bundle, add src to path
    if getattr(sys, 'frozen', False):
        # Running as bundle
        bundle_dir = sys._MEIPASS
        sys.path.insert(0, bundle_dir)
    else:
        # Running as script - add src directory
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

    # Now import and run main
    import src.main
