import pandas as pd
from tqdm import tqdm
import regex
import string
import json
from codebleu import calc_codebleu
import random

def clean_tokens(tokens):
    tokens = tokens.replace("<pad>", "")
    tokens = tokens.replace("<s>", "")
    tokens = tokens.replace("</s>", "")
    tokens = tokens.strip("\n")
    tokens = tokens.strip()
    return tokens

def normalize_answer(s):
    def remove_articles(text):
        return regex.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))

def exact_match_score(prediction, ground_truth):
    normal_prediction = normalize_answer(prediction)
    normal_groundtruth = normalize_answer(ground_truth)
    if normal_groundtruth == normal_prediction:
        return True
    return False

def ems(prediction, ground_truth):
    return exact_match_score(prediction, ground_truth)



dataset = "d2a"  # bigvul_cvefixes
model = 'DeepSeekCoder'  # DeepSeekCoder chatgpt  CodeLlama  codegeex4_7b

source_file1 = f"./data/{dataset}/prediction_result/{dataset}_{model}_tem1.csv"  #  chatgpt  DeepSeekCoder
source_file2 = f"./data/{dataset}/prediction_result/{dataset}_{model}_tem2.csv"
source_file3 = f"./data/{dataset}/prediction_result/{dataset}_{model}_tem3.csv"
source_file4 = f"./data/{dataset}/prediction_result/{dataset}_{model}_tem4.csv"
source_file5 = f"./data/{dataset}/prediction_result/{dataset}_{model}_tem5.csv"
source_file6 = f"./data/{dataset}/prediction_result/{dataset}_{model}_tem6.csv"
source_file7 = f"./data/{dataset}/prediction_result/{dataset}_{model}_tem7.csv"
source_file8 = f"./data/{dataset}/prediction_result/{dataset}_{model}_tem8.csv"
source_file9 = f"./data/{dataset}/prediction_result/{dataset}_{model}_tem9.csv"
source_file10 = f"./data/{dataset}/prediction_result/{dataset}_{model}_tem10.csv"


data_1 = pd.read_csv(source_file1)
data_2 = pd.read_csv(source_file2)
data_3 = pd.read_csv(source_file3)
data_4 = pd.read_csv(source_file4)
data_5 = pd.read_csv(source_file5)
data_6 = pd.read_csv(source_file6)
data_7 = pd.read_csv(source_file7)
data_8 = pd.read_csv(source_file8)
data_9 = pd.read_csv(source_file9)
data_10 = pd.read_csv(source_file10)


accuracy = []
ground_truths = []
raw_predictions = []
out_filepaths = []
responses = []
for i in tqdm(range(len(data_1["ground_truths"]))):
    filepath = data_1["out_filepaths"][i]
    ground_truth = str(data_1["ground_truths"][i])
    response = str(data_1["responses"][i])
    pred_diff = str(data_1["raw_predictions"][i])
    correct_pred = False
    for data_f in [data_1, data_2, data_3, data_4, data_5, data_6, data_7, data_8, data_9, data_10]:
        prediction_result = data_f["correctly_predicted"][i]
        if prediction_result == 1:
            pred_diff = str(data_f["raw_predictions"][i])
            correct_pred = True
            break
    if correct_pred:
        accuracy.append(1)
    else:
        accuracy.append(0)
    if pred_diff == 'nan':
        pred_diff = response

    ground_truths.append(ground_truth)
    raw_predictions.append(pred_diff)
    out_filepaths.append(filepath)
    responses.append(response)



result = calc_codebleu(ground_truths, raw_predictions, lang="c", weights=(0.25, 0.25, 0.25, 0.25), tokenizer=None)
print(result)
# calculate accuracy
test_result = round(sum(accuracy) / len(accuracy), 4)
print("Accuracy: " + str(test_result))

df = pd.DataFrame({"filepaths":[], "ground_truths": [], "raw_predictions": [], "correctly_predicted": [], "responses": []})
df["filepaths"] = out_filepaths
df["ground_truths"] = ground_truths
df["raw_predictions"] = raw_predictions
df["correctly_predicted"] = accuracy
df["responses"] = responses
df.to_csv(f"./data/{dataset}/prediction_result/{dataset}_{model}_combined_prediction.csv")