import os
import json
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Configure upload storage folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATA_FILE_PATH = os.path.join(UPLOAD_FOLDER, 'data.json')

def load_roster_data():
    """Loads and normalizes roster data from the uploaded data.json file with safe fallbacks."""
    if not os.path.exists(DATA_FILE_PATH):
        return []
    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Support both raw lists and wrapped dictionaries
            if isinstance(data, list):
                veterans = data
            elif isinstance(data, dict):
                veterans = data.get('veterans', data.get('chara_list', []))
            else:
                veterans = []
            
            processed = []
            for v in veterans:
                # 1. Fallbacks for missing display names and titles to fix blank cards
                v['display_name'] = v.get('display_name') or v.get('name') or v.get('chara_name') or 'Unknown Uma'
                v['display_title'] = v.get('display_title') or v.get('title') or v.get('chara_title') or ''

                # 2. Ensure factors and parents are valid lists
                if 'localized_factors' not in v:
                    v['localized_factors'] = v.get('factors', [])
                if 'localized_parents' not in v:
                    v['localized_parents'] = v.get('parents', [])

                # 3. Ensure white skill counts exist for sorting
                if 'main_white_count' not in v:
                    factors = v.get('localized_factors', [])
                    v['main_white_count'] = sum(
                        1 for f in factors 
                        if str(f.get('category', '')).lower() == 'white' or str(f.get('type', '')).lower() == 'white'
                    )
                if 'total_white_count' not in v:
                    v['total_white_count'] = v.get('main_white_count', 0) * 2
                
                processed.append(v)
            return processed
    except Exception as e:
        print(f"Error loading data.json: {e}")
        return []

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get('data_file')
        if file and file.filename.endswith('.json'):
            file.save(DATA_FILE_PATH)
        return redirect(url_for('index'))

    has_data_file = os.path.exists(DATA_FILE_PATH)
    veterans = load_roster_data()

    # Retrieve query parameters from frontend requests
    current_sort = request.args.get("sort", "desc")
    blue_factor = request.args.get("blue_factor", "")
    blue_scope = request.args.get("blue_scope", "all")
    pair_sort = request.args.get("pair_sort", "main_total")
    action_triggered = request.args.get("action", "")
    api_key = request.args.get("api_key", "")

    # Filter veterans for Parent Finder based on selected blue factor
    filtered_veterans = veterans
    if blue_factor:
        filtered_veterans = [
            v for v in veterans 
            if any(
                str(f.get('name', '')).lower() == blue_factor.lower() and str(f.get('category', '')).lower() == 'blue' 
                for f in v.get('localized_factors', [])
            )
        ]

    filtered_count = len(filtered_veterans)

    # Roster Sorting Logic
    if current_sort == "desc":
        veterans = sorted(veterans, key=lambda x: x.get("rank_score", 0), reverse=True)
    elif current_sort == "asc":
        veterans = sorted(veterans, key=lambda x: x.get("rank_score", 0), reverse=False)
    elif current_sort == "main_white":
        veterans = sorted(veterans, key=lambda x: x.get("main_white_count", 0), reverse=True)
    elif current_sort == "total_white":
        veterans = sorted(veterans, key=lambda x: x.get("total_white_count", 0), reverse=True)

    # Parent Finder Action Handlers
    top_parent_pairs = []
    external_results = []
    external_title = ""

    if action_triggered == "local_sparks":
        pairs = []
        for i in range(len(filtered_veterans)):
            for j in range(i + 1, len(filtered_veterans)):
                v1 = filtered_veterans[i]
                v2 = filtered_veterans[j]
                unique_whites = v1.get('main_white_count', 0) + v2.get('main_white_count', 0)
                main_whites = min(v1.get('main_white_count', 0), v2.get('main_white_count', 0))
                pairs.append({
                    "parent1": v1,
                    "parent2": v2,
                    "unique_white_count": unique_whites,
                    "main_white_count": main_whites
                })
        
        if pair_sort == "total_main":
            pairs.sort(key=lambda x: x['unique_white_count'], reverse=True)
        else:
            pairs.sort(key=lambda x: x['main_white_count'], reverse=True)
            
        top_parent_pairs = pairs[:20]

    elif action_triggered in ["rental_min_20", "rental_top_whites"]:
        external_title = "Top White Sparks Rentals" if action_triggered == "rental_top_whites" else "Rental Parents (Min 20 Main Whites)"
        if api_key:
            try:
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get("https://uma.moe/api/rentals", headers=headers, timeout=5)
                if response.status_code == 200:
                    external_results = response.json().get('results', [])
            except Exception as e:
                print(f"API Request error: {e}")

    return render_template(
        "index.html",
        veterans=veterans,
        has_data_file=has_data_file,
        current_sort=current_sort,
        blue_factor=blue_factor,
        blue_scope=blue_scope,
        pair_sort=pair_sort,
        action_triggered=action_triggered,
        filtered_count=filtered_count,
        top_parent_pairs=top_parent_pairs,
        external_results=external_results,
        external_title=external_title
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)