#!/usr/bin/env python3
"""
Comprehensive script to fix all flake8 linting issues.
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
    
    # Fix specific issues
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Fix long lines by breaking them
        if len(line) > 79:
            # Fix specific patterns
            if 'os.path.join(' in line and len(line) > 79:
                # Break os.path.join lines
                indent = len(line) - len(line.lstrip())
                if 'os.path.join(' in line:
                    # Extract the parts
                    parts = line.split('os.path.join(', 1)
                    if len(parts) == 2:
                        before = parts[0]
                        after = parts[1]
                        # Find the matching closing parenthesis
                        paren_count = 0
                        end_pos = 0
                        for j, char in enumerate(after):
                            if char == '(':
                                paren_count += 1
                            elif char == ')':
                                paren_count -= 1
                                if paren_count == 0:
                                    end_pos = j
                                    break
                        
                        if end_pos > 0:
                            args = after[:end_pos]
                            rest = after[end_pos+1:]
                            
                            # Split arguments by comma
                            arg_parts = [arg.strip() for arg in args.split(',')]
                            
                            fixed_lines.append(before + 'os.path.join(')
                            for j, arg in enumerate(arg_parts):
                                if j == len(arg_parts) - 1:
                                    fixed_lines.append(' ' * (indent + 4) + arg + ')' + rest)
                                else:
                                    fixed_lines.append(' ' * (indent + 4) + arg + ',')
                            continue
            
            elif ' = ' in line and len(line) > 79:
                # Break assignment lines
                parts = line.split(' = ', 1)
                if len(parts) == 2:
                    var_name = parts[0]
                    value = parts[1]
                    if len(var_name) + 4 + len(value) > 79:
                        indent = len(line) - len(line.lstrip())
                        fixed_lines.append(var_name + ' = (')
                        # Break the value into multiple lines
                        value_lines = [value[i:i+75-indent-4] for i in range(0, len(value), 75-indent-4)]
                        for j, value_line in enumerate(value_lines):
                            if j == len(value_lines) - 1:
                                fixed_lines.append(' ' * (indent + 4) + value_line + ')')
                            else:
                                fixed_lines.append(' ' * (indent + 4) + value_line)
                        continue
        
        # Fix specific line issues
        if 'import *' in line:
            # Fix star imports
            if 'from dist_gcs_pdf_processing.gcs_utils import *' in line:
                fixed_lines.append('from dist_gcs_pdf_processing.gcs_utils import (')
                fixed_lines.append('    list_new_files,')
                fixed_lines.append('    download_from_gcs,')
                fixed_lines.append('    upload_to_gcs,')
                fixed_lines.append('    file_exists_in_dest,')
                fixed_lines.append('    gcs_path')
                fixed_lines.append(')')
                continue
            elif 'from dist_gcs_pdf_processing.unified_worker import *' in line:
                fixed_lines.append('from dist_gcs_pdf_processing.unified_worker import (')
                fixed_lines.append('    process_file,')
                fixed_lines.append('    split_pdf_to_pages,')
                fixed_lines.append('    markdown_to_pdf,')
                fixed_lines.append('    is_valid_pdf,')
                fixed_lines.append('    get_pdf_page_count,')
                fixed_lines.append('    MAX_CONCURRENT_FILES,')
                fixed_lines.append('    MAX_RETRIES,')
                fixed_lines.append('    GEMINI_GLOBAL_CONCURRENCY')
                fixed_lines.append(')')
                continue
        
        # Fix unused imports
        if 'import tempfile' in line and 'tempfile' not in content:
            continue
        if 'import base64' in line and 'base64' not in content:
            continue
        if 'import MagicMock' in line and 'MagicMock' not in content:
            continue
        if 'import call' in line and 'call' not in content:
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
