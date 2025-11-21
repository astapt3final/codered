# toxicity_check.py
from transformers import AutoTokenizer
from optimum.onnxruntime import ORTModelForSequenceClassification
import numpy as np

MODEL_ID = "gravitee-io/bert-small-toxicity"  # small, fast toxicity model

# load once when module imported
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
# Optimum will look for ONNX files in the repo (quantized if available)
model = ORTModelForSequenceClassification.from_pretrained(MODEL_ID, file_name="model.quant.onnx")

def _probs_to_score(probs):
    # probs shape: (1, num_labels). We'll treat index 1 as 'toxic' probability if present.
    toxic_prob = float(probs[0][1]) if probs.shape[1] > 1 else float(probs[0][0])
    return round(toxic_prob * 100, 2)

def modelCheck(prompt, threshold=50):
    """
    Input: prompt (str)
    Returns: {"score": 0-100 float, "flagged": bool}
    """
    if not isinstance(prompt, str):
        prompt = str(prompt)

    # tokenize (fast, truncated)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, padding=True, max_length=128)
    outputs = model(**inputs)
    logits = outputs.logits.detach().cpu().numpy()

    # convert logits -> probs
    if logits.shape[1] == 1:
        # single logit -> sigmoid
        probs = 1 / (1 + np.exp(-logits))
        probs = np.concatenate([1-probs, probs], axis=1)  # [not-toxic, toxic]
    else:
        exps = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        probs = exps / np.sum(exps, axis=1, keepdims=True)

    score = _probs_to_score(probs)
    flagged = score >= threshold
    return {"score": score, "flagged": bool(flagged)}
