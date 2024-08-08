import requests
from PIL import Image
from io import BytesIO
import time
import datetime
from config import request_url
import fal_client
import os


file_path = ''

def close(e):
    print(f'Ошибка в процессе генерации фото: {e}')


def url_to_image(url, retries=3):
    try:
        for _ in range(retries):
            try:
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                img_data = BytesIO(response.content)
                img = Image.open(img_data)
                return img
            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}")
                time.sleep(2)  # Wait before retrying
            return 'Ошибка'
    except Exception as e:
        close(e)
        return


def request_to_ip(prompt):
    try:
        handler = fal_client.submit(
            request_url,
            arguments={
                "prompt": prompt
            },
        )
        result = handler.get()
        print(f"Request result: {result}")
        image_url = result['images'][0]['url']
        return image_url
    except Exception as e:
        close(e)
        return


def save_image(prompt):
    global file_path
    try:
        image_url = request_to_ip(prompt)
        image = url_to_image(image_url)
        if image == 'Ошибка':
            file_path = 'Ошибка'
        if not os.path.exists('data/images'):
            os.makedirs('data/images')
        file_path = f'data/images/{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.jpg'
        image.save(file_path)
        print(f"Image saved to {file_path}")
        return file_path
    except Exception as e:
        close(e)
        return