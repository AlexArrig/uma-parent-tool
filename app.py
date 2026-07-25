import json
import os
import requests
from flask import Flask, render_template, request, session, redirect, url_for
from itertools import combinations

app = Flask(__name__)
app.secret_key = "some_random_secret_key_for_session"

DATA_DIR = "data"

def load_json_file(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def veteran_matches_blue(v, target_stat, scope):
    if not target_stat:
        return True
    
    target_lower = target_stat.lower()
    has_in_main = any(
        f["category"] == "blue" and target_lower in f["name"].lower()
        for f in v.get("localized_factors", [])
    )
    
    if scope == "main":
        return has_in_main
    
    if has_in_main:
        return True
        
    for p in v.get("localized_parents", []):
        if any(
            pf.get("category") == "blue" and target_lower in pf.get("name", "").lower()
            for pf in p.get("factors", [])
        ):
            return True
            
    return False

@app.route("/", methods=["GET", "POST"])
def index():
    char_map = load_json_file("characters.json")
    skill_map = load_json_file("skills.json")
    factor_map = load_json_file("factors.json")
    
    # Handle data.json upload and save it locally
    if request.method == "POST" and "data_file" in request.files:
        file = request.files["data_file"]
        if file and file.filename.endswith(".json"):
            try:
                os.makedirs(DATA_DIR, exist_ok=True)
                file.save(os.path.join(DATA_DIR, "data.json"))
            except Exception as e:
                print("Error saving uploaded file:", e)

    raw_data = load_json_file("data.json")
    veterans_list = raw_data if isinstance(raw_data, list) else raw_data.get("trained_chara_array", [])

    vet_lookup = {}
    for v in veterans_list:
        t_id = v.get("trained_chara_id")
        if t_id:
            vet_lookup[str(t_id)] = v

    localized_veterans = []
    
    for v in veterans_list:
        card_id = str(v.get("card_id"))
        char_info = char_map.get(card_id, {"name": f"Character #{card_id}", "title": "Custom Chara"})
        
        localized_skills = []
        for s in v.get("skill_array", []):
            s_id = str(s.get("skill_id"))
            s_info = skill_map.get(s_id, {"name": f"Skill ID {s_id}", "description": ""})
            localized_skills.append({
                "id": s_id,
                "name": s_info["name"],
                "level": s.get("level", 1),
                "description": s_info.get("description", "")
            })
            
        localized_factors = []
        for f in v.get("factor_info_array", []):
            f_id = str(f.get("factor_id"))
            f_info = factor_map.get(f_id, {"name": f"Factor #{f_id}", "type": 3, "star": 1, "description": ""})
            f_type = f_info.get("type", 3)
            star_count = f_info.get("star", 1)
            
            if f_type == 1:
                cat = "blue"
            elif f_type == 2:
                cat = "pink"
            else:
                cat = "white"
                
            localized_factors.append({
                "name": f_info["name"],
                "star": star_count,
                "category": cat,
                "description": f_info.get("description", "")
            })

        parents = []
        succession_array = v.get("succession_chara_array", [])
        succ_by_pos = {item.get("position_id"): item for item in succession_array}
        
        parent_configs = [
            {"id_key": "succession_trained_chara_id_1", "pos_id": 10},
            {"id_key": "succession_trained_chara_id_2", "pos_id": 20}
        ]
        
        for config in parent_configs:
            p_id = v.get(config["id_key"])
            p_data = None
            is_rental = False
            
            if p_id and str(p_id) in vet_lookup:
                p_data = vet_lookup[str(p_id)]
            else:
                p_data = succ_by_pos.get(config["pos_id"])
                is_rental = True
                
            if p_data:
                p_card_id = str(p_data.get("card_id"))
                p_char_info = char_map.get(p_card_id, {"name": f"Character #{p_card_id}", "title": "Rental / External"})
                
                p_factors = []
                for pf in p_data.get("factor_info_array", []):
                    pf_id = str(pf.get("factor_id"))
                    pf_info = factor_map.get(pf_id, {"name": f"Factor #{pf_id}", "type": 3, "star": 1})
                    pf_type = pf_info.get("type", 3)
                    p_factors.append({
                        "name": pf_info["name"],
                        "star": pf_info.get("star", 1),
                        "category": "blue" if pf_type == 1 else ("pink" if pf_type == 2 else "white")
                    })

                parents.append({
                    "name": p_char_info["name"],
                    "title": p_char_info["title"] + (" (Rental)" if is_rental and p_data.get("owner_viewer_id", 0) != 0 else ""),
                    "rank_score": p_data.get("rank_score", "N/A" if is_rental else "-"),
                    "speed": p_data.get("speed", "-"),
                    "stamina": p_data.get("stamina", "-"),
                    "power": p_data.get("power", "-"),
                    "guts": p_data.get("guts", "-"),
                    "wiz": p_data.get("wiz", "-"),
                    "is_rental": is_rental,
                    "factors": p_factors
                })
            else:
                parents.append({
                    "name": "Unknown Parent",
                    "title": "Inherited",
                    "rank_score": "N/A",
                    "speed": "-", "stamina": "-", "power": "-", "guts": "-", "wiz": "-",
                    "is_rental": True,
                    "factors": []
                })

        v["display_name"] = char_info["name"]
        v["display_title"] = char_info["title"]
        v["localized_skills"] = localized_skills
        v["localized_factors"] = localized_factors
        v["localized_parents"] = parents
        
        v_white_set = set()
        for f in localized_factors:
            if f["category"] == "white":
                v_white_set.add(f["name"])
        for p in parents:
            for pf in p.get("factors", []):
                if pf.get("category") == "white":
                    v_white_set.add(pf["name"])
        v["white_skill_set"] = v_white_set
        
        localized_veterans.append(v)

    sort_order = request.args.get("sort", "desc")
    try:
        localized_veterans.sort(
            key=lambda x: float(x.get("rank_score", 0)),
            reverse=(sort_order == "desc")
        )
    except Exception:
        pass

    blue_factor = request.args.get("blue_factor", "")
    blue_scope = request.args.get("blue_scope", "all")
    pair_sort = request.args.get("pair_sort", "main_total")
    
    filtered_veterans = [
        v for v in localized_veterans 
        if veteran_matches_blue(v, blue_factor, blue_scope)
    ]

    top_parent_pairs = []
    external_results = []
    external_title = ""
    action = request.args.get("action")
    
    if action == "local_sparks":
        parent_combinations = []
        for v1, v2 in combinations(filtered_veterans, 2):
            if v1.get("card_id") == v2.get("card_id"):
                continue
                
            combined_white = {}
            for f in v1.get("localized_factors", []) + v2.get("localized_factors", []):
                if f["category"] == "white":
                    name = f["name"]
                    if name not in combined_white or f["star"] > combined_white[name]["star"]:
                        combined_white[name] = f
            for p in v1.get("localized_parents", []) + v2.get("localized_parents", []):
                for pf in p.get("factors", []):
                    if pf.get("category") == "white":
                        name = pf["name"]
                        if name not in combined_white or pf["star"] > combined_white[name]["star"]:
                            combined_white[name] = pf
                            
            unique_white_list = list(combined_white.values())

            main_white = {}
            for f in v1.get("localized_factors", []) + v2.get("localized_factors", []):
                if f["category"] == "white":
                    name = f["name"]
                    if name not in main_white or f["star"] > main_white[name]["star"]:
                        main_white[name] = f
            main_white_list = list(main_white.values())

            parent_combinations.append({
                "parent1": v1,
                "parent2": v2,
                "unique_white_count": len(unique_white_list),
                "main_white_count": len(main_white_list),
                "unique_white_factors": unique_white_list
            })

        if pair_sort == "total_main":
            parent_combinations.sort(key=lambda x: (x["unique_white_count"], x["main_white_count"]), reverse=True)
        else:
            parent_combinations.sort(key=lambda x: (x["main_white_count"], x["unique_white_count"]), reverse=True)
            
        top_parent_pairs = parent_combinations[:20]

    elif action in ["rental_min_20", "rental_top_whites"]:
        if action == "rental_min_20":
            external_title = "Rental Parents Ranked by Combined Unique White Skills vs Filtered Roster"
            url = "https://uma.moe/api/v3/search?page=0&limit=100&search_type=inheritance&max_follower_num=999&parent_rank=1&min_main_white_count=20"
        else:
            external_title = "Top White Sparks Rental Parents Ranked vs Filtered Roster"
            url = "https://uma.moe/api/v3/search?page=0&limit=100&search_type=inheritance&max_follower_num=999&sort_by=white_count&sort_order=desc"
            
        api_key_header = request.args.get("api_key", "")
        headers = {"accept": "application/json"}
        if api_key_header:
            headers["X-API-Key"] = api_key_header

        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                raw_items = []
                if isinstance(data, list):
                    raw_items = data
                elif isinstance(data, dict):
                    raw_items = data.get("items", data.get("results", data.get("data", [])))
                    if not raw_items:
                        for val in data.values():
                            if isinstance(val, list):
                                raw_items = val
                                break

                for item in raw_items:
                    inheritance = item.get("inheritance", {})
                    main_id = str(inheritance.get("main_parent_id", ""))
                    char_info = char_map.get(main_id, {"name": f"Character #{main_id}" if main_id else "External Character", "title": "Rental Parent"})
                    
                    rental_white_set = set()
                    for k in ["white_sparks", "white_skills", "white_factor_array", "white_factors"]:
                        if k in inheritance:
                            for fid in inheritance[k]:
                                f_info = factor_map.get(str(fid), {})
                                if f_info:
                                    rental_white_set.add(f_info.get("name", f"Factor #{fid}"))
                    
                    fallback_count = inheritance.get("white_count") or item.get("white_count") or 20
                    if not rental_white_set:
                        for i in range(int(fallback_count)):
                            rental_white_set.add(f"Rental_White_{main_id}_{i}")

                    best_combined_count = 0
                    best_vet_match = None
                    
                    if filtered_veterans:
                        for v in filtered_veterans:
                            v_set = v.get("white_skill_set", set())
                            if not v_set:
                                v_set = {f"Local_White_{v.get('card_id')}_{i}" for i in range(20)}
                                
                            combined_set = v_set.union(rental_white_set)
                            combined_count = len(combined_set)
                            if combined_count > best_combined_count:
                                best_combined_count = combined_count
                                best_vet_match = v
                    else:
                        best_combined_count = len(rental_white_set)

                    external_results.append({
                        "trainer_name": item.get("trainer_name", "Unknown Trainer"),
                        "account_id": item.get("account_id", "N/A"),
                        "follower_num": item.get("follower_num", "N/A"),
                        "chara_name": char_info.get("name", "External Character"),
                        "chara_title": char_info.get("title", "Rental"),
                        "white_count": inheritance.get("white_count", item.get("white_count", "N/A")),
                        "combined_unique_count": best_combined_count,
                        "best_veteran": best_vet_match,
                        "rank": inheritance.get("parent_rank", "N/A")
                    })
                
                external_results.sort(key=lambda x: x["combined_unique_count"], reverse=True)
                external_results = external_results[:20]
        except Exception as e:
            print("API Error Exception:", e)

    return render_template(
        "index.html", 
        veterans=localized_veterans, 
        current_sort=sort_order, 
        top_parent_pairs=top_parent_pairs,
        external_results=external_results,
        external_title=external_title,
        action_triggered=action,
        blue_factor=blue_factor,
        blue_scope=blue_scope,
        pair_sort=pair_sort,
        filtered_count=len(filtered_veterans),
        has_data_loaded=bool(raw_data)
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)