import requests
import json
import time
import os
from PIL import Image, ImageFilter
import io
import cairosvg
import base64

import runwayml

from imgur_python import Imgur

from config import (IMAGE_GENERATION_MODEL, SD_KEY, SD_API_HOST, IMAGE_GENERATION_SEED, SVG_IMAGE_ENDPOINT, IMGUR_CLIENT_ID, IMGUR_CLIENT_SECRET,VIDEO_GENERATION_MODEL, VIDEO_GENERATION_KEY)


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

def upload_image_to_imgur(image_path):
    """Uploads an image to Imgur and returns the URL.

    Args:
        image_path (str): The path to the image file.

    Returns:
        str: The URL of the uploaded image.
    """
    client_id = IMGUR_CLIENT_ID
    headers = {"Authorization": f"Client-ID {client_id}"}
    url = "https://api.imgur.com/3/image"

    with open(image_path, "rb") as file:
        files = {"image": file}
        data = {
            "type": "file",
            "title": "Simple upload",
            "description": "This is a simple image upload in Imgur"
        }

        response = requests.post(url, headers=headers, files=files, data=data)
        
    if response.status_code == 200:
        data = response.json()
        image_url = data["data"]["link"]
        return image_url
    else:
        raise Exception(f"Failed to upload image: {response.text}")

def image_to_video(prompt_text, image_url, video_path):
    """Converts an image to a video.

    Args:
        image_path (str): The path to the image file.
        video_path (str): The path to save the video file.
    """
    prompt_text = prompt_text[0:510]

    print(f"Video Prompt: {prompt_text}")


    # The env var RUNWAYML_API_SECRET is expected to contain your API key.
    client = runwayml.RunwayML(api_key=VIDEO_GENERATION_KEY)

    try:
        task = client.image_to_video.create(
            model=VIDEO_GENERATION_MODEL,
            prompt_image=image_url,
            prompt_text=prompt_text,
            duration=5,
            ratio='16:9',
        )
    except runwayml.RateLimitError as e:
        raise requests.exceptions.RetryError("Rate limit exceeded")

    task_id = task.id
    # print(f"Task ID: {task_id}")
    failure_code = None
    # Wait for the task to complete
    while True:
        time.sleep(1)
        task = client.tasks.retrieve(id=task_id)
        status = task.status
        if status == 'PENDING':
            continue
        elif status == 'RUNNING':
            # print(f"Task {task_id} is running with progress {task.progress}")
            continue
        elif status == 'SUCCEEDED':
            output_urls = task.output
            # print(f"Task {task_id} succeeded with output URLs:")
            break
        elif status == 'FAILED':
            failure_reason = task.failure
            failure_code = task.failureCode
            print(failure_code)
            if failure_code == 429:
                raise requests.exceptions.RetryError("Rate limit exceeded")
            else:
                raise Exception(f"Task {task_id} failed with code {failure_code}: {failure_reason}")
    
        elif status == 'CANCELED':
            raise Exception(f"Task {task_id} was canceled")
        else:
            raise Exception(f"Unknown task status: {status}")

    # Download the generated video
    output_url = output_urls[0]
    response = requests.get(output_url)
    if response.status_code == 200:
        with open(video_path, 'wb') as f:
            f.write(response.content)
        print(f"Saved generated video as {video_path}")
    else:
        raise Exception(f"Failed to download video: {response.text}")


def generate_image(positive_prompt, negative_prompt):
    """takes in prompt and filename and saves generated image to filename

    Args:
        prompt (str): image generation prompt

    Returns:
        str: base64 image encoding or none
    """

    if "sd3.5" in IMAGE_GENERATION_MODEL:
        print(positive_prompt)
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
                "aspect_ratio": "16:9",
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

def generate_svg_image(positive_prompt, svg, negative_prompt=None, seed=0, output_format="png", svg_output_path="./temp_svg.png", kwargs={}):
    # Render SVG to PNG
    png_data = cairosvg.svg2png(bytestring=svg.encode('utf-8'), output_width=512, output_height=512)
    
    # Save the PNG data if svg_output_path is provided
    if svg_output_path:
        with open(svg_output_path, "wb") as f:
            f.write(png_data)
        print(f"Saved SVG-to-PNG image as {svg_output_path}")

    # Prepare the request
    url = f"{SD_API_HOST}{SVG_IMAGE_ENDPOINT}"
    headers = {
        "Authorization": f"Bearer {SD_KEY}",
        "Accept": "image/*"
    }
    
    files = {
        "image": ("image.png", png_data, "image/png")
    }
    
    data = {
        "prompt": positive_prompt,
        "output_format": output_format
    }
    data.update(kwargs)
    
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
    
    except Exception as e:
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
    
    # try:
    image_bytes = generate_svg_image(test_prompt, test_svg, svg_output_path="debug_svg_to_png.png")
    image = Image.open(io.BytesIO(image_bytes))

    # Save the generated image
    output_file = "./generated_image.png"
    with open(output_file, "wb") as f:
        f.write(image_bytes)
    print(f"Saved generated image as {output_file}")

    from os import path
    import requests
    import os
    from runwayml import RunwayML
    file = path.realpath(output_file)

    # upload image
    image_url = upload_image_to_imgur(file)
    print(f"Uploaded image to Imgur: {image_url}")

    # test video gen
    prompt_text = "A rose burning in a fire, resulting in a pile of ash"
    video_path = "./generated_video.mp4"
    image_to_video(prompt_text, image_url, video_path)
    print(f"Generated video from image: {video_path}")

    # except Exception as e:
    #     print(f"Error generating image: {str(e)}")
