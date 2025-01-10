import os
import subprocess
from flask import Flask, request, render_template_string
from openai import OpenAI
import requests


app = Flask(__name__)

# --------------------------------------------------------------------
# Read your API key from ~/api_key
# --------------------------------------------------------------------
with open(os.path.expanduser('./api_key'), 'r') as f:
    api_key = f.read().strip()
client = OpenAI(api_key=api_key)

# --------------------------------------------------------------------
# Combined HTML template with side-by-side layout
# --------------------------------------------------------------------
main_html = """
<!doctype html>
<html>
<head>
    <title>Code Generator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
            margin: 0;
            padding: 20px;
        }
        .container {
            display: flex;
            gap: 20px;
            max-width: 1600px;
            margin: 0 auto;
        }
        .input-section, .output-section {
            flex: 1;
            background-color: #fff;
            padding: 20px;
            border-radius: 5px;
        }
        textarea {
            width: 100%;
            height: 300px;
            font-size: 16px;
        }
        pre {
            background: #eeeeee;
            padding: 10px;
            overflow-x: auto;
            min-height: 300px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            margin-top: 10px;
            cursor: pointer;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="input-section">
            <h1>Enter Your Prompt</h1>
            <form method="post" action="/" id="promptForm">
                <textarea name="prompt" placeholder="Enter your instructions here..."></textarea><br>
                <button type="submit">Generate Code</button>
            </form>
        </div>
        <div class="output-section">
            <h1>Generated Code</h1>
            <pre>{{ code if code else "Generated code will appear here..." }}</pre>
        </div>
    </div>
    <script>
        document.getElementById('promptForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            document.querySelector('.output-section pre').textContent = result.code;
        };
    </script>
</body>
</html>
"""

# --------------------------------------------------------------------
# Route to handle both GET (show form) and POST (process prompt)
# --------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_prompt = request.form.get("prompt", "")

        # Generate code using the API
        api_response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": user_prompt + "\nPlease return only raw code without any formatting No docstrings, just raw code"
                }
            ],
            model="o1-mini"
        )
        generated_code = api_response.choices[0].message.content.lstrip('```')
        generated_code = generated_code.rstrip('```')

        # Save the code to a temporary .py file
        desktop_path = os.path.join(os.path.expanduser('~/desktop'), 'temp_generated_code.py')
        with open(desktop_path, 'w') as temp_file:
            temp_file.write(generated_code)

        # Execute the code in a new Terminal window (macOS only)
        applescript_command = f'''
        tell application "Terminal"
            activate
            do script "python3 '{desktop_path}'"
        end tell
        '''
        subprocess.run(["osascript", "-e", applescript_command])

        # Return JSON response for AJAX request
        return {"code": generated_code}

    # Initial page load
    return render_template_string(main_html, code="")

# --------------------------------------------------------------------
# Run the Flask server
# --------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=False)
