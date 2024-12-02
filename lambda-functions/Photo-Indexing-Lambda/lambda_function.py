import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection

# from requests_aws4auth import AWS4Auth

def lambda_handler(event, context):
    print("LF1 Triggered Again!!!")

    bucket = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']
    eventTime = event["Records"][0]["eventTime"]

    # Initialize Rekognition client
    rekognition = boto3.client('rekognition')
    
    # Detect labels
    response = rekognition.detect_labels(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': object_key
            }
        },
        MaxLabels=10,
        MinConfidence=70
    )
    
    # Extract labels from the response
    labels = [label['Name'].lower() for label in response['Labels']]

    # Initialize S3 client
    s3 = boto3.client('s3')
    
    # Retrieve object metadata
    metadata = s3.head_object(Bucket=bucket, Key=object_key)
    
    # Extract custom labels if present
    custom_labels = []
    if 'customlabels' in metadata['Metadata']:
        custom_labels += [label.strip() for label in metadata['Metadata']['customlabels'].split(',')]
    
    # Combine detected and custom labels
    all_labels = list(set(labels + custom_labels))

    photo_details = {
        "objectKey" : object_key,
        "bucket" : bucket,
        "createdTimestamp" : eventTime,
        "labels" : all_labels
    }
    print(photo_details)
    
    index_to_opensearch(photo_details)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

def get_secret():
    secret_name = "Opensearch_secrets"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = json.loads(get_secret_value_response['SecretString'])
    return (secret['user'],secret['password'])

def index_to_opensearch(photo_details):
    region = 'us-east-1'  # e.g., us-west-1
    service = 'es'
    # credentials = boto3.Session().get_credentials()
    # awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    host = 'search-photosearch-c7jjw3m3xugrq2sfm3r6jpdoju.aos.us-east-1.on.aws'  # Replace with your OpenSearch domain endpoint
    index_name = 'photos'
    auth = get_secret()
    opensearch = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = auth,
        use_ssl = True,
        verify_certs = True,
        ssl_assert_hostname=False,
        ssl_show_warn=False
    )

    response = opensearch.index(
        index = index_name,
        body = photo_details,
        id = photo_details['objectKey'],
        refresh = True
    )

    print(f"OpenSearch indexing response: {response}")