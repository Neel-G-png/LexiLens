import os
import logging
import json
import uuid
import boto3
from opensearchpy import OpenSearch
from botocore.exceptions import ClientError
import re

# logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)

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

def get_os_client():
    host = 'search-photosearch-c7jjw3m3xugrq2sfm3r6jpdoju.aos.us-east-1.on.aws'
    port = 443
    auth = get_secret()
    try:
        client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=auth, 
            use_ssl=True,
            verify_certs=True,
            ssl_assert_hostname=False,
            ssl_show_warn=False
        )
        return client
    except Exception as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        return e

def get_photo_url(matching_photos):
    matching_photos_url = []
    for image_data in matching_photos:
        img_path = 'https://s3.amazonaws.com/' + image_data['bucket'] + '/' + image_data['objectKey']
        matching_photos_url.append(img_path)
    return matching_photos_url

def query_photos(slots, os_client, index_name = "photos"):
    try:
        tags = [slots[tag].lower() for tag in slots]
        if not tags:
            raise ValueError("Tags list cannot be empty.")
        query = {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"labels": tag}} for tag in tags
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        # Execute the search
        response = os_client.search(
            index=index_name,
            body=query
        )
        # Extract the hits
        print("############################ This OS response : ", response)
        hits = response['hits']['hits']
        matching_photos = [hit['_source'] for hit in hits]
        matching_photos_url = get_photo_url(matching_photos)
        return matching_photos_url, False
    except Exception as e:
        return [e], True

def format_slots(unformatted_slots):
    return {tag:unformatted_slots[tag]['value']['originalValue'] for tag in unformatted_slots if unformatted_slots[tag]}

def get_lex_reply(session_id, user_input):
    client = boto3.client('lexv2-runtime')
    
    # Set your Lex V2 bot details
    bot_id = 'SMKL2ABKNV'
    bot_alias_id = 'TSTALIASID'
    locale_id = 'en_US'  # Adjust if using a different locale
    
    try:
        # Call the Lex V2 bot
        response = client.recognize_text(
            botId=bot_id,
            botAliasId=bot_alias_id,
            localeId=locale_id,
            sessionId=session_id,  # Use dynamic session ID
            text=user_input
        )
        print("#############################\nResponse from lex - ", json.dumps(response), "#############################")
        # Extract the bot's response
        unformatted_slots = response['interpretations'][0]['intent']['slots']
        formatted_slots = format_slots(unformatted_slots)
        return {
            'statusCode': 200,
            'body': json.dumps(formatted_slots)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def lambda_handler(event, context):
    print("#############\n Triggering Event - ", event, "#############\n")
    session_id = str(uuid.uuid4())
    query_params = event.get("queryStringParameters", {})
    user_input = query_params.get("q", None)

    if not query_params or not user_input:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Query params do not contain user_input'})
        }

    lex_reply = get_lex_reply(session_id, user_input)
    print("#############################\nThese are the slots - ", lex_reply['body'], "#############################")
    slots = json.loads(lex_reply['body'])
    os_client = get_os_client()
    opensearch_response, err = query_photos(slots, os_client)
    response = {
        'statusCode': 200 if not err else 500,
        'body': json.dumps(opensearch_response) if opensearch_response else "No images for the tags you entered!",
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin' : "*",
            'Access-Control-Allow-Methods': 'OPTIONS,GET',
            "Content-Type": "application/json",
        },
        "isBase64Encoded": False
    }
    print(f"################# Response from open search - {response} #################")
    return response
