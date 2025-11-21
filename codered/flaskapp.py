from flask import Flask, request, jsonify
from flask_cors import CORS
from mltoxiccheck import modelCheck
import re

app = Flask(__name__)
CORS(app)

# --- LAYER 1: PRIVACY CHECK ---
def check_privacy_leak(prompt):
    ssn_pattern = r"\b\d{3}-\d{2,3}-\d{4}\b"
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    if re.search(ssn_pattern, prompt): return "Block: Contains SSN pattern"
    if re.search(email_pattern, prompt): return "Block: Contains Email Address"
    return None 

# --- LAYER 2: INTENT & KEYWORD BLOCK (The "Bouncer") ---
def check_intent_and_keywords(prompt):
    p = prompt.lower()
    
    # 1. JAILBREAK / ROLEPLAY
    jailbreaks = [
        "ignore previous instructions", "act like dan", "do anything now", 
        "simulate", "system prompt", "jailbreak", "developer mode",
        "ignore all rules", "pretend", "imagine", "roleplay", 
        "hypothetical", "unfiltered", "uncensored", "you are now",
        "allowed to", "authorized to", "override"
    ]
    
    # 2. FRAUD / FINANCIAL CRIME
    frauds = [
        "fetch me money", "steal money", "transfer funds", "bank details", 
        "credit card number", "bypass security", "steal identity"
    ]

    # 3. VIOLENCE / WEAPONS (Zero Tolerance - INSTANT BLOCK)
    # We moved "bomb", "kill", etc. here so they don't rely on math scores.
    violence = [
        "bomb", "explosive", "detonate", "kill", "murder", "shoot", 
        "weapon", "gun", "suicide", "terrorist", "nuclear", "anthrax", "death"
    ]

    # 4. PHYSICAL HARM / SECURITY BYPASS
    physical_harm = [
        "disable", "bypass", "cut wire", "silence", "deactivate", 
        "pick lock", "lockpick", "camera", "cctv", "alarm", "sentry"
    ]

    for phrase in jailbreaks:
        if phrase in p: return f"Block: Jailbreak detected ('{phrase}')"
            
    for phrase in frauds:
        if phrase in p: return f"Block: Fraud detected ('{phrase}')"
            
    for phrase in violence:
        if phrase in p: return f"Block: Violence detected ('{phrase}')"

    # Special check for physical security (needs context)
    for phrase in physical_harm:
        if phrase in p:
            # Only block "disable" if it's about a camera/alarm/lock
            if "camera" in p or "cctv" in p or "alarm" in p or "lock" in p:
                 return f"Block: Security threat detected ('{phrase}')"

    return None

# --- LAYER 3: AI SCORING (For general toxicity/insults) ---
def rule_based_score(prompt):
    prompt_l = prompt.lower()
    # Only "softer" bad words stay here for scoring
    kw = ["stupid", "idiot", "hate", "ugly", "fat", "dumb", "hack", "exploit"] 
    hits = sum(1 for k in kw if k in prompt_l)
    return min(100, hits * 30)

ML_WEIGHT = 0.7
RULE_WEIGHT = 0.3
FINAL_THRESHOLD = 50

@app.route("/safe-check", methods=["POST"])
def safe_check():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
    if not isinstance(prompt, str): prompt = str(prompt)

    # 1. Privacy
    privacy_msg = check_privacy_leak(prompt)
    if privacy_msg:
        return jsonify({"flagged": True, "message": privacy_msg, "score": 100}), 200

    # 2. Intent & Keywords (Now includes Bomb/Violence)
    block_msg = check_intent_and_keywords(prompt)
    if block_msg:
        return jsonify({"flagged": True, "message": block_msg, "score": 100}), 200

    # 3. AI Toxicity
    ml = modelCheck(prompt, threshold=FINAL_THRESHOLD)
    combined = round(ML_WEIGHT * ml["score"] + RULE_WEIGHT * rule_based_score(prompt), 2)
    flagged = combined >= FINAL_THRESHOLD

    return jsonify({
        "prompt": prompt,
        "combined_score": combined,
        "flagged": flagged,
        "message": "Likely Unsafe" if flagged else "Safe"
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)