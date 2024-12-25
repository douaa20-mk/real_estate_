from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import re
import openai

app = Flask(__name__)
CORS(app)

# Load the real estate data
real_estate_data = pd.read_csv('modified_algeria_real_estate_random.csv')

# Synonyms for flexibility
property_synonyms = {
    "house": "villa",
    "flat": "apartment",
    "f4": "f3|f6",
    "studio": "apartment"
}

location_synonyms = {
    "oran": "oran",
    "alger": "algiers",
    "constantine": "constantine",
    "annaba": "annaba",
    "batna": "batna",
    "béjaïa": "bejaia",
    "blida": "blida"
}

def replace_synonyms(text, synonyms_dict):
    for key, value in synonyms_dict.items():
        text = re.sub(key, value, text)
    return text

def parse_query(query):
    query = query.lower()
    query = replace_synonyms(query, property_synonyms)
    query = replace_synonyms(query, location_synonyms)

    # Extract location, property type, and price range using regex
    location = re.search(r"(oran|algiers|constantine|annaba|batna|bejaia|blida)", query)
    property_type = re.search(r"(villa|f3|f6|apartment)", query)
    price_range = re.search(r"(less than \d+m|more than \d+m|between \d+m and \d+m)", query)

    return {
        "location": location.group(0) if location else None,
        "property_type": property_type.group(0) if property_type else None,
        "price_range": price_range.group(0) if price_range else None
    }

def filter_properties(criteria):
    result = real_estate_data.copy()

    if criteria["property_type"]:
        result = result[result['Property'].str.contains(criteria["property_type"], case=False)]
    if criteria["location"]:
        result = result[result['City'].str.contains(criteria["location"], case=False)]
    if criteria["price_range"]:
        if "less than" in criteria["price_range"]:
            price = int(re.search(r"\d+", criteria["price_range"]).group(0))
            result = result[result['Price Range'].str.contains(f"Less than {price}M", case=False)]
        elif "more than" in criteria["price_range"]:
            price = int(re.search(r"\d+", criteria["price_range"]).group(0))
            result = result[result['Price Range'].str.contains(f"More than {price}M", case=False)]
        elif "between" in criteria["price_range"]:
            numbers = re.findall(r"\d+", criteria["price_range"])
            result = result[result['Price Range'].str.contains(f"{numbers[0]}M-{numbers[1]}M", case=False)]
    return result

def get_chatgpt_response(prompt):
    try:
        openai.api_key =  "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"

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return "Sorry, I couldn't connect to ChatGPT at the moment."

@app.route('/query', methods=['POST'])
def query():
    query = request.json.get('query', '')
    criteria = parse_query(query)

    if not any(criteria.values()):
        return jsonify({
            "status": "error",
            "message": "Please specify property type, location, or price range."
        })

    filtered_data = filter_properties(criteria)
    if filtered_data.empty:
        gpt_prompt = f"The user searched for real estate with the following criteria: {criteria}. Could you suggest how they might broaden their search or what alternatives they might consider?"
        gpt_response = get_chatgpt_response(gpt_prompt)
        return jsonify({
            "status": "no_results",
            "message": "No matching properties found.",
            "suggestion": gpt_response
        })
    
    return jsonify({
        "status": "success",
        "data": filtered_data[['Property', 'City', 'Price Range']].head(5).to_dict(orient='records')
    })

if __name__ == '__main__':
    app.run(debug=True)