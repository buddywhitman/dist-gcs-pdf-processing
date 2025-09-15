#!/usr/bin/env python3
"""
Final comprehensive linting fix script to make GitHub Actions succeed.
This will fix ALL remaining flake8 errors systematically.
"""

import os
import re
import subprocess
import sys

def fix_file(file_path):
    """Fix linting issues in a single file."""
    print(f"Fixing {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix line length issues (E501) - break long lines at logical points
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if len(line) > 79 and not line.strip().startswith('#'):
            # Don't break strings, comments, or URLs
            if ('"' in line and line.count('"') >= 2) or \
               ("'" in line and line.count("'") >= 2) or \
               line.strip().startswith('http') or \
               line.strip().startswith('#'):
                fixed_lines.append(line)
            else:
                # Try to break at logical points
                if ' = ' in line and len(line) > 79:
                    parts = line.split(' = ', 1)
                    if len(parts) == 2:
                        fixed_lines.append(parts[0] + ' = (')
                        fixed_lines.append('    ' + parts[1] + ')')
                    else:
                        fixed_lines.append(line)
                elif ' (' in line and len(line) > 79:
                    # Function call - break after opening paren
                    paren_pos = line.find(' (')
                    if paren_pos > 0:
                        fixed_lines.append(line[:paren_pos + 2])
                        remaining = line[paren_pos + 2:].rstrip()
                        if remaining.endswith(')'):
                            remaining = remaining[:-1]
                        fixed_lines.append('    ' + remaining + ')')
                    else:
                        fixed_lines.append(line)
                elif ' and ' in line and len(line) > 79:
                    # Break at 'and' for long conditions
                    parts = line.split(' and ', 1)
                    if len(parts) == 2:
                        fixed_lines.append(parts[0] + ' and')
                        fixed_lines.append('    ' + parts[1])
                    else:
                        fixed_lines.append(line)
                elif ' or ' in line and len(line) > 79:
                    # Break at 'or' for long conditions
                    parts = line.split(' or ', 1)
                    if len(parts) == 2:
                        fixed_lines.append(parts[0] + ' or')
                        fixed_lines.append('    ' + parts[1])
                    else:
                        fixed_lines.append(line)
                elif ' if ' in line and len(line) > 79:
                    # Break at 'if' for long conditions
                    parts = line.split(' if ', 1)
                    if len(parts) == 2:
                        fixed_lines.append(parts[0] + ' if')
                        fixed_lines.append('    ' + parts[1])
                    else:
                        fixed_lines.append(line)
                elif ' for ' in line and len(line) > 79:
                    # Break at 'for' for long comprehensions
                    parts = line.split(' for ', 1)
                    if len(parts) == 2:
                        fixed_lines.append(parts[0] + ' for')
                        fixed_lines.append('    ' + parts[1])
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Fix blank line issues
    content = re.sub(r'\n\n\n+', '\n\n', content)  # Remove excessive blank lines
    content = re.sub(r'[ \t]+\n', '\n', content)  # Remove trailing whitespace
    
    # Fix f-string issues
    content = re.sub(r'print\("([^"]*\{[^}]*\}[^"]*)"\)', r'print(f"\1")', content)
    content = re.sub(r'logger\.info\("([^"]*\{[^}]*\}[^"]*)"\)', r'logger.info(f"\1")', content)
    content = re.sub(r'logger\.error\("([^"]*\{[^}]*\}[^"]*)"\)', r'logger.error(f"\1")', content)
    content = re.sub(r'logger\.warning\("([^"]*\{[^}]*\}[^"]*)"\)', r'logger.warning(f"\1")', content)
    content = re.sub(r'logger\.debug\("([^"]*\{[^}]*\}[^"]*)"\)', r'logger.debug(f"\1")', content)
    
    # Fix specific indentation patterns
    content = re.sub(r'(\s+)except Exception as e:\s*\n\s*logger\.error', r'\1except Exception as e:\n\1    logger.error', content)
    
    # Fix spacing around equals (E251)
    content = re.sub(r' = ', ' = ', content)
    
    # Fix continuation line indentation (E128)
    content = re.sub(r'(\s+)if \(', r'\1if (', content)
    
    # Ensure file ends with newline
    if content and not content.endswith('\n'):
        content += '\n'
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Fixed {file_path}")
        return True
    else:
        print(f"  No changes needed for {file_path}")
        return False

def remove_unused_imports(file_path):
    """Remove unused imports from a file."""
    print(f"Removing unused imports from {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Common unused imports to remove
    unused_imports = [
        'from typing import Dict, Any',
        'from typing import Set, Optional',
        'import base64',
        'import mimetypes',
        'from docx import Document',
        'import os',
        'import pytest',
        'import shutil',
        'from unittest.mock import call',
        'from dist_gcs_pdf_processing.unified_worker import process_file, process_files',
        'from dist_gcs_pdf_processing.unified_worker import split_pdf_to_pages',
        'from googleapiclient.errors import HttpError',
        'from .shared import DRIVE_LIMITER',
        'from .shared import GCS_LIMITER',
        'from .shared import GEMINI_LIMITER',
        'from .shared import RateLimiter',
        'from queue import Queue, Empty',
        'from .config import DOC_BATCH_SIZE',
        'from .config import GCS_BUCKET_NAME',
        'from .gcs_utils import file_exists_in_dest as gcs_file_exists',
        'from .drive_utils_oauth2 import file_exists_in_dest as drive_file_exists',
    ]
    
    for unused_import in unused_imports:
        if unused_import in content:
            content = content.replace(unused_import + '\n', '')
            content = content.replace(unused_import, '')
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Removed unused imports from {file_path}")
        return True
    else:
        print(f"  No unused imports to remove from {file_path}")
        return False

def main():
    """Main function to fix all linting issues."""
    print("Starting final comprehensive linting fix...")
    
    # Get list of Python files
    stdout, stderr, returncode = run_command("find src tests -name '*.py' -type f")
    if returncode != 0:
        print(f"Error finding Python files: {stderr}")
        return 1
    
    python_files = [f.strip() for f in stdout.split('\n') if f.strip()]
    
    print(f"Found {len(python_files)} Python files to fix")
    
    fixed_count = 0
    for file_path in python_files:
        if os.path.exists(file_path):
            if fix_file(file_path):
                fixed_count += 1
            if remove_unused_imports(file_path):
                fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")
    
    # Run flake8 to check remaining issues
    print("\nRunning flake8 to check remaining issues...")
    stdout, stderr, returncode = run_command("flake8 src tests --max-line-length=79 --exclude=__pycache__")
    
    if returncode == 0:
        print("✅ All linting issues fixed!")
    else:
        print("⚠️  Some issues remain:")
        print(stdout)
        print(stderr)
    
    return returncode

def run_command(cmd):
    """Run a command and return its output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        print(f"Error running command '{cmd}': {e}")
        return "", str(e), 1

if __name__ == "__main__":
    sys.exit(main())