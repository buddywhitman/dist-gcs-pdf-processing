#!/usr/bin/env python3
"""
Final comprehensive linting fix script.
This will fix all remaining flake8 errors systematically.
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
    
    # Fix line length issues (E501) - break long lines
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
                else:
                    fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Fix blank line issues
    content = re.sub(r'\n\n\n+', '\n\n', content)  # Remove excessive blank lines
    content = re.sub(r'[ \t]+\n', '\n', content)  # Remove trailing whitespace
    
    # Fix import organization - move all imports to top
    lines = content.split('\n')
    import_lines = []
    other_lines = []
    in_imports = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(('import ', 'from ')) and not stripped.startswith('#'):
            import_lines.append(line)
            in_imports = True
        elif in_imports and (stripped == '' or stripped.startswith('#')):
            import_lines.append(line)
        else:
            if in_imports and stripped != '':
                in_imports = False
            other_lines.append(line)
    
    # Reorganize content
    if import_lines:
        content = '\n'.join(import_lines) + '\n\n' + '\n'.join(other_lines)
    
    # Fix specific patterns
    content = re.sub(r'except Exception as e:\s*\n\s*pass', 'except Exception:\n    pass', content)
    content = re.sub(r'except Exception as e:\s*\n\s*logger\.error', 'except Exception as e:\n    logger.error', content)
    
    # Fix f-string issues
    content = re.sub(r'print\("([^"]*\{[^}]*\}[^"]*)"\)', r'print(f"\1")', content)
    content = re.sub(r'logger\.info\("([^"]*\{[^}]*\}[^"]*)"\)', r'logger.info(f"\1")', content)
    content = re.sub(r'logger\.error\("([^"]*\{[^}]*\}[^"]*)"\)', r'logger.error(f"\1")', content)
    content = re.sub(r'logger\.warning\("([^"]*\{[^}]*\}[^"]*)"\)', r'logger.warning(f"\1")', content)
    content = re.sub(r'logger\.debug\("([^"]*\{[^}]*\}[^"]*)"\)', r'logger.debug(f"\1")', content)
    
    # Fix unused variable issues
    content = re.sub(r'except Exception as e:\s*\n\s*pass', 'except Exception:\n    pass', content)
    content = re.sub(r'except Exception as e:\s*\n\s*logger\.error', 'except Exception as e:\n    logger.error', content)
    
    # Fix indentation issues
    content = re.sub(r'except Exception as e:\s*\n\s*logger\.error', 'except Exception as e:\n    logger.error', content)
    
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
