import re
import json, hashlib
from model_info import model_configs
import constants
import boto3
### function that parses output of LLM to get json part
def parse_json(output):
    escape_characters = '\n\r\t\b\f\v'
    translation_table = str.maketrans('', '', escape_characters)
    
    output = output.translate(translation_table)
    
    json_match = re.search(r"(\{[^}]*\})", output, re.DOTALL)
    if json_match:
        json_part = json_match.group(1)
        try:
            json_data = json.loads(json_part)
        except json.JSONDecodeError as e:
            error_message = str(e)
            json_data = None
    else:
        json_part = None
        json_data = None
        error_message = "No JSON structure found."
    return json_data

def hash_id(x):
    return hashlib.sha256(str(x).encode()).hexdigest()





def run_api(modelId, model_configuration, prompt):
#     session = boto3.Session(profile_name='sso-elliot')
    session = boto3.Session(profile_name='sso-elliot', region_name="us-west-2")
    bedrock = session.client(service_name='bedrock-runtime')
    
    model = model_configs[modelId]
    config = {}
    if 'amazon' in modelId:
        config['textGenerationConfig'] = model_configuration.copy()
        config['inputText'] = prompt
        response = bedrock.invoke_model(body=json.dumps(config), modelId=modelId, accept="application/json", contentType="application/json")
        response_body = json.loads(response.get('body').read())['results'][0]
    elif 'mistral' in modelId:
        config = model_configuration.copy()
        config["prompt"] = prompt
        response = bedrock.invoke_model(body=json.dumps(config), modelId=modelId, accept="application/json", contentType="application/json")
        response_body = json.loads(response.get('body').read()).get('outputs')[0]
    else:
        config = model_configuration.copy()
        config["prompt"] = prompt
        response = bedrock.invoke_model(body=json.dumps(config), modelId=modelId, accept="application/json", contentType="application/json")
        response_body = json.loads(response.get('body').read())
        
    if model["keyword"] not in response_body:
    #         print(resume_job[1]['index'], response_body)
        raise Exception("Something went wrong")
        
    response_text = response_body.get(model["keyword"])
    model_json_response = parse_json(response_text)
    return model_json_response