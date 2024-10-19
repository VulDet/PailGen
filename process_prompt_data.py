import pandas as pd
import json
import csv
from tree_sitter import Language, Parser
CS_LANGUAGE = Language('/home/smm/APP/build/my-languages.so', 'c_sharp')
c_parser = Parser()
c_parser.set_language(CS_LANGUAGE)


dataset = 'd2a'
data = pd.read_csv(f"./data/{dataset}/raw/{dataset}_test.csv")
with open(f'./data/{dataset}/raw/{dataset}_matched_templates_top10.json', 'r') as f:
    fix_patterns = json.load(f)

with open(f'./data/{dataset}/raw/{dataset}_similar_codes_top10.json', 'r') as f:
    similar_diff_codes = json.load(f)


for tmp_num in range(1,11):
    my_test_data = pd.DataFrame(columns=['filepath', 'source', 'target', 'ast', 'patch_code', 'template', 'vul_lines', 'similar_diff', 'similar_vul_code', 'similar_patch_code'], dtype=object)
    for i, row in data.iterrows():
        source = row['vul_code']
        target = row['diff_target']
        patch_code = row['patch_code']
        filepath = row['filepath']
        similar_diff = similar_diff_codes[filepath][tmp_num-1][1][0]
        similar_vul_code = similar_diff_codes[filepath][tmp_num-1][1][1]
        similar_patch_code = similar_diff_codes[filepath][tmp_num-1][1][2]

        try:
            fix_template = fix_patterns[filepath]
            fix_template = [temp[1] for temp in fix_template]
            template = fix_template[tmp_num-1]
            template = template.replace('\n', ' ')
            template = ' '.join(template.split())
        except:
            template = ''

        ast_tree = c_parser.parse(bytes(source, 'utf-8'))
        root = ast_tree.root_node
        ast_seq = root.sexp()

        vul_code_lines = target.split('+')[0].replace('-', '')
        series = pd.Series({'filepath': filepath, 'source': source, 'target': target, 'ast': ast_seq, 'patch_code': patch_code,
                            'template': template, 'vul_lines': vul_code_lines, 'similar_diff': similar_diff,
                            'similar_vul_code': similar_vul_code, 'similar_patch_code': similar_patch_code})
        my_test_data = my_test_data.append(series, ignore_index=True)

    my_test_data.to_csv(f'./data/{dataset}/processed/{dataset}_tem{tmp_num}_test_top10.csv')
print('a')
