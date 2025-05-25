# src/__init__.py
"""Initialize the src package and fix Azure imports."""

# Fix Azure namespace package issue
try:
    import azure
    azure.__path__ = azure.__extend_path__(azure.__path__, azure.__name__)
except:
    pass

__version__ = "1.0.0"