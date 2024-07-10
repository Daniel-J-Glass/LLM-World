from flask import Flask, render_template, request, jsonify
from src.game_structure import Game
from utils.llm_utils import initialize_client, update_chat_history
import base64
from io import BytesIO

app = Flask(__name__)

client = initialize_client()
game = Game(client)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form['user_input']
    response_stream = game.process_input(user_input)
    
    response = ""
    for chunk in response_stream:
        if chunk is None:
            break
        if isinstance(chunk, str):
            response += chunk
        elif isinstance(chunk, dict):
            if 'narrative' in chunk:
                response = chunk['narrative']
            game.update_game_state(chunk)
            break
    
    return jsonify({'response': response})

@app.route('/reset', methods=['POST'])
def reset():
    game.reset()
    return jsonify({'status': 'success'})

@app.route('/image')
def get_image():
    image = game.get_current_image()
    if image:
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return jsonify({'image': img_str})
    else:
        return jsonify({'image': None})

@app.route('/minimap')
def get_minimap():
    minimap_data = game.get_minimap_data()
    return jsonify(minimap_data)

@app.route('/chat_history')
def get_chat_history():
    return jsonify({'history': game.chat_history})

if __name__ == '__main__':
    app.run(debug=True)