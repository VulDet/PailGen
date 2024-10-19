import os
import sys
import random
import pandas as pd
import csv
import re
import itertools
import difflib
import codecs
import math
import subprocess
import clang.cindex
from pathlib import Path
from clang.cindex import CursorKind
from multiprocessing import Pool
from unidiff import PatchSet
import traceback
import json


def read_my_data(src_file, tgt_file):
    src_list = []
    tgt_list = []
    
    # Read all data as they are.
    with open(src_file) as f:
        src_list.extend(f.read().splitlines())
    with open(tgt_file) as f:
        tgt_list.extend(f.read().splitlines())

    assert len(src_list) == len(tgt_list)

    # Remove instances where the src or tgt is whitespace only.
    src_nonempty_list = []
    tgt_nonempty_list = []
    for src, tgt in zip(src_list, tgt_list):
        if src.strip() and tgt.strip():
            src_nonempty_list.append(src)
            tgt_nonempty_list.append(tgt)

    return src_nonempty_list, tgt_nonempty_list


def remove_duplicate(src_list, tgt_list, full_tgt_list, filepath_list):
    src_unique_list = []
    tgt_unique_list = []
    full_tgt_unique_list = []
    filepath_unique_list = []
    unique_pairs = set()

    for src, tgt, full_tgt, filepath in zip(src_list, tgt_list, full_tgt_list, filepath_list):
        if (src, tgt) not in unique_pairs:
            unique_pairs.add((src, tgt))
            src_unique_list.append(src)
            tgt_unique_list.append(tgt)
            full_tgt_unique_list.append(full_tgt)
            filepath_unique_list.append(filepath)
        
    return src_unique_list, tgt_unique_list, full_tgt_unique_list, filepath_unique_list


def remove_long_sequence(src_list, tgt_list, full_tgt_list, filepath_list, max_length_src, max_length_tgt):
    src_suitable_list = []
    tgt_suitable_list = []
    full_tgt_suitable_list = []
    filepath_suitable_list = []

    for src, tgt, full_tgt, filepath in zip(src_list, tgt_list, full_tgt_list, filepath_list):
        if len(src.split(' ')) <= max_length_src and len(tgt.split(' ')) <= max_length_tgt:
            src_suitable_list.append(src)
            tgt_suitable_list.append(tgt)
            full_tgt_suitable_list.append(full_tgt)
            filepath_suitable_list.append(filepath)

    return src_suitable_list, tgt_suitable_list, full_tgt_suitable_list, filepath_suitable_list


def random_split(dataset, src_list, tgt_list, full_tgt_list, filepath_list, output_dir):
    triples = list(zip(src_list, tgt_list, full_tgt_list, filepath_list))
    random.shuffle(triples)
    src_list, tgt_list, full_tgt_list, filepath_list = zip(*triples)

    num_examples = len(src_list)
    max_train_index = math.floor(0.8 * num_examples)

    my_train_data = [['filepath', 'vul_code', 'diff_target', 'patch_code']]
    for i, source in enumerate(src_list[:max_train_index]):
        target = tgt_list[:max_train_index][i]
        filepath = filepath_list[:max_train_index][i]
        full_target = full_tgt_list[:max_train_index][i]
        my_train_data.append([filepath, source, target, full_target])
    
    with open(output_dir + f'{dataset}_train.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        for row in my_train_data:
            writer.writerow(row)

    my_test_data = [['filepath', 'vul_code', 'diff_target', 'patch_code']]
    for i, source in enumerate(src_list[max_train_index:]):
        target = tgt_list[max_train_index:][i]
        filepath = filepath_list[max_train_index:][i]
        full_target = full_tgt_list[max_train_index:][i]
        my_test_data.append([filepath, source, target, full_target])
    with open(output_dir + f'{dataset}_test.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        for row in my_test_data:
            writer.writerow(row)




src_list=[]
tgt_list=[]
full_tgt_list = []
filepath_list = []
dataset = 'bigvul_cvefixes'
source_data = pd.read_json(open(f'./data/{dataset}/raw/{dataset}_data.json'))
source_data = source_data.drop_duplicates(subset='vul_func_code')
source_data = source_data.drop_duplicates(subset='patch_func_code')

for i, pair in source_data.iterrows():
    print(i)
    vul_filepath = pair['vul_filepath']
    try:
        filepath_func = str(i) + '----' + pair['vul_type'] + '----' + vul_filepath + '----' + pair['function_name']
    except:
        filepath_func = str(i) + '----' + 'None' + '----' + vul_filepath + '----' + pair['function_name']
    
    pre_version_function_str = pair['vul_func_code']
    post_version_function_str = pair['patch_func_code']
    vul_lines = pair['before_change_lines']
    patch_lines = pair['after_change_lines']

    pre_statements = pre_version_function_str.split('\n')
    post_statements = post_version_function_str.split('\n')
    change_statements = []
    for i in vul_lines:
        st = pre_statements[i-1].strip('\t').strip()
        st = ' '.join(st.split())
        if st.startswith('*') or st.endswith('*/'):
            continue
        change_statements.append('-' + ' ' + st)
    if len(change_statements)==0:
        continue

    for j in patch_lines:
        st = post_statements[j-1].strip('\t').strip()
        st = ' '.join(st.split())
        if st.startswith('*') or st.endswith('*/'):
            continue
        change_statements.append('+' + ' ' + st)

    target_diff = '\n'.join(change_statements)

    pre_version_function_str = ''
    for i, st in enumerate(pre_statements):
        if i+1 in vul_lines:
            pre_version_function_str += '<S2SV_StartVul>' + ' ' + st + ' ' + '<S2SV_EndVul>\n'
        else:
            pre_version_function_str += st + '\n'

    if ''.join(pre_version_function_str) == ''.join(post_version_function_str):
        print('The vulnerable code is same as the patched code!')
        continue
    # remove comments
    with codecs.open("/tmp/function_pre.c", 'w', 'utf-8') as f1:
        f1.write(pre_version_function_str)
        f1.close()

    with codecs.open("/tmp/function_post.c", 'w', 'utf-8') as f2:
        f2.write(post_version_function_str)
        f2.close()    
    pre_result = subprocess.run(["gcc", "-fpreprocessed", "-dD", "-E", "-P", "/tmp/function_pre.c"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pre_version_function_str = pre_result.stdout.decode('utf-8')
    post_result = subprocess.run(["gcc", "-fpreprocessed", "-dD", "-E", "-P", "/tmp/function_post.c"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    post_version_function_str = post_result.stdout.decode('utf-8')

    pre_version_function_str = pre_version_function_str.replace('\n',' ')
    post_version_function_str = post_version_function_str.replace('\n',' ')
    pre_version_function_str = ' '.join(pre_version_function_str.split())
    post_version_function_str = ' '.join(post_version_function_str.split())

    if pre_version_function_str == post_version_function_str:
        continue

    if pre_version_function_str.endswith(' '):
        pre_version_function_str=pre_version_function_str[:-1]
    if post_version_function_str.endswith(' '):
        post_version_function_str=post_version_function_str[:-1]

    src_list.append(pre_version_function_str)
    full_tgt_list.append(post_version_function_str)
    tgt_list.append(target_diff)
    filepath_list.append(filepath_func)

output_dir = f'./data/{dataset}/raw/'
src_list, tgt_list, full_tgt_list, filepath_list = remove_duplicate(src_list, tgt_list, full_tgt_list, filepath_list)
src_list, tgt_list, full_tgt_list, filepath_list = remove_long_sequence(src_list, tgt_list, full_tgt_list, filepath_list, 1000, 100)
random_split(dataset, src_list, tgt_list, full_tgt_list, filepath_list, output_dir)
