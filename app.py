from flask import Flask, render_template, request, jsonify
import requests
from textblob import TextBlob  # type: ignore
import speech_recognition as sr
import csv
import json
import threading
import queue
import io
import numpy as np

app = Flask(__name__)

# Load CRM data with proper encoding
def load_crm_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

CRM_DATA = load_crm_data('crm_data.json')

def query_llama_llm(user_input, customer_context):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json"
    }
    
    negotiation_prompt = (
    f"Your name is Alexa, an advanced AI-powered  Negotiation Bot. "
    f"You are assisting a customer named {customer_context['name']}."
    f"{' The customer prefers ' + customer_context['preferences'] if customer_context.get('preferences') else ''}."
    f"{' They have previously purchased ' + ', '.join(customer_context['purchase_history']) if customer_context.get('purchase_history') else ''}."
    f"{' During the last interaction, the customer showed interest in ' + customer_context['last_interaction'] if customer_context.get('last_interaction') else ''}."
    f" If this is the first interaction or there is no prior context, focus on making a positive first impression and guiding the customer effectively."
    " Analyze the language, sentiment, and tone to provide tailored recommendations and strategies to negotiate prices "
    "or discuss queries about products. "
    "Respond professionally to maximize customer satisfaction while protecting profitability. "
    "You're in India, so provide prices in INR format without using the ₹ symbol - use 'INR' instead."
)

    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": negotiation_prompt},
            {"role": "user", "content": user_input}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json().get("choices")[0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"Error in API call: {str(e)}"

def analyze_sentiment(user_input):
    analysis = TextBlob(user_input)
    polarity = analysis.sentiment.polarity
    sentiment = "Positive" if polarity > 0 else "Negative" if polarity < 0 else "Neutral"
    return sentiment, polarity

# Updated CSV logging function with proper encoding
def log_to_csv(file_name, data):
    try:
        # First, ensure all data is properly converted to strings
        formatted_data = [str(item).encode('utf-8').decode('utf-8') if item is not None else '' for item in data]
        
        # Try to append to existing file
        try:
            with open(file_name, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(formatted_data)
        except FileNotFoundError:
            # If file doesn't exist, create it with headers
            with open(file_name, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['Customer Name', 'User Input', 'Sentiment', 'Sentiment Score', 'Response'])
                writer.writerow(formatted_data)
    except Exception as e:
        print(f"Error logging to CSV: {str(e)}")
        # Continue execution even if logging fails
        pass

# Speech recognition function with error handling
def recognize_speech():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("Listening...")
            r.adjust_for_ambient_noise(source)
            audio = r.listen(source)
            
        text = r.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError:
        return "Could not request results"
    except Exception as e:
        print(f"Error in speech recognition: {str(e)}")
        return "Error in speech recognition"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_listening', methods=['POST'])
def start_listening():
    text = recognize_speech()
    return jsonify({"text": text})

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if request.is_json:
            data = request.get_json()
            user_input = data.get('user_input', '')
            customer_name = data.get('customer_name', '')
        else:
            user_input = request.form.get('user_input', '')
            customer_name = request.form.get('customer_name', '')
        
        default_context = {
            "name": customer_name,
            "preferences": "Not specified",
            "purchase_history": [],
            "last_interaction": "None"
        }
        
        customer_context = CRM_DATA.get(customer_name.lower(), default_context)
        
        sentiment, sentiment_score = analyze_sentiment(user_input)
        response = query_llama_llm(user_input, customer_context)
        
        # Log the interaction
        try:
            log_to_csv("sales_data1.csv", [customer_context['name'], user_input, sentiment, sentiment_score, response])
        except Exception as e:
            print(f"Logging error: {str(e)}")  # Log error but continue execution
        
        if request.is_json:
            return jsonify({
                "sentiment": {"sentiment": sentiment, "polarity": sentiment_score},
                "llama_response": response
            })
        else:
            return render_template('result.html', 
                                user_input=user_input, 
                                sentiment=sentiment, 
                                sentiment_score=sentiment_score, 
                                response=response)
                                
    except Exception as e:
        print(f"Error in analyze route: {str(e)}")
        return jsonify({"error": "An error occurred processing your request"}), 500

@app.route('/sentiment_data', methods=['GET'])
def sentiment_data():
    # Load the sentiment data from the CSV file
    sentiments = []
    try:
        with open("sales_data1.csv", mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                sentiments.append({
                    "name": row["Customer Name"],
                    "sentiment": row["Sentiment"],
                    "score": float(row["Sentiment Score"])
                })
    except FileNotFoundError:
        return jsonify({"error": "No data available"}), 404
    
    # Process the sentiments to separate positive, negative, and neutral
    positive_scores = [s["score"] for s in sentiments if s["sentiment"] == "Positive"]
    negative_scores = [s["score"] for s in sentiments if s["sentiment"] == "Negative"]
    neutral_scores = [s["score"] for s in sentiments if s["sentiment"] == "Neutral"]

    # Calculate averages for the graph
    data = {
        "positive": np.mean(positive_scores) if positive_scores else 0,
        "negative": np.mean(negative_scores) if negative_scores else 0,
        "neutral": np.mean(neutral_scores) if neutral_scores else 0,
    }
    
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
