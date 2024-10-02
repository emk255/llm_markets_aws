import boto3, re, json, random, hashlib, math, time, os
from model_info import model_configs
import pandas as pd
import numpy as np
from constants import *
from utilities import parse_json, hash_id, run_api
from itertools import combinations, product
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import deferred_acceptance as da

jobs = pd.read_csv('data/jobs_df.csv')[['Content', 'job_cluster']]
job_clusters = [1,23,13]
jobs_df = pd.DataFrame()
for cluster in job_clusters:
    sampled = jobs[jobs['job_cluster']==cluster].sample(1, random_state=123)
    jobs_df = pd.concat([jobs_df, sampled])
    
jobs_df = jobs_df.reset_index(drop = True)

resumes = pd.read_csv('data/resume_df.csv')
resume_clusters = [10,26,23]
resumes_df = pd.DataFrame()
for cluster in resume_clusters:
    sampled = resumes[resumes['resume_cluster']==cluster].sample(1, random_state=123)
    resumes_df = pd.concat([resumes_df, sampled])
resumes_df = resumes_df.reset_index(drop = True)

df = pd.merge(jobs_df, resumes_df, how = "cross").rename(columns={"Content":"Job"}).reset_index()
df['index'] = df['index'].apply(hash_id)

jobs = df['Job'].unique()
resumes = df['Resume'].unique()

resume_id_map = {resume: hash_id(resume) for resume in resumes}
job_id_map = {job: hash_id(job) for job in jobs}

df['Resume_index'] = df['Resume'].map(resume_id_map)
df['Job_index'] = df['Job'].map(job_id_map)

prompts = [firm_rate_comb1]
name_dic = {firm_rate_p1:'firm_rate_p1', firm_rate_p2:'firm_rate_p2', 
            app_rate_p0:"app_rate_p0", firm_rate_lenient:'firm_rate_lenient', 
            app_rate_comb:"app_rate_comb", firm_rate_comb:"firm_rate_comb",
           firm_rate_comb1: "firm_rate_comb1", firm_rate_comb2: "firm_rate_comb2",
           firm_rate_comb_short: "firm_rate_comb_short", app_rate_comb_short: "app_rate_comb_short",
           firm_rate_comb_short_1: "firm_rate_comb_short_1"}

models = ['us.meta.llama3-2-11b-instruct-v1:0','us.meta.llama3-2-90b-instruct-v1:0']
for row, col in df.iterrows():
    start = time.time()
    
    resume = col['Resume']
    job = col['Job']
    for modelId in models:
        model = model_configs[modelId]
        for p in prompts:
            prompt = p + f"""

            Resume: {resume}

            Job Description: {job}

            Json File:

            Assistant:
            """
            output=''
            cost = model['cost_mapping'][0] * len(prompt)
            try:
                output = run_api(modelId, model['config'], prompt)
#                 print(output)
                if output is not None:
                    df.at[row, f"{model['short_name']}_{name_dic[p]}"] = output['Score']
                    cost += model['cost_mapping'][1] * len(output)
                    df.at[row, f"{model['short_name']}_{name_dic[p]}_cost"] = cost
                else:
                    df.at[row, f"{model['short_name']}_{name_dic[p]}"] = 1
                
            except Exception as e:
                print(output, e)
    end = time.time()
    print(row, end-start)
    
model_key = ['Llama','Mistral','Hand']
filtered_columns = [col for col in df.columns if any(key in col for key in model_key)]
for col in filtered_columns:
    df[col] = pd.to_numeric(df[col], errors='coerce')
    df[col] = df[col] + np.random.uniform(0, 1, len(df[col]))

csv_file_path = "data/df_105x105.csv"  

df.to_csv(csv_file_path, index = False)

def upload_to_s3(file_name, bucket, object_name=None):
    if object_name is None:
        object_name = os.path.basename(file_name)

    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
        print(f"{file_name} has been uploaded to {bucket}/{object_name}")
    except Exception as e:
        print(f"Error uploading {file_name}: {e}")
        raise e
    
s3_bucket = "llm-markets"  # Replace this with your S3 bucket name
upload_to_s3(csv_file_path, s3_bucket)

