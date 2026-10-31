"""Compatibility entry point: dashboard tests now run against an isolated DB/server.

The former test depended on the removed alert dropdown and wrote to the demo DB.
stage14 covers the redesigned UI, real prediction, SHAP/LIME, CSV and PCAP.
"""
from stage14_test_dashboard_redesign import main

if __name__ == "__main__":
    main()
