
import re

def clean_app():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Helper to remove first occurrence of a function block including decorator
    # Pattern: @app.route(..)\n def funcname(..): ... until next @app.route
    
    def remove_function(func_name, text):
        # Regex to match the function and its decorator, up to the next decorator or end of file
        # We assume the old functions are earlier in the file, so sub(count=1) works.
        
        # This regex is tricky because of indentation and decorators.
        # Simpler approach: Locate the start, find the end (e.g. next @app.route), and cut.
        
        pattern = r'(@app\.route\([^\)]+\)\s+def ' + func_name + r'\([^)]*\):)'
        match = re.search(pattern, text)
        if not match:
            print(f"Function {func_name} not found.")
            return text
            
        start_idx = match.start()
        # Find next @app.route after this match
        next_route = re.search(r'@app\.route', text[start_idx + 1:])
        
        if next_route:
            end_idx = start_idx + 1 + next_route.start()
            # Backtrack to the previous newline to be clean
            slice_end = end_idx
            print(f"Removing {func_name} from {start_idx} to {slice_end}")
            return text[:start_idx] + text[slice_end:]
        else:
            # If no next route (unlikely for the first ones), assume end of file or look for something else?
            # But we know there are new functions later.
            print(f"Could not find end of {func_name}, skipping.")
            return text

    # Remove duplicates in order
    content = remove_function('get_conversations', content)
    content = remove_function('get_messages', content)
    # send_message is tricky because it might have a docstring or comments. The regex handles basic def.
    content = remove_function('send_message', content)
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Cleanup complete.")

if __name__ == "__main__":
    clean_app()
