from openai import OpenAI
import pandas as pd
from tqdm import tqdm
import regex
import string
import json
from codebleu import calc_codebleu
client = OpenAI(api_key="xxx", base_url="https://api.deepseek.com")


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


tem = 'tem1'
dataset = 'bigvul_cvefixes'
source_file = f"./data/{dataset}/processed/{dataset}_{tem}_test_top10.csv"
print(source_file)
data = pd.read_csv(source_file)

sources = data["source"]
labels = data["target"]
filepaths = data["filepath"]
templates = data["template"]
asts = data['ast']
vul_lines = data['vul_lines']
similar_diff_codes = data['similar_diff']
similar_patches = data['similar_patch_code']

prompt_base = "### Vulnerable code: {code} ### Task: The code contains a vulnerability. Note that <S2SV_StartVul> and <S2SV_EndVul> indicate the start and the end of vulnerable code lines. Thus the vulnerable code lines are: {vul_line}. Please generate a diff to fix the vulnerability."
prompt_augment = "### Vulnerable code: {code} ### The Abstract Syntax Tree (AST) of the code is: {ast}. ### Task: The code contains a vulnerability. Note that <S2SV_StartVul> and <S2SV_EndVul> indicate the start and the end of vulnerable code lines. Thus the vulnerable code lines are: {vul_line}. Please generate a diff to fix the vulnerability. Here is an example of relevant patches: {relevant_patch} and the fix template generated from the AST of relevant vulnerability-fix pair: {fix_template}."
prompt = prompt_augment
print(prompt)

accuracy = []
raw_predictions = []
ground_truths = []
out_filepaths = []
responses = []
for i in tqdm(range(len(sources))):
    vul_code = sources[i]
    patch_code = labels[i]
    template = templates[i]
    filepath = filepaths[i]
    ast = asts[i]
    vul_code = vul_code.replace('\n',' ')
    vul_code = ' '.join(vul_code.split())

    vul_line = vul_lines[i]
    patch_code = patch_code.replace('\n',' ')
    patch_code = ' '.join(patch_code.split())
    patch_code = clean_tokens(patch_code)

    relevant_patch = similar_diff_codes[i]

    new_vul_code = prompt.format(code=vul_code, ast=ast, vul_line=vul_line, relevant_patch=relevant_patch, fix_template=template)
    messages = [
                {'role':'system', 
                 'content': 'You are a helpful assistant'},
                {
                'role': 'user',
                'content': new_vul_code},
               ]

    try:
        response = client.chat.completions.create(model="deepseek-coder", messages=messages, stream=False)
        prediction = response.choices[0].message.content
        responses.append(prediction)

        if "Here is the diff" in prediction:
            prediction = prediction.split("Here is the diff")[1]
        elif "Here's the diff" in prediction:
            prediction = prediction.split("Here's the diff")[1]
        elif "here's the diff" in prediction:
            prediction = prediction.split("here's the diff")[1]
        elif "here is the diff" in prediction:
            prediction = prediction.split("here is the diff")[1]
        elif "Here is a diff" in prediction:
            prediction = prediction.split("Here is a diff")[1]
        elif "Here's a diff" in prediction:
            prediction = prediction.split("Here's a diff")[1]
        elif "here's a diff" in prediction:
            prediction = prediction.split("here's a diff")[1]
        elif "here is a diff" in prediction:
            prediction = prediction.split("here is a diff")[1]
        else:
            prediction = prediction

        try:
            prediction = prediction.split("```")[1]
        except:
            prediction = prediction

        prediction = prediction.split("diff")[-1]
        prediction_result = prediction.split('\n')
        new_prediction = []
        for res in prediction_result:
            res = res.strip()
            if res.startswith('-') and not res.startswith('---') and not res.endswith('.c') and not res.endswith('.h>') and "#include" not in res:
                res = res.strip('-').strip()
                if res.startswith('//') or res.startswith('*') or res.endswith('*/'):
                    continue
                elif '//' in res:
                    res = res.split('//')[0]
                res = '-' + ' ' + res
                new_prediction.append(res)
        for res in prediction_result:
            res = res.strip()
            if res.startswith('+') and not res.startswith('+++') and not res.endswith('.c') and not res.endswith('.h>') and "#include" not in res:
                res = res.strip('+').strip()
                if res.startswith('//') or res.startswith('*') or res.endswith('*/'):
                    continue
                elif '//' in res:
                    res = res.split('//')[0]
                res = '+' + ' ' + res
                new_prediction.append(res)

        new_prediction = ' '.join(new_prediction)
        new_prediction = new_prediction.replace('<S2SV_StartVul>', '').replace('<S2SV_EndVul>', '')
        new_prediction = ' '.join(new_prediction.split())
        new_prediction = clean_tokens(new_prediction)
        # print(new_prediction)
        ground_truth = patch_code
        result = ems(new_prediction, ground_truth)
        if result:
            accuracy.append(1)
            print("True")
        else:
            accuracy.append(0)
        raw_predictions.append(new_prediction)
        ground_truths.append(ground_truth)
        out_filepaths.append(filepath)

    except:
        accuracy.append(0)
        raw_predictions.append('')
        ground_truths.append(patch_code)
        out_filepaths.append(filepath)
        responses.append('')


# write prediction to file
df = pd.DataFrame({"out_filepaths":[], "ground_truths": [], "raw_predictions": [], "correctly_predicted": [], "responses": []})
df["out_filepaths"] = out_filepaths
df["ground_truths"] = ground_truths
df["raw_predictions"] = raw_predictions
df["correctly_predicted"] = accuracy
df["responses"] = responses

out_file = f"./data/{dataset}/prediction_result/{dataset}_DeepSeekCoder_{tem}.csv"
print(out_file)
df.to_csv(out_file)

print(prompt)