
import os
import re

def fix_all_files():
    base_dir = r'c:\Users\HP\OneDrive\Masaüstü\moto'
    
    # List of files and their known broken patterns (regex or string)
    # We will use regex to find {{ ... \n ... }} and join them.
    
    files_to_scan = [
        'forum.html',
        'ihale.html',
        'ilan.html',
        'ilan_detay.html',
        'index.html',
        'mesajlarim.html'
    ]
    
    # Regex to find split tags: {{ followed by anything (non-greedy), newline, anything, closing }}
    # We want to match {{ [content] \n [content] }}
    # Pattern: \{\{(.*?)\n(.*?)\}\}  (simplified)
    # Actually, simpler: re.sub(r'\{\{\s*([^\}]+?)\s*\}\}', lambda m: f'{{{{ {m.group(1).replace(chr(10), " ").strip()} }}}}', content, flags=re.DOTALL)
    
    for fname in files_to_scan:
        path = os.path.join(base_dir, fname)
        if not os.path.exists(path):
            continue
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_len = len(content)
        
        # Function to clean whitespace inside {{ }} that spans newlines
        def fixer(match):
            # content inside the brackets
            inner = match.group(1)
            # Replace newlines with space and normalize spaces
            cleaned = re.sub(r'\s+', ' ', inner).strip()
            return f"{{{{ {cleaned} }}}}"

        # Match {{ content }} where content contains at least one newline
        # The regex: {{ (something with newline) }}
        # We use non-greedy matching for inner content
        new_content = re.sub(r'\{\{(?!\s*\}\})(.*?)\}\}', fixer, content, flags=re.DOTALL)
        
        # Also clean up cases where }} might be on a widely separated line if regex missed simple ones
        # But DOTALL should handle it.
        
        if len(new_content) != original_len or new_content != content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed {fname}")
        else:
            print(f"No changes in {fname}")

if __name__ == "__main__":
    fix_all_files()
