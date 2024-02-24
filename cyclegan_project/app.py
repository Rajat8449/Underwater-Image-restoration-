from flask import Flask, render_template, request, send_file
from PIL import Image
import numpy as np
from keras.models import model_from_json
import os
import io

app = Flask(__name__)

# Load your CycleGAN model
model_json_path = 'C:/Users/rashm/cyclegan_project/checkpoints/model_5502_.json'  # Replace with your actual path
model_h5_path = 'C:/Users/rashm/cyclegan_project/checkpoints/model_5502_.h5'  # Replace with your actual path

# Load the JSON file to get the model architecture
with open(model_json_path, 'r') as json_file:
    loaded_model_json = json_file.read()

# Load the model architecture from JSON
cycle_gan = model_from_json(loaded_model_json)

# Load the weights
cycle_gan.load_weights(model_h5_path)
def preprocess(x):
    # [0,255] -> [-1, 1]
    return x
    #(x / 127.5) - 1.0

def deprocess(x, np_uint8=True):
    # [-1,1] -> [0, 255]
  #  x = (x + 1.0) * 127.5
   # return np.uint8(x) if np_uint8 else x
    return x
def translate_image(input_image):
    # Resize and preprocess the input image
    input_image = Image.open(input_image).resize((256, 256))
    #input_image = np.array(input_image).astype(np.float32)
    input_image = preprocess(input_image)
    input_image = np.expand_dims(input_image, axis=0)

    # Translate the image using the CycleGAN model
    translated_image = cycle_gan.predict(input_image)[0]

    # Deprocess the translated image
    translated_image = deprocess(translated_image)[0]

    # Convert to uint8 before saving as JPEG
    translated_image = translated_image.astype(np.uint8)

    return translated_image

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    # Handle the image translation using your CycleGAN model here
    input_image = request.files['input_image']
    translated_image = translate_image(input_image)

    # Save the translated image temporarily
    translated_image_path = 'C:/Users/rashm/cyclegan_project/static/images/translated_image.jpg'
    Image.fromarray(translated_image).save(translated_image_path)

    # Pass the input and translated image paths to the result.html template
    input_image_path = 'static/images/input_image.jpg'
    Image.open(input_image).save(input_image_path)

    return render_template('result.html', input_image_url=input_image_path, translated_image_url=translated_image_path)

@app.route('/download_result')
def download_result():
    # Download the translated image
    translated_image_path = 'C:/Users/rashm/cyclegan_project/static/images/translated_image.jpg'
    return send_file(translated_image_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
