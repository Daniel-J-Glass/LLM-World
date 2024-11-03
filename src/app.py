from flask import Flask, render_template, request, jsonify
from src.game_structure import Game
from utils.llm_utils import initialize_client, update_chat_history
import base64
from io import BytesIO
import os

app = Flask(__name__)

game = Game()

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

@app.route('/video_status')
def get_video_status():
    if game.video_processing:
        return jsonify({
            'status': 'processing'
        })
    elif game.current_video and os.path.exists(game.current_video):
        with open(game.current_video, 'rb') as video_file:
            video_data = base64.b64encode(video_file.read()).decode()
        return jsonify({
            'status': 'ready',
            'video': video_data
        })
    else:
        return jsonify({
            'status': 'none'
        })

@app.route('/image')
def get_image():
    if game.video_processing:
        # Return current frame if video is being processed
        image = game.get_current_image()
        if image:
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return jsonify({
                'image': img_str,
                'video_processing': True
            })
    return jsonify({
        'image': None,
        'video_processing': game.video_processing
    })

@app.route('/minimap')
def get_minimap():
    minimap_data = game.get_minimap_data()
    return jsonify(minimap_data)

@app.route('/chat_history')
def get_chat_history():
    return jsonify({'history': game.chat_history})

@app.route('/compile_videos', methods=['POST'])
def compile_videos():
    compilation_path, message = game.compile_videos()
    if compilation_path:
        with open(compilation_path, 'rb') as video_file:
            video_data = base64.b64encode(video_file.read()).decode()
        return jsonify({
            'status': 'success',
            'video': video_data,
            'message': message
        })
    return jsonify({
        'status': 'error',
        'message': message
    })

if __name__ == '__main__':
    app.run(debug=True)