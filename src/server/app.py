from flask import Flask, send_from_directory, request, jsonify
import base64
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from urllib.parse import urljoin
import boto3

app = Flask(__name__, static_folder='./static')


@app.route("/")
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route("/upload", methods=['POST'])
def upload_image():
    if request.method == 'POST':
        user_image = request.files.get('user_image')
        ref_image = request.files.get('reference_image')
        if user_image and ref_image:
            user_response = recognize_celebrities(user_image)
            user_image.seek(0)  # Reset the file pointer to the beginning of the file
            compare_response = compare_faces(user_image, ref_image)

            if len(user_response['CelebrityFaces']) == 0:
                comparison_confidence = 0

                if 'FaceMatches' in compare_response and len(compare_response['FaceMatches']) > 0:
                    comparison_confidence = compare_response['FaceMatches'][0]['Similarity']

                return jsonify({
                    'found': False,
                    'comparison_confidence': comparison_confidence,
                    'message': "저희 데이터베이스에는 유사도가 높은 연예인이 존재하지 않습니다...\n\nRef 인물과 유사도는 아래와 같습니다!"
                })

            most_similar_celebrity = user_response['CelebrityFaces'][0]

            # Fetch the HTML content of the celebrity's Wikipedia page
            page_url = most_similar_celebrity['Urls'][0]
            if not page_url.startswith(('http://', 'https://')):
                page_url = 'https://' + page_url
            try:
                page_response = requests.get(page_url)
                soup = BeautifulSoup(page_response.text, 'html.parser')
                image_tag = soup.find('img')
                image_exist = 'alt' in image_tag.attrs

                if (image_exist):
                    comparison_confidence = 0
                    if 'FaceMatches' in compare_response and len(compare_response['FaceMatches']) > 0:
                        comparison_confidence = compare_response['FaceMatches'][0]['Similarity']

                    return jsonify({
                        'found': True,
                        'name': most_similar_celebrity['Name'],
                        'match_confidence': most_similar_celebrity['MatchConfidence'],
                        'comparison_confidence': comparison_confidence,
                        'info_url': most_similar_celebrity['Urls'][0],
                        'message': 'Celebrity found! But no image available'
                    })
                # print(f'image tag: {test}')
                if image_tag and 'src' in image_tag.attrs:
                    image_url = urljoin(page_url, image_tag['src'])
                    image_response = requests.get(image_url)
                    image_content = BytesIO(image_response.content)
                    image_data_url = 'data:image/jpeg;base64,' + base64.b64encode(image_content.read()).decode()

                    comparison_confidence = 0
                    if 'FaceMatches' in compare_response and len(compare_response['FaceMatches']) > 0:
                        comparison_confidence = compare_response['FaceMatches'][0]['Similarity']

                    return jsonify({
                        'found': True,
                        'name': most_similar_celebrity['Name'],
                        'match_confidence': most_similar_celebrity['MatchConfidence'],
                        'comparison_confidence': comparison_confidence,
                        'info_url': most_similar_celebrity['Urls'][0],
                        'image': image_data_url,
                        'message': ''
                    })
            except requests.exceptions.RequestException as e:
                return jsonify({'found': False, 'error': 'Error fetching page or image', 'details': str(e)})

        else:
            return jsonify({'error': 'Both user image and reference image are required'})


def recognize_celebrities(image):
    session = boto3.Session()
    client = session.client('rekognition')
    try:
        response = client.recognize_celebrities(
            Image={'Bytes': image.read()})
    except Exception as e:
        print(f"Error in Rekognition: {str(e)}")
        return {'CelebrityFaces': []}

    print(response)
    print()
    return response


def compare_faces(source_image, target_image):
    session = boto3.Session()
    client = session.client('rekognition')
    try:
        response = client.compare_faces(
            SourceImage={'Bytes': source_image.read()},
            TargetImage={'Bytes': target_image.read()},
            SimilarityThreshold=0
        )
    except Exception as e:
        print(f"Error in Rekognition: {str(e)}")
        return {'FaceMatches': []}
    print(response)
    return response


if __name__ == "__main__":
    app.run(debug=False)
