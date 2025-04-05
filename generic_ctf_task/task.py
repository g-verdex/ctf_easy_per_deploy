from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

# Get flag from environment variable
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Get flag from environment variable
FLAG = os.environ.get('FLAG', 'CTF{this_is_a_default_flag}')

# Store click count for each session
click_counts = {}

# HTML for the single-page application
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CTF Challenge - Click The Button</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            background-color: #1a1a1a;
            color: #33ff33;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        
        .container {
            text-align: center;
            background-color: #2a2a2a;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(51, 255, 51, 0.3);
            max-width: 600px;
            width: 90%;
        }
        
        h1 {
            margin-top: 0;
            color: #33ff33;
        }
        
        .button-container {
            margin: 30px 0;
        }
        
        #click-button {
            background-color: #33ff33;
            color: #1a1a1a;
            font-weight: bold;
            font-size: 18px;
            padding: 15px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        #click-button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 15px rgba(51, 255, 51, 0.6);
        }
        
        .message-area {
            min-height: 80px;
            margin: 20px 0;
        }
        
        .counter {
            font-size: 24px;
            font-weight: bold;
            margin: 20px 0;
        }
        
        .flag-container {
            background-color: #1a1a1a;
            padding: 15px;
            border-radius: 5px;
            display: none;
            word-break: break-all;
        }
        
        .reset-button {
            background-color: #ff3366;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>The Button Challenge</h1>
        <p>This challenge is simple. Just click the button three times to reveal the flag.</p>
        
        <div class="counter">
            Clicks: <span id="click-count">0</span>
        </div>
        
        <div class="button-container">
            <button id="click-button">CLICK ME</button>
        </div>
        
        <div class="message-area">
            <p id="message">Click the button to start...</p>
        </div>
        
        <div class="flag-container" id="flag-container">
            <p>Your flag: <span id="flag-value"></span></p>
        </div>
        
        <button class="reset-button" id="reset-button">Reset Counter</button>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const clickButton = document.getElementById('click-button');
            const resetButton = document.getElementById('reset-button');
            const clickCount = document.getElementById('click-count');
            const message = document.getElementById('message');
            const flagContainer = document.getElementById('flag-container');
            const flagValue = document.getElementById('flag-value');
            
            clickButton.addEventListener('click', function() {
                fetch('/click', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                })
                .then(response => response.json())
                .then(data => {
                    clickCount.textContent = data.clicks;
                    message.textContent = data.message;
                    
                    if (data.flag) {
                        flagValue.textContent = data.flag;
                        flagContainer.style.display = 'block';
                        clickButton.disabled = true;
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    message.textContent = 'An error occurred. Please try again.';
                });
            });
            
            resetButton.addEventListener('click', function() {
                fetch('/reset', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                })
                .then(response => response.json())
                .then(data => {
                    clickCount.textContent = data.clicks;
                    message.textContent = data.message;
                    flagContainer.style.display = 'none';
                    clickButton.disabled = false;
                })
                .catch(error => {
                    console.error('Error:', error);
                    message.textContent = 'An error occurred. Please try again.';
                });
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the single-page application"""
    return HTML

@app.route('/click', methods=['POST'])
def click():
    """Handle button clicks and reveal flag after 3 clicks"""
    # Get unique identifier for session (IP address in this simple example)
    session_id = request.remote_addr
    
    # Initialize click count if this is the first click
    if session_id not in click_counts:
        click_counts[session_id] = 0
    
    # Increment click count
    click_counts[session_id] += 1
    
    # Prepare response
    response = {
        'clicks': click_counts[session_id],
        'message': f"You've clicked {click_counts[session_id]} times!"
    }
    
    # If 3 clicks reached, reveal the flag
    if click_counts[session_id] >= 3:
        response['flag'] = FLAG
        response['message'] = "Congratulations! You've earned the flag!"
    
    return jsonify(response)

@app.route('/reset', methods=['POST'])
def reset():
    """Reset click counter for a session"""
    session_id = request.remote_addr
    click_counts[session_id] = 0
    return jsonify({'message': 'Counter reset successfully', 'clicks': 0})

@app.route('/hint')
def hint():
    """Provide a hint to users"""
    return jsonify({'hint': 'Keep clicking the button. Good things come to those who click!'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
