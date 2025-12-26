from flask import Flask, render_template
import sys
import os

# Set template folder to current directory
app = Flask(__name__, template_folder='.', static_folder='static')
app.config['SECRET_KEY'] = 'dev'

# Minimal mock for 'url_for' if needed, though Flask handles it.
# We need to make sure 'app.py' imports don't interface if we import it, 
# so we just define a fresh app accessing the same template.

def run_test():
    print("Starting render test for ihale.html...")
    with app.app_context():
        # Test Case 1: List View
        try:
            auctions = [
                {'id': 1, 'title': 'Test Motor', 'description': 'Desc', 'image_url': None, 'current_price': 10000}
            ]
            output_list = render_template('ihale.html', auctions_list=auctions, user_name='TestUser')
            print("Render List View: SUCCESS")
            
            # Check for unrendered Jinja tags
            if '{{' in output_list or '}}' in output_list:
                print("WARNING: Found double curly braces in List View output!")
                for i, line in enumerate(output_list.split('\n')):
                    if '{{' in line or '}}' in line:
                         print(f"Line {i+1}: {line.strip()}")
            
            if '{%' in output_list or '%}' in output_list:
                print("WARNING: Found Jinja block tags in List View output!")
                for i, line in enumerate(output_list.split('\n')):
                    if '{%' in line or '%}' in line:
                         print(f"Line {i+1}: {line.strip()}")
                         
        except Exception as e:
            print(f"Render List View: FAILED with error: {e}")

        # Test Case 2: Detail View
        try:
            output_detail = render_template('ihale.html', auction_id=1, user_name='TestUser')
            print("Render Detail View: SUCCESS")
            
            if '{{' in output_detail or '}}' in output_detail:
                print("WARNING: Found double curly braces in Detail View output!")
                for i, line in enumerate(output_detail.split('\n')):
                    if '{{' in line or '}}' in line:
                         print(f"Line {i+1}: {line.strip()}")
                         
            if '{%' in output_detail or '%}' in output_detail:
                print("WARNING: Found Jinja block tags in Detail View output!")
                for i, line in enumerate(output_detail.split('\n')):
                    if '{%' in line or '%}' in line:
                         print(f"Line {i+1}: {line.strip()}")

        except Exception as e:
             print(f"Render Detail View: FAILED with error: {e}")

if __name__ == '__main__':
    run_test()
