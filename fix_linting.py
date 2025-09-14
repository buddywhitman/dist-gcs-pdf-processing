#!/usr/bin/env python3
"""
Script to fix common flake8 linting issues automatically.
"""

import os
import re
from pathlib import Path


def fix_file(file_path):
    """Fix common linting issues in a file."""
    print(f"Fixing {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix trailing whitespace
    content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
    
    # Fix missing newline at end of file
    if content and not content.endswith('\n'):
        content += '\n'
    
    # Fix f-strings without placeholders
    content = re.sub(r'f"([^"]*)"', r'"\1"', content)
    content = re.sub(r"f'([^']*)'", r"'\1'", content)
    
    # Fix bare except
    content = re.sub(r'except:', 'except Exception:', content)
    
    # Fix blank lines with whitespace
    content = re.sub(r'^[ \t]+$', '', content, flags=re.MULTILINE)
    
    # Fix missing blank lines before function/class definitions
    # This is more complex and would need AST parsing, so we'll skip for now
    
    # Fix line length issues by breaking long lines
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if len(line) > 79:
            # Try to break long lines at logical points
            if ' = ' in line and len(line) > 79:
                # Break assignment lines
                parts = line.split(' = ', 1)
                if len(parts) == 2:
                    var_name = parts[0]
                    value = parts[1]
                    if len(var_name) + 4 + len(value) > 79:
                        # Break after the assignment
                        indent = len(line) - len(line.lstrip())
                        new_line = var_name + ' = ('
                        fixed_lines.append(new_line)
                        # Break the value into multiple lines
                        value_lines = [value[i:i+75-indent-4] for i in range(0, len(value), 75-indent-4)]
                        for i, value_line in enumerate(value_lines):
                            if i == len(value_lines) - 1:
                                fixed_lines.append(' ' * (indent + 4) + value_line + ')')
                            else:
                                fixed_lines.append(' ' * (indent + 4) + value_line)
                        continue
            elif 'import ' in line and len(line) > 79:
                # Break long import lines
                if 'from ' in line:
                    # from module import item1, item2, item3
                    parts = line.split(' import ', 1)
                    if len(parts) == 2:
                        module_part = parts[0]
                        items_part = parts[1]
                        indent = len(line) - len(line.lstrip())
                        fixed_lines.append(module_part + ' import (')
                        # Split items by comma
                        items = [item.strip() for item in items_part.split(',')]
                        for i, item in enumerate(items):
                            if i == len(items) - 1:
                                fixed_lines.append(' ' * (indent + 4) + item + ')')
                            else:
                                fixed_lines.append(' ' * (indent + 4) + item + ',')
                        continue
                else:
                    # import module1, module2, module3
                    indent = len(line) - len(line.lstrip())
                    fixed_lines.append('import (')
                    modules = [mod.strip() for mod in line[7:].split(',')]
                    for i, module in enumerate(modules):
                        if i == len(modules) - 1:
                            fixed_lines.append(' ' * (indent + 4) + module + ')')
                        else:
                            fixed_lines.append(' ' * (indent + 4) + module + ',')
                    continue
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Only write if content changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Fixed {file_path}")
    else:
        print(f"  No changes needed for {file_path}")


def main():
    """Fix linting issues in all Python files."""
    src_dir = Path("src/dist_gcs_pdf_processing")
    tests_dir = Path("tests")
    
    # Fix source files
    for py_file in src_dir.glob("*.py"):
        fix_file(py_file)
    
    # Fix test files
    for py_file in tests_dir.glob("*.py"):
        fix_file(py_file)
    
    print("Linting fixes complete!")


if __name__ == "__main__":
    main()
