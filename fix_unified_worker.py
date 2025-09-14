#!/usr/bin/env python3
"""
Fix specific linting issues in unified_worker.py
"""

import re


def fix_unified_worker():
    """Fix the unified_worker.py file."""
    file_path = "src/dist_gcs_pdf_processing/unified_worker.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
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
    
    # Fix specific line length issues
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if len(line) > 79:
            # Fix specific long lines
            if 'TimedRotatingFileHandler(log_file_path, when="midnight", backupCount=20' in line:
                # Break the TimedRotatingFileHandler line
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + 'TimedRotatingFileHandler(')
                fixed_lines.append(' ' * (indent + 4) + 'log_file_path, when="midnight", backupCount=200)')
                continue
            elif 'file_handler.setFormatter(logging.Formatter(' in line:
                # Break the setFormatter line
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + 'file_handler.setFormatter(')
                fixed_lines.append(' ' * (indent + 4) + 'logging.Formatter(')
                fixed_lines.append(' ' * (indent + 8) + "'%(asctime)s %(levelname)s %(message)s'))")
                continue
            elif 'stream_handler.setFormatter(logging.Formatter(' in line:
                # Break the stream_handler setFormatter line
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + 'stream_handler.setFormatter(')
                fixed_lines.append(' ' * (indent + 4) + 'logging.Formatter(')
                fixed_lines.append(' ' * (indent + 8) + "'%(asctime)s %(levelname)s %(message)s'))")
                continue
            elif 'logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])' in line:
                # Break the basicConfig line
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + 'logging.basicConfig(')
                fixed_lines.append(' ' * (indent + 4) + 'level=logging.INFO,')
                fixed_lines.append(' ' * (indent + 4) + 'handlers=[file_handler, stream_handler])')
                continue
            elif 'from concurrent.futures import (' in line:
                # Break the import line
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + 'from concurrent.futures import (')
                fixed_lines.append(' ' * (indent + 4) + 'ThreadPoolExecutor,')
                fixed_lines.append(' ' * (indent + 4) + 'as_completed,')
                fixed_lines.append(' ' * (indent + 4) + 'wait,')
                fixed_lines.append(' ' * (indent + 4) + 'FIRST_COMPLETED)')
                continue
            elif 'from .config import (' in line:
                # Break the config import line
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + 'from .config import (')
                fixed_lines.append(' ' * (indent + 4) + 'POLL_INTERVAL,')
                fixed_lines.append(' ' * (indent + 4) + 'STAGING_DIR,')
                fixed_lines.append(' ' * (indent + 4) + 'PROCESSED_DIR,')
                fixed_lines.append(' ' * (indent + 4) + 'PAGE_MAX_WORKERS,')
                fixed_lines.append(' ' * (indent + 4) + 'MAX_CONCURRENT_FILES,')
                fixed_lines.append(' ' * (indent + 4) + 'MAX_CONCURRENT_WORKERS,')
                fixed_lines.append(' ' * (indent + 4) + 'GEMINI_GLOBAL_CONCURRENCY)')
                continue
            else:
                # Generic line breaking for other long lines
                if ' = ' in line and len(line) > 79:
                    parts = line.split(' = ', 1)
                    if len(parts) == 2:
                        var_name = parts[0]
                        value = parts[1]
                        if len(var_name) + 4 + len(value) > 79:
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
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed unified_worker.py")


if __name__ == "__main__":
    fix_unified_worker()
