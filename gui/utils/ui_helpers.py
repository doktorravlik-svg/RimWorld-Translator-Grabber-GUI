# gui/utils/ui_helpers.py
"""
UI Helper functions for common GUI operations.

Provides reusable utilities for window positioning, styling, and other
common GUI tasks to eliminate code duplication.
"""


def center_window(window, parent, width: int, height: int) -> None:
    """
    Safely centers a child window relative to its parent.

    Args:
        window: The child window (Toplevel) to center
        parent: The parent window to center relative to
        width: Width of the child window
        height: Height of the child window

    Example:
        center_window(dialog, parent, 600, 400)
    """
    window.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def safe_configure(style, style_name: str, **kwargs) -> bool:
    """
    Safely configures a ttk style with error handling.

    Catches TclError exceptions that may occur when invalid colors
    or fonts are provided in user configuration.

    Args:
        style: ttk.Style instance
        style_name: Name of the style to configure
        **kwargs: Configuration options (background, foreground, etc.)

    Returns:
        True if configuration succeeded, False otherwise

    Example:
        safe_configure(style, "TButton", background="#22c55e", foreground="white")
    """
    try:
        style.configure(style_name, **kwargs)
        return True
    except Exception:
        # Invalid color/font - silently use system defaults
        return False