import re

def check_brackets(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Simple check for simple mismatched brackets in script tags
    # This is a heuristic, not a full parser
    script_blocks = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
    
    print(f"Found {len(script_blocks)} script blocks.")
    
    for i, block in enumerate(script_blocks):
        # Remove comments to avoid false positives
        clean_block = re.sub(r'//.*', '', block)
        clean_block = re.sub(r'/\*.*?\*/', '', clean_block, flags=re.DOTALL)
        
        open_braces = clean_block.count('{')
        close_braces = clean_block.count('}')
        open_parens = clean_block.count('(')
        close_parens = clean_block.count(')')
        
        if open_braces != close_braces:
            print(f"Script Block {i+1}: Mismatched braces {{}} -> Open: {open_braces}, Closed: {close_braces}")
            # Try to find context
            lines = block.split('\n')
            balance = 0
            for ln, line in enumerate(lines):
                 balance += line.count('{') - line.count('}')
                 if balance < 0:
                      print(f"  first likely extra closing brace at line {ln}: {line.strip()}")
                      break
            if balance > 0:
                 print(f"  Script block ends with {balance} unclosed braces.")

        if open_parens != close_parens:
            print(f"Script Block {i+1}: Mismatched parens () -> Open: {open_parens}, Closed: {close_parens}")

def check_tags(file_path):
    # Very basic tag balancer for common container tags
    # Ignores void tags and typical self-closing tags
    
    void_tags = {'meta', 'link', 'img', 'input', 'br', 'hr', 'source', 'area', 'base', 'col', 'embed', 'track', 'wbr'}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    stack = []
    
    # Simple regex for tags
    tag_re = re.compile(r'<\s*(/?)\s*([a-zA-Z0-9-]+)([^>]*)>')
    
    msg_limit = 10
    msg_count = 0
    
    for line_num, line in enumerate(lines, 1):
        # Remove Jinja comments and blocks roughly to avoid confusion
        line_clean = re.sub(r'{#.*?#}', '', line)
        line_clean = re.sub(r'{%.*?%}', '', line_clean) # Very aggressive, might eat attributes but ok for structure check
        
        matches = tag_re.finditer(line_clean)
        
        for match in matches:
            slash = match.group(1)
            tag_name = match.group(2).lower()
            attrs = match.group(3)
            
            if tag_name in void_tags:
                continue
            
            # Skip doctype and comments
            if tag_name.startswith('!'):
                continue
                
            if not slash:
                # Open tag
                stack.append((tag_name, line_num))
            else:
                # Close tag
                if not stack:
                    print(f"Error: Unexpected closing tag </{tag_name}> at line {line_num}")
                    msg_count += 1
                else:
                    last_tag, last_line = stack.pop()
                    if last_tag != tag_name:
                        print(f"Error: Mismatched tag. Expected </{last_tag}> (from line {last_line}), found </{tag_name}> at line {line_num}")
                        stack.append((last_tag, last_line)) # Put it back to assume missing close rather than wrong close
                        msg_count += 1
            
            if msg_count >= msg_limit:
                print("Too many errors, stopping tag check.")
                return

    if stack:
        print(f"Error: Unclosed tags remaining: {stack[:5]}...")

if __name__ == "__main__":
    print("Checking brackets in scripts...")
    check_brackets('ihale.html')
    print("\nChecking HTML tags...")
    check_tags('ihale.html')
