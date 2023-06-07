import base64
import json
import redis
from redis.commands.json.path import Path
import redis.commands.bf
import time
import os
import datetime
import functions_framework
from transformers import AutoModelForSequenceClassification
from transformers import AutoTokenizer
import numpy as np
from scipy.special import softmax

REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = os.environ.get('REDIS_PORT')
REDIS_PWD = os.environ.get('REDIS_PWD')
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PWD, db=0)

# Create a T-Digest Structure if not exists
if not redis_client.exists("satisfaction-tdigest"):
    redis_client.tdigest().create("satisfaction-tdigest", 1000)

print("******** Redis Demo : Customer Satisfaction : GCP Cloud Function - START ********")

# Triggered from a message on a Cloud Pub/Sub topic.
@functions_framework.cloud_event
def pubsub_event_function(cloud_event):
    payload = base64.b64decode(cloud_event.data['message']['data']).decode('utf-8')
    customer_id=cloud_event.data["message"]["orderingKey"]

    # Reserve the Top-K Structure if not exists
    if not redis_client.exists(f"sentiment-tk:customer:{customer_id}"):
        redis_client.topk().reserve(f"sentiment-tk:customer:{customer_id}", 3, 5000, 3, 0.9)
    
    if payload == 'exit':
        print(f"Conversation Finished with Customer {customer_id}")
        satisfaction_score = get_satisfaction_score(customer_id)
        persist_conversation_score(customer_id, satisfaction_score)
    else: 
        persist_conversation_data(customer_id,payload)
        output = perform_inference(payload)
        persist_analysis_scores(customer_id,output)

def persist_conversation_score(customer_id,satisfaction_score):
    print("** persist_conversation_score - START")
    now = datetime.datetime.now() # current date and time
    trans_date_trans_time = now.strftime("%Y/%m/%d-%H:%M:%S")
    key = "customer-satisfaction:" + customer_id

    data = {}
    data['end_time'] = trans_date_trans_time
    data['score'] = satisfaction_score
    
    # Merging the conversation end time and overall score
    # Available Only in Redis 7.2-RC1
    # redis_client.json().merge(key, Path.root_path(), data)

    # Adding the satisfaction Score to T-digest structure
    redis_client.tdigest().add("satisfaction-tdigest", [float(satisfaction_score)])

    print("** persist_conversation_score - END")
    

def perform_inference(data_payload):
    print("** perform_inference - START")
    output = {}
    sentiment_labels=["negative","neutral","positive"]
    emotion_labels=["anger","joy","optimism","sadness"]

    output["sentiment_analysis"] = get_analysis(data_payload, "sentiment", sentiment_labels)
    output["emotion_analysis"] = get_analysis(data_payload, "emotion", emotion_labels)

    print("** perform_inference - END")
    return output

def get_analysis(data, task, labels):
    MODEL = f"cardiffnlp/twitter-roberta-base-{task}"
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    tokenizer.save_pretrained("/tmp") 

    model = AutoModelForSequenceClassification.from_pretrained(MODEL)
    model.save_pretrained("/tmp")

    encoded_input = tokenizer(data, return_tensors='pt')
    output = model(**encoded_input)
    scores = output[0][0].detach().numpy()
    scores = softmax(scores)

    ranking = np.argsort(scores)
    ranking = ranking[::-1]
    output = []
    for i in range(scores.shape[0]):
        l = labels[ranking[i]]
        s = scores[ranking[i]]
        output.insert(i, {'label_index' : int(ranking[i]),'label' : l, 'score' : np.round(float(s), 4)}) 

    return output
    
def persist_conversation_data(customer_id,payload):
    print("** persist_conversation_data - START")
    now = datetime.datetime.now() # current date and time
    trans_date_trans_time = now.strftime("%Y/%m/%d-%H:%M:%S")
    key = "customer-satisfaction:" + customer_id
    
    if redis_client.exists(key):
        prompt = {}
        prompt['publish_time'] = trans_date_trans_time
        prompt['content'] = payload
        redis_client.json().arrappend(key, "$.transcription", prompt)
    else:
        data = {}
        data['customer_id'] = customer_id
        data['start_time'] = trans_date_trans_time
        prompt = {}
        prompt['publish_time'] = trans_date_trans_time
        prompt['content'] = payload
        data['transcription'] = [prompt]
        redis_client.json().set(key, Path.root_path(), data)    
        
    result = redis_client.json().get(key)
    print("** persist_conversation_data - END")

def get_satisfaction_score(customer_id):
    sentiments_count_array = redis_client.topk().count(f"sentiment-tk:customer:{customer_id}", 0, 1, 2)
    sentiments_count = np.sum(sentiments_count_array)

    positive_sentiment_percentage = np.round(float(sentiments_count_array[2] / sentiments_count), 4)
    neutral_sentiment_percentage = np.round(float(sentiments_count_array[1] / sentiments_count), 4)
    negative_sentiment_percentage = np.round(float(sentiments_count_array[0] / sentiments_count), 4)

    satisfaction_score = positive_sentiment_percentage + neutral_sentiment_percentage - negative_sentiment_percentage
    satisfaction_score = 0 if satisfaction_score < 0 or np.isnan(satisfaction_score) else satisfaction_score
    return satisfaction_score

def persist_analysis_scores(customer_id,output):
    print("** persist_analysis_scores - START")

    now = datetime.datetime.now() # current date and time
    timestamp = int(round(now.timestamp()))

    # Save the prevalent sentiment
    label_index = output['sentiment_analysis'][0]['label_index']
    redis_client.ts().add(f"sentiment-ts:customer:{customer_id}",timestamp,label_index,duplicate_policy='last', labels={'type': "sentiment"})
    
    # Adding the sentiment to Top-K structure
    redis_client.topk().add(f"sentiment-tk:customer:{customer_id}", label_index)

    # Calculate the satisfaction score
    satisfaction_score = get_satisfaction_score(customer_id)

    # Save the satisfaction score
    redis_client.ts().add(f"overall-satisfaction-ts:customer:{customer_id}",timestamp,satisfaction_score,duplicate_policy='last', labels={'type': "satisfaction"})

    # Save positive sentiments for timeline analysis
    for sentence in output['sentiment_analysis']:
        if sentence['label_index'] == 2:
            score = sentence['score']
            redis_client.ts().add(f"sentiment-positive-ts:customer:{customer_id}",timestamp,score,duplicate_policy='last', labels={'type': "sentiment_positive_score"})
            break

    # Save the prevalent emotion
    label_index = output['emotion_analysis'][0]['label_index']
    redis_client.ts().add(f"emotion-ts:customer:{customer_id}",timestamp,label_index,duplicate_policy='last', labels={'type': "emotion"})
        
    print("** persist_analysis_scores - END")