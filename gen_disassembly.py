"""
Generate full disassembly for all 11 recovered modules.
"""
import importlib.machinery
import sys
import os
import types
import dis
import io

# === MOCKS (same as before) ===
class TrFunc:
    def __call__(self, *args, **kwargs):
        return args[0] if args else ''

gui_i18n = types.ModuleType('gui_i18n')
gui_i18n.tr = TrFunc()
sys.modules['gui_i18n'] = gui_i18n

gui_pkg = types.ModuleType('gui')
gui_gui18n = types.ModuleType('gui.gui_i18n')
gui_gui18n.tr = TrFunc()
sys.modules['gui'] = gui_pkg
sys.modules['gui.gui_i18n'] = gui_gui18n

import tkinter as real_tk
import tkinter.colorchooser as real_cc
import tkinter.filedialog as real_fd
import tkinter.messagebox as real_mb
import tkinter.scrolledtext as real_st
import tkinter.ttk as real_ttk
import tkinter.simpledialog as real_sd

tkinter_mod = types.ModuleType('tkinter')
for attr in dir(real_tk):
    if not attr.startswith('_'):
        setattr(tkinter_mod, attr, getattr(real_tk, attr))
tkinter_mod.colorchooser = real_cc
tkinter_mod.filedialog = real_fd
tkinter_mod.messagebox = real_mb
tkinter_mod.scrolledtext = real_st
tkinter_mod.ttk = real_ttk
tkinter_mod.simpledialog = real_sd

sys.modules['tkinter'] = tkinter_mod
sys.modules['tkinter.colorchooser'] = real_cc
sys.modules['tkinter.filedialog'] = real_fd
sys.modules['tkinter.messagebox'] = real_mb
sys.modules['tkinter.scrolledtext'] = real_st
sys.modules['tkinter.ttk'] = real_ttk
sys.modules['tkinter.simpledialog'] = real_sd

ttk_mod = types.ModuleType('ttkbootstrap')
ttk_constants = types.ModuleType('ttkbootstrap.constants')
for const_name in ['PRIMARY', 'SECONDARY', 'SUCCESS', 'DANGER', 'WARNING', 'INFO',
                    'LIGHT', 'DARK', 'LINK', 'WHITE', 'BLACK', 'HORIZONTAL', 'VERTICAL',
                    'END', 'LEFT', 'RIGHT', 'TOP', 'BOTTOM', 'BOTH', 'X', 'Y', 'NW', 'N', 'NE',
                    'EW', 'NS', 'NSEW', 'W', 'E', 'S', 'CENTER', 'TRUE', 'FALSE']:
    setattr(ttk_constants, const_name, const_name)
sys.modules['ttkbootstrap'] = ttk_mod
sys.modules['ttkbootstrap.constants'] = ttk_constants

for cls_name in ['Window', 'Dialog', 'Button', 'Label', 'Frame', 'Entry', 
                  'Text', 'Checkbutton', 'Combobox', 'Spinbox', 'Scale',
                  'Progressbar', 'Scrollbar', 'Separator', 'TreeView',
                  'Menubutton', 'Notebook', 'Radiobutton', 'Panedwindow',
                  'Labelframe', 'Sizegrip', 'OptionMenu', 'Slider',
                  'DateEntry', 'Floodgauge', 'Meter', 'Toast',
                  'CTkButton', 'CTkFrame', 'CTkLabel', 'CTkEntry',
                  'CTkComboBox', 'CTkCheckBox', 'CTkSwitch', 'CTkTextBox',
                  'CTkScrollableFrame', 'CTkTabView', 'CTkImage',
                  'CTkOptionMenu', 'CTkSegmentedButton', 'CTkProgressBar',
                  'CTkSlider', 'CTkFont', 'CTkToplevel']:
    setattr(ttk_mod, cls_name, type(cls_name, (), {}))
    setattr(ttk_constants, cls_name, type(cls_name, (), {}))

sys.modules['customtkinter'] = ttk_mod

for mod_name in ['gui.tabs', 'gui.dialogs', 'gui.utils', 'gui.widgets', 
                  'gui.theme_manager', 'gui.gui_dependencies',
                  'models', 'config', 'core', 'utils', 'services',
                  'gui.translation_manager', 'core.mod_manager',
                  'services.mod_service', 'utils.file_utils',
                  'utils.path_utils', 'utils.config', 'core.settings',
                  'services.update_checker', 'utils.platform_utils',
                  'core.logger', 'services.cache_service',
                  'core.project_manager', 'services.project_service',
                  'utils.mod_path_utils', 'core.i18n', 'services.i18n_service',
                  'gui.i18n', 'gui.i18n_manager']:
    if mod_name not in sys.modules:
        parts = mod_name.split('.')
        parent = None
        for i, part in enumerate(parts):
            full = '.'.join(parts[:i+1])
            if full not in sys.modules:
                m = types.ModuleType(full)
                sys.modules[full] = m
                if parent:
                    setattr(parent, part, m)
                parent = m

all_files = [
    (r'F:\Games\Rimprog\new_folder\gui\dialogs\__pycache__\about_dialog.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\dialogs\about_dialog_disassembly.txt'),
    (r'F:\Games\Rimprog\new_folder\gui\dialogs\__pycache__\shortcuts_dialog.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\dialogs\shortcuts_dialog_disassembly.txt'),
    (r'F:\Games\Rimprog\new_folder\gui\dialogs\__pycache__\history_dialog.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\dialogs\history_dialog_disassembly.txt'),
    (r'F:\Games\Rimprog\new_folder\gui\dialogs\__pycache__\documentation_dialog.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\dialogs\documentation_dialog_disassembly.txt'),
    (r'F:\Games\Rimprog\new_folder\gui\dialogs\__pycache__\debug_log_dialog.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\dialogs\debug_log_dialog_disassembly.txt'),
    (r'F:\Games\Rimprog\new_folder\gui\tabs\__pycache__\gui_tab_translation.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\tabs\gui_tab_translation_disassembly.txt'),
    (r'F:\Games\Rimprog\new_folder\gui\tabs\__pycache__\gui_tab_duplicates.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\tabs\gui_tab_duplicates_disassembly.txt'),
    (r'F:\Games\Rimprog\new_folder\gui\tabs\__pycache__\gui_mods_tab.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\tabs\gui_mods_tab_disassembly.txt'),
    (r'F:\Games\Rimprog\new_folder\gui\tabs\__pycache__\gui_filters_tab.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\tabs\gui_filters_tab_disassembly.txt'),
    (r'F:\Games\Rimprog\new_folder\gui\tabs\__pycache__\gui_tab_verification.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\tabs\gui_tab_verification_disassembly.txt'),
    (r'F:\Games\Rimprog\new_folder\gui\tabs\__pycache__\gui_tab_settings.cpython-314.pyc',
     r'F:\Games\Rimprog\new_folder\gui\tabs\gui_tab_settings_disassembly.txt'),
]

def full_disassemble_module(module):
    """Generate full disassembly of all code objects in a module."""
    lines = []
    
    # Module-level code object
    if hasattr(module, '__file__') and module.__file__:
        lines.append(f"# Module: {module.__name__}")
        lines.append(f"# File: {module.__file__}")
        lines.append("")
    
    # Module docstring
    if module.__doc__:
        lines.append(f'# Docstring: {module.__doc__}')
        lines.append("")
    
    # Module-level code object
    if hasattr(module, '__code__'):
        lines.append(f"\n# {'='*60}")
        lines.append(f"# MODULE-LEVEL CODE")
        lines.append(f"# {'='*60}")
        old = sys.stdout
        sys.stdout = io.StringIO()
        try:
            dis.dis(module.__code__)
        except Exception as e:
            lines.append(f"# Disassembly error: {e}")
        output = sys.stdout.getvalue()
        sys.stdout = old
        lines.append(output)
    
    # All top-level items
    for name in sorted(dir(module)):
        if name.startswith('__'):
            continue
        obj = getattr(module, name)
        
        if isinstance(obj, type):
            lines.append(f"\n# {'='*60}")
            lines.append(f"# CLASS: {name}")
            lines.append(f"# {'='*60}")
            if obj.__doc__:
                lines.append(f"# Docstring: {obj.__doc__}")
            lines.append(f"# Bases: {[b.__name__ for b in obj.__bases__ if b is not object]}")
            
            for mn in sorted(dir(obj)):
                if mn.startswith('__'):
                    continue
                method = getattr(obj, mn, None)
                if callable(method) and hasattr(method, '__code__'):
                    code = method.__code__
                    lines.append(f"\n# --- Method: {name}.{mn} ---")
                    lines.append(f"# File: {code.co_filename}, Line: {code.co_firstlineno}")
                    lines.append(f"# Args: {list(code.co_varnames[:code.co_argcount])}")
                    lines.append(f"# KW-only args: {list(code.co_varnames[code.co_argcount + code.co_posonlyargcount:code.co_argcount + code.co_posonlyargcount + code.co_kwonlyargcount])}")
                    lines.append(f"# All vars: {list(code.co_varnames)}")
                    lines.append(f"# Names: {list(code.co_names)}")
                    if code.co_consts:
                        str_consts = [c for c in code.co_consts if isinstance(c, str) and c]
                        if str_consts:
                            lines.append(f"# String constants: {str_consts[:15]}")
                    lines.append("")
                    
                    old = sys.stdout
                    sys.stdout = io.StringIO()
                    try:
                        dis.dis(code)
                    except Exception as e:
                        lines.append(f"# Disassembly error: {e}")
                    output = sys.stdout.getvalue()
                    sys.stdout = old
                    lines.append(output)
                    
                    # Nested code objects (comprehensions, lambdas, inner functions)
                    for const in code.co_consts:
                        if hasattr(const, 'co_code') and const.co_name not in ('<module>',):
                            lines.append(f"\n# ... Nested: {const.co_name}")
                            lines.append(f"# Vars: {list(const.co_varnames)}")
                            lines.append(f"# Names: {list(const.co_names)}")
                            old = sys.stdout
                            sys.stdout = io.StringIO()
                            try:
                                dis.dis(const)
                            except:
                                pass
                            nested_out = sys.stdout.getvalue()
                            sys.stdout = old
                            lines.append(nested_out)
        
        elif callable(obj) and hasattr(obj, '__code__'):
            code = obj.__code__
            lines.append(f"\n# {'='*60}")
            lines.append(f"# FUNCTION: {name}")
            lines.append(f"# {'='*60}")
            lines.append(f"# File: {code.co_filename}, Line: {code.co_firstlineno}")
            lines.append(f"# Args: {list(code.co_varnames[:code.co_argcount])}")
            lines.append(f"# All vars: {list(code.co_varnames)}")
            lines.append(f"# Names: {list(code.co_names)}")
            if code.co_consts:
                str_consts = [c for c in code.co_consts if isinstance(c, str) and c]
                if str_consts:
                    lines.append(f"# String constants: {str_consts[:15]}")
            lines.append("")
            
            old = sys.stdout
            sys.stdout = io.StringIO()
            try:
                dis.dis(code)
            except Exception as e:
                lines.append(f"# Disassembly error: {e}")
            output = sys.stdout.getvalue()
            sys.stdout = old
            lines.append(output)
    
    return '\n'.join(lines)

for pyc_path, dis_path in all_files:
    name = os.path.splitext(os.path.basename(pyc_path))[0].replace('.cpython-314', '')
    print(f"\nDisassembling: {name}...", flush=True)
    
    if name in sys.modules:
        del sys.modules[name]
    
    try:
        loader = importlib.machinery.SourcelessFileLoader(name, pyc_path)
        module = loader.load_module(name)
        
        dis_content = full_disassemble_module(module)
        with open(dis_path, 'w', encoding='utf-8') as f:
            f.write(dis_content)
        print(f"  Written: {dis_path} ({len(dis_content)} bytes)", flush=True)
    except Exception as e:
        print(f"  FAILED: {e}", flush=True)
        import traceback
        traceback.print_exc()

print("\nDone!")
