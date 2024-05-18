from flask import Flask, send_from_directory, request, jsonify
import base64
import requests
from bs4 import BeautifulSoup
from io import BytesIO

import boto3

app = Flask(__name__, static_folder='./static')


@app.route("/")
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route("/upload", methods=['POST'])
def upload_image():
    if request.method == 'POST':
        user_image = request.files['user_image']
        if user_image:
            response = recognize_celebrities(user_image)
            if len(response['CelebrityFaces']) == 0:
                response = {
                    'found': False,
                }
                return response

            most_similar_celebrity = response['CelebrityFaces'][0]
            print('most_similar_celebrity : ', most_similar_celebrity)

            # Fetch the HTML content of the Wikipedia page
            page_url = most_similar_celebrity['Urls'][0]
            if not page_url.startswith(('http://', 'https://')):
                page_url = 'https://' + page_url
            page_response = requests.get(page_url)

            # Parse the HTML to find the URL of the first image
            soup = BeautifulSoup(page_response.text, 'html.parser')
            image_tag = soup.find('img')
            image_url = 'https:' + image_tag['src']

            # Fetch the image from the URL
            image_response = requests.get(image_url)

            # Create a BytesIO object from the image content
            image_content = BytesIO(image_response.content)

            # Convert the image to a data URL
            image_data_url = 'data:image/jpeg;base64,' + base64.b64encode(image_content.read()).decode()

            # Create the JSON response
            response = {
                'found': True,
                'name': most_similar_celebrity['Name'],
                'match_confidence': most_similar_celebrity['MatchConfidence'],
                'info_url': most_similar_celebrity['Urls'][0],
                'image': image_data_url
            }

            return jsonify(response)

        else:
            # Announce user that no file was uploaded
            return 'No file uploaded'


def recognize_celebrities(image):

    client = boto3.client('rekognition')
    try:
        response = client.recognize_celebrities(
            Image={'Bytes': image.read()})
    except:
        response = {'CelebrityFaces': []}
        return response

    print(response)
    return response


def detect_labels(photo):
    client = boto3.client('rekognition')

    with open(photo, 'rb') as image:
        # For using the default model
        try:
            response = client.detect_labels(Image={'Bytes': image.read()})
        except:
            response = {'Labels': []}
            return response

        # For using a custom model
        # We should use AWS Resource Access Manager (RAM) to share the model with the account that the server is using
        # Arn : Amazon Resource Name

        # response = client.detect_labels(Image={'Bytes': image.read()},
        #                                 ProjectVersionArn='arn:aws:rekognition:us-west-2:123456789012:project/version/your-model/1.0')

    print('Detected labels in ' + photo)
    for label in response['Labels']:
        print(label['Name'] + ' : ' + str(label['Confidence']))

    return response
