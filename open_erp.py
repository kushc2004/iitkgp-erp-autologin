#!/usr/bin/env python3
"""Run the ERP auto-login from a source checkout.

Thin wrapper around the same code path as the installed ``erp-login``
command; the launcher scripts (open_erp.command / .sh / .bat) call this.
"""

from erplogin.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
