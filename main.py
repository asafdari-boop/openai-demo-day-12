import os
import subprocess
from flask import Flask, request, render_template_string, jsonify, make_response
import time
from openai import OpenAI
import requests
from pydantic import BaseModel

class Executeable(BaseModel):
    code: str
    file_type: str


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
            margin-right: 10px;
        }
        .hidden {
            display: none;
        }
        .execution-output {
            margin-top: 20px;
            background: #000;
            color: #fff;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
        }
        #codeEditor {
            width: 100%;
            height: 300px;
            font-family: monospace;
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
            <textarea id="codeEditor" name="code">{{ code if code else "Generated code will appear here..." }}</textarea>
            <input type="hidden" id="fileType" value="{{ file_type }}">
            <button onclick="executeCode()">Execute Modified Code</button>
            <h2>Execution Output</h2>
            <div class="execution-output">{{ output if output else "Program output will appear here..." }}</div>
        </div>
    </div>
    <script>
        document.getElementById('promptForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });
            const result = await response.json();
            document.querySelector('#codeEditor').value = result.code;
            document.querySelector('#fileType').value = result.file_type;
            document.querySelector('.execution-output').textContent = result.output;
        };

        async function executeCode() {
            const code = document.querySelector('#codeEditor').value;
            const fileType = document.querySelector('#fileType').value;

            const response = await fetch('/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    code: code,
                    file_type: fileType
                })
            });
            const result = await response.json();
            document.querySelector('.execution-output').textContent = result.output;
        }
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
        session_id = request.cookies.get('session_id')

        # Force new session ID if server has restarted
        server_start_time = getattr(app, 'start_time', None)
        if server_start_time or not session_id:
            session_id = str(int(time.time()))
            app.start_time = None

        # Load conversation history for current session
        history_file = os.path.join(os.path.dirname(__file__), 'temp', 'conversation_history.txt')
        messages = []

        print("session id", session_id)
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                all_history = f.read().strip().split('SESSION:')

                # Find current session's history
                current_session = None

                for session in all_history:
                    if session.startswith(f"{session_id}\n"):
                        current_session = session
                        break

                if current_session:
                    exchanges = current_session.split('---')
                    # Get last 3 exchanges from current session
                    for entry in exchanges[-3:]:
                        if entry:
                            parts = entry.strip().split('\n')
                            user_lines = []
                            assistant_lines = []
                            output_lines = []
                            current_section = None
                            for line in parts:
                                if line.startswith("User: "):
                                    current_section = "user"
                                    user_lines.append(line.replace("User: ", ""))
                                elif line.startswith("Assistant: "):
                                    current_section = "assistant"
                                    assistant_lines.append(line.replace("Assistant: ", ""))
                                elif line.startswith("Output: "):
                                    current_section = "output"
                                    output_lines.append(line.replace("Output: ", ""))
                                elif line and current_section:
                                    if current_section == "user":
                                        user_lines.append(line)
                                    elif current_section == "assistant":
                                        assistant_lines.append(line)
                                    elif current_section == "output":
                                        output_lines.append(line)
                            messages.append({"role": "user", "content": "\n".join(user_lines)})
                            messages.append({"role": "assistant", "content": "\n".join(assistant_lines)})
                            messages.append({"role": "assistant", "content": "\n".join(output_lines)})
                            print("Added messages:", messages[-2:])

        # Add current prompt at the end
        messages.append({
            "role": "user",
            "content": user_prompt + "\nPlease return only raw code without any formatting No docstrings, just raw code. The requests will require you to either write bash scripts or python script or both. You need to decide the better way to write the script. Complete all commands you are given by the user in the script you write, do not skip any instructions. You are operating on a MacOS for any bash scripts you write. Don't import libraries in any Python scripts you write!"
        })

        # Generate code using the API
        api_response = client.beta.chat.completions.parse(
            messages=messages,
            model="gpt-4o",
            response_format=Executeable
        )
        print("messages sent", messages)
        executeable = api_response.choices[0].message.parsed
        code = executeable.code
        file_type = executeable.file_type

        output = execute_code(code, file_type)

        # Save conversation to history under current session
        os.makedirs(os.path.dirname(history_file), exist_ok=True)

        # Check if this session exists in the file
        session_exists = False
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                content = f.read()
                session_exists = f"SESSION:{session_id}" in content

        with open(history_file, 'a') as f:
            if not os.path.getsize(history_file) or not session_exists:
                f.write(f"SESSION:{session_id}\n")
            f.write(f"User: {user_prompt}\n")
            f.write(f"Assistant: {code}\n")
            f.write(f"Output: {output}\n")
            f.write("---\n")

        # Create response with cookie
        response = make_response(jsonify({
            "code": code,
            "file_type": file_type,
            "output": output
        }))
        response.set_cookie('session_id', session_id, httponly=True, samesite='Strict')
        return response

    # Initial page load - set cookie if not present
    response = make_response(render_template_string(main_html, code="", output="", file_type=""))
    if not request.cookies.get('session_id'):
        response.set_cookie('session_id', str(int(time.time())), httponly=True, samesite='Strict')
    return response

@app.route("/execute", methods=["POST"])
def execute_modified():
    data = request.get_json()
    code = data.get("code")
    file_type = data.get("file_type")

    output = execute_code(code, file_type)
    return {"output": output}

def execute_code(code, file_type):
    # Generate appropriate file extension based on file type
    file_ext = '.py' if file_type == 'python' else '.sh'

    # Save the code to a temporary file with appropriate extension
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f'temp_generated_code{file_ext}')

    # Create or get persistent terminal session file
    terminal_session = os.path.join(temp_dir, 'terminal_session')
    if not os.path.exists(terminal_session):
        with open(terminal_session, 'w') as f:
            f.write('')

    with open(temp_file_path, 'w') as temp_file:
        temp_file.write(code)

    # Make shell scripts executable if needed
    if file_type == 'bash':
        os.chmod(temp_file_path, 0o755)

    # Execute the code in Terminal
    try:
        if file_type == 'python':
            run_command = ["python3", temp_file_path]
        else:
            run_command = ["bash", temp_file_path]

        # Modified AppleScript to create a new window
        terminal_command = f"""
        osascript -e '
            tell application "Terminal"
                activate
                do script ""  # This creates a new window
                set currentTab to selected tab of window 1
                set bounds of window 1 to {50, 50, 800, 600}

                # Show the contents of the file
                do script "echo \\"Contents of {temp_file_path}:\\" && cat {temp_file_path}" in currentTab
                delay 1

                # Execute the command
                do script "{' '.join(run_command)}" in currentTab
                delay 0.5
            end tell
        '"""
        subprocess.run(['bash', '-c', terminal_command])

        # Then run for web output
        process = subprocess.run(
            run_command,
            capture_output=True,
            text=True
        )

        # Combine stdout and stderr for complete output
        output = process.stdout
        if process.stderr:
            output += "\nErrors:\n" + process.stderr

        if not output.strip():
            output = "Command executed successfully with no output"

        # Append command and output to terminal session file
        with open(terminal_session, 'a') as f:
            f.write(f"\n$ {' '.join(run_command)}\n{output}\n")

    except Exception as e:
        output = f"Error executing program: {str(e)}"

    return output

# --------------------------------------------------------------------
# Run the Flask server
# --------------------------------------------------------------------
if __name__ == "__main__":
    app.start_time = str(int(time.time()))  # Add server start timestamp
    app.run(debug=False)
