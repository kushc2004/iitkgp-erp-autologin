"""Automatic sign-in for the IIT KGP ERP portal."""

from .core import ErpLoginError, login

__all__ = ["ErpLoginError", "login"]
__version__ = "1.0.1"
