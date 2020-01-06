import upip

def install_dependencies():
    try:
        import logging
    except ImportError:
        upip.install("pycopy-logging") 

    print("pycopy-logging: ✓")