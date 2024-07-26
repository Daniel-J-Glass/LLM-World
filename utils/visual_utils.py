import requests
import json
import time
import os
from PIL import Image
import io
import cairosvg
import base64

from config import (IMAGE_GENERATION_MODEL, SD_KEY, SD_API_HOST, IMAGE_GENERATION_SEED)


def send_async_generation_request(host, params, image_bytes=None):
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {SD_KEY}"
    }

    # Prepare files
    files = {}
    if image_bytes:
        files = {"image": ("image.png", image_bytes, "image/png")}

    # Send request
    print(f"Sending REST request to {host}...")
    response = requests.post(
        host,
        headers=headers,
        files=files,
        data=params
    )
    if not response.ok:
        raise Exception(f"HTTP {response.status_code}: {response.text}")

    # Process async response
    response_dict = json.loads(response.text)
    generation_id = response_dict.get("id", None)
    assert generation_id is not None, "Expected id in response"

    # Loop until result or timeout
    timeout = int(os.getenv("WORKER_TIMEOUT", 500))
    start = time.time()
    status_code = 202
    while status_code == 202:
        response = requests.get(
            f"{host}/result/{generation_id}",
            headers={
                **headers,
                "Accept": "image/*"
            },
        )

        if not response.ok:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        status_code = response.status_code
        time.sleep(10)
        if time.time() - start > timeout:
            raise Exception(f"Timeout after {timeout} seconds")

    return response

def generate_image(positive_prompt, negative_prompt):
    """takes in prompt and filename and saves generated image to filename

    Args:
        prompt (str): image generation prompt

    Returns:
        str: base64 image encoding or none
    """

    if "sd3" in IMAGE_GENERATION_MODEL:
        response = requests.post(
            f"{SD_API_HOST}/v2beta/stable-image/generate/core",
            headers={
                "authorization": f"Bearer {SD_KEY}",
                "accept": "image/*"
            },
            files={"none": ''},
            data={
                "prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "samples": 1,
                "aspect_ratio": "3:2",
                "output_format": "jpeg",
                "seed": IMAGE_GENERATION_SEED,
                "model": {IMAGE_GENERATION_MODEL},
            },
        )

        if response.status_code == 200:
            return response.content
        else:
            raise Exception(str(response.json()))
        
    elif "sd2" in IMAGE_GENERATION_MODEL:
        raise NotImplementedError
        engine_id = "stable-diffusion-v1-6"
        api_host = SD_API_HOST
        response = requests.post(
            f"{api_host}/v1/generation/{engine_id}/text-to-image",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {SD_KEY}"
            },
            json={
                "text_prompts": [
                    {
                        "text": prompt
                    }
                ],
                "cfg_scale": 7,
                "height": 640,
                "width": 448,
                "samples": 1,
                "steps": 20,
            },
        )

        if response.status_code != 200:
            raise Exception("Non-200 response: " + str(response.text))

        data = response.json()

        return [image["base64"] for image in data["artifacts"]][0]

    return None

def generate_svg_image(positive_prompt, svg, negative_prompt=None, control_strength=0.7, seed=0, output_format="png"):
    # Render SVG to PNG
    png_data = cairosvg.svg2png(bytestring=svg.encode('utf-8'))
    
    # Prepare the request
    url = f"{SD_API_HOST}/v2beta/stable-image/control/sketch"
    headers = {
        "Authorization": f"Bearer {SD_KEY}",
        "Accept": "image/*"
    }
    
    files = {
        "image": ("image.png", png_data, "image/png")
    }
    
    data = {
        "prompt": positive_prompt,
        "control_strength": control_strength,
        "output_format": output_format
    }
    
    if negative_prompt:
        data["negative_prompt"] = negative_prompt
    
    if seed != 0:
        data["seed"] = seed

    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"API request failed with status code {response.status_code}: {response.text}")
    
    except requests.RequestException as e:
        print("Failed SVG image generation")
        raise Exception(f"API request failed: {str(e)}")

if __name__ == "__main__":
    # Test the generate_svg_image function
    test_svg = '''
    <svg width="100" height="100">
        <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
    </svg>
    '''
    test_prompt = "A red circle transformed into a beautiful rose"
    
    try:
        image_bytes = generate_svg_image(test_prompt, test_svg)
        image = Image.open(io.BytesIO(image_bytes))
        image.show()
        
        # Save the generated image
        output_file = "generated_image.png"
        with open(output_file, "wb") as f:
            f.write(image_bytes)
        print(f"Saved generated image as {output_file}")
    except Exception as e:
        print(f"Error generating image: {str(e)}")

