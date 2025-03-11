# app.py

from flask import Flask, jsonify, request
import json
from collections import defaultdict


app = Flask(__name__)

dataset_path = "VisualizeTask\edinburgh_knn2rest.json"

# Load the dataset once at startup
with open('result_4_Chuongg.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Extract restaurant-to-keyword mappings
restaurant_to_keywords = defaultdict(set)
for user_id, user_data in data.items():
    keywords = user_data.get('kw', [])
    candidates = user_data.get('candidate', [])

    # Ensure both keywords and candidates are lists and clean them
    if not isinstance(keywords, list) or not isinstance(candidates, list):
        app.logger.warning(f"Invalid data for user {user_id}: 'kw' or 'candidate' not a list.")
        continue

    min_length = min(len(keywords), len(candidates))  # Handle mismatched lengths
    for candidate, keyword in zip(candidates[:min_length], keywords[:min_length]):
        # Strip whitespace from both keywords and candidates
        cleaned_keyword = keyword.strip()
        cleaned_candidate = candidate.strip()

        if cleaned_candidate and cleaned_keyword:  # Skip empty entries
            restaurant_to_keywords[cleaned_candidate].add(cleaned_keyword)

@app.route('/get_restaurant_keywords', methods=['GET'])
def get_restaurant_keywords():
    # Get selected keywords from query parameters
    selected_keywords = request.args.getlist('keywords')
    selected_keywords = [kw.strip() for kw in selected_keywords]

    if not selected_keywords:
        return jsonify([])

    filtered_edges = []
    restaurant_connections = defaultdict(int)

    # Build edges and count connections for restaurants
    for restaurant, keywords in restaurant_to_keywords.items():
        for keyword in keywords:
            if keyword in selected_keywords:
                filtered_edges.append((keyword, restaurant))
                restaurant_connections[restaurant] += 1

    # Add a 'special' flag to restaurants with multiple connections
    filtered_edges_with_flags = [
        {"keyword": keyword, "restaurant": restaurant, "special": restaurant_connections[restaurant] > 1}
        for keyword, restaurant in filtered_edges
    ]

    return jsonify(filtered_edges_with_flags)

# Serve CSS file
# app_dir = Path(__file__).parent
# @app.route('/styles.css')
# def serve_css():
#     return send_from_directory(app_dir, 'styles.css')
#     # return send_from_directory(os.getcwd(), 'styles.css')

if __name__ == '__main__':
    app.run(debug=True)
