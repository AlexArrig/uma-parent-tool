import os
import json
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATA_FILE_PATH = os.path.join(UPLOAD_FOLDER, 'data.json')

def load_roster_data():
    """Loads and robustly normalizes roster data from the uploaded data.json file."""
    if not os.path.exists(DATA_FILE_PATH):
        return []
    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if isinstance(data, list):
                veterans = data
            elif isinstance(data, dict):
                veterans = data.get('veterans', data.get('chara_list', data.get('roster', [])))
            else:
                veterans = []
            
            processed = []
            for v in veterans:
                norm_v = {}
                # Robust name and title fallbacks across different extraction schemas
                norm_v['display_name'] = (
                    v.get('display_name') or v.get('name') or 
                    v.get('chara_name') or v.get('character_name') or 'Unknown Uma'
                )
                norm_v['display_title'] = (
                    v.get('display_title') or v.get('title') or 
                    v.get('chara_title') or v.get('character_title') or ''
                )
                norm_v['rank_score'] = int(
                    v.get('rank_score') or v.get('score') or 
                    v.get('evaluation') or v.get('rate') or 0
                )
                
                # Stats mapping
                norm_v['speed'] = int(v.get('speed') or v.get('spd') or 0)
                norm_v['stamina'] = int(v.get('stamina') or v.get('sta') or 0)
                norm_v['power'] = int(v.get('power') or v.get('pwr') or 0)
                norm_v['guts'] = int(v.get('guts') or v.get('gut') or 0)
                norm_v['wiz'] = int(v.get('wiz') or v.get('wit') or v.get('wisdom') or 0)

                # Factors mapping
                factors = v.get('localized_factors') or v.get('factors') or v.get('sparks') or []
                norm_factors = []
                for f in factors:
                    if isinstance(f, dict):
                        norm_factors.append({
                            'name': f.get('name') or f.get('factor_name') or 'Unknown Factor',
                            'star': int(f.get('star') or f.get('level') or f.get('stars') or 1),
                            'category': str(f.get('category') or f.get('type') or f.get('color') or 'blue').lower()
                        })
                    elif isinstance(f, str):
                        norm_factors.append({'name': f, 'star': 1, 'category': 'blue'})
                norm_v['localized_factors'] = norm_factors

                # Parents mapping
                parents = v.get('localized_parents') or v.get('parents') or []
                norm_parents = []
                for p in parents:
                    if isinstance(p, dict):
                        norm_parents.append({
                            'name': p.get('name') or p.get('chara_name') or 'Unknown Parent',
                            'title': p.get('title') or p.get('chara_title') or ''
                        })
                    elif isinstance(p, str):
                        norm_parents.append({'name': p, 'title': ''})
                norm_v['localized_parents'] = norm_parents

                # White skill counts calculation / fallback
                main_whites = sum(1 for f in norm_factors if f.get('category') in ['white', 'skill'])
                if main_whites == 0 and len(norm_factors) > 0:
                    main_whites = int(v.get('main_white_count') or v.get('main_whites') or len(norm_factors))
                else:
                    main_whites = int(v.get('main_white_count') or v.get('main_whites') or main_whites)

                norm_v['main_white_count'] = main_whites
                norm_v['total_white_count'] = int(v.get('total_white_count') or v.get('total_whites') or (main_whites * 2))

                processed.append(norm_v)
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

    current_sort = request.args.get("sort", "desc")
    blue_factor = request.args.get("blue_factor", "")
    blue_scope = request.args.get("blue_scope", "all")
    pair_sort = request.args.get("pair_sort", "main_total")
    action_triggered = request.args.get("action", "")
    api_key = request.args.get("api_key", "")

    # Filter veterans for Parent Finder
    filtered_veterans = veterans
    if blue_factor:
        filtered_veterans = [
            v for v in veterans 
            if any(
                str(f.get('name', '')).lower() == blue_factor.lower() and f.get('category', '') == 'blue' 
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