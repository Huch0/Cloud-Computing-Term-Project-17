from flask import Flask
from flask import send_from_directory
from flask import request
from werkzeug.utils import secure_filename
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
            user_image.save(app.static_folder +
                            '/uploads/' + secure_filename(user_image.filename))

            # detect_labels(app.static_folder + '/uploads/' +
            #               secure_filename(user_image.filename))
            response = detect_labels(app.static_folder + 'test_dog.jpg')

            # Delete the uploaded file
            # os.remove(app.static_folder + '/uploads/' +
            #           secure_filename(user_image.filename))

            # Return the most confident label and its confidence
            return response['Labels'][0]['Name'] + ' : ' + str(response['Labels'][0]['Confidence'])

        else:
            # Announce user that no file was uploaded
            return 'No file uploaded'


def detect_labels(photo):
    client = boto3.client('rekognition')

    with open(photo, 'rb') as image:
        # For using the default model
        response = client.detect_labels(Image={'Bytes': image.read()})

        # For using a custom model
        # We should use AWS Resource Access Manager (RAM) to share the model with the account that the server is using
        # Arn : Amazon Resource Name

        # response = client.detect_labels(Image={'Bytes': image.read()},
        #                                 ProjectVersionArn='arn:aws:rekognition:us-west-2:123456789012:project/version/your-model/1.0')

    print('Detected labels in ' + photo)
    for label in response['Labels']:
        print(label['Name'] + ' : ' + str(label['Confidence']))

    return response
