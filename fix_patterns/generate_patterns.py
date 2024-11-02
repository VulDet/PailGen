
import time
import json
from tqdm import tqdm
import pandas as pd
from fix_miner import ASTCompare
from tree_sitter import Language, Parser
CS_LANGUAGE = Language('/home/smm/APP/build/my-languages.so', 'c_sharp')
c_parser = Parser()
c_parser.set_language(CS_LANGUAGE)


def iter_nodes(tree):
    nodes = [tree.node]
    while(len(nodes) > 0):
        node = nodes[0]
        nodes = nodes[1:]
        yield node
        for n in node.children:
            nodes.append(n)


def compare_leaf_path(a, b):
    if len(a) != len(b):
        return False
    for i, na in enumerate(a):
        if type(na) != type(b[i]):
            return False
        elif isinstance(na, TemplateNode):
            if na.value != b[i].value or na.type != b[i].type or na.ast_type != b[i].ast_type:
                return False
        elif na != b[i]:
            return False
    
    return True


def get_leaf_nodes(tree):
        leaf_nodes = []
        for n in iter_nodes(tree):
            if len(n.children) == 0:
                leaf_nodes.append(n)
        
        return leaf_nodes


def get_leaf_paths(tree):
    paths = {}
    leaf_nodes = get_leaf_nodes(tree)
    for n in leaf_nodes:
        cur_node = n
        path = []
        while True:
            path += [cur_node, cur_node.parent.children.index(cur_node)]
            cur_node = cur_node.parent
            if cur_node == tree.node:
                break
        path.append(cur_node)
        paths[n] = path

    return leaf_nodes, paths


def node_compare(a, b):
    if a.type != b.type or a.text != b.text:
        return False
    return True


def compare_leaf_path(a, b):
        if len(a) != len(b):
            return False
        for i, na in enumerate(a):
            if type(na) != type(b[i]):
                return False
            elif isinstance(na, (int, float, complex)):
                if na != b[i]:
                    return False        
            else:
                if na.type != b[i].type:
                    return False
        
        return True


def generate_templates(change_pairs):
    total_templates = {}
    diff_codes = {}
    for r in tqdm(change_pairs, desc = 'Initializing Fix Templates'):
        try:
            templates = []
            for pair in change_pairs[r]:
                if len(pair.status['Added']['Totally']) + len(pair.status['Added']['Partially']) > 0:
                    if len(pair.status['Added']['Totally']) > 0:
                        after_subtrees = pair.status['Added']['Totally']
                    elif len(pair.status['Added']['Partially']) > 0:
                        after_subtrees = pair.status['Added']['Partially']
                    for after_subtree in after_subtrees:
                        after_leaf_nodes, after_leaf_paths = get_leaf_paths(after_subtree)
                        for i, after_leaf_node in enumerate(after_leaf_nodes):
                            after_leaf_path = after_leaf_paths[after_leaf_node][::-1]
                            fix_template = ''
                            after_child = 'child'
                            i = 0
                            while i < len(after_leaf_path):
                                start = '---' * (i//2)
                                after_node = after_leaf_path[i]
                                after_node_value = after_node.text.decode('utf8')
                                after_node_value = after_node_value.replace('\n',' ')
                                after_node_value = ' '.join(after_node_value.split())
                                if i != 0:
                                    after_child += '_' + str(after_leaf_path[i-1])
                                    fix_template = fix_template + ' ' + start + ' ADD ' + after_node.type + '@@' + after_node_value + \
                                    " @TO@ " + parent_node_type + '@@' + parent_node_value + ' @AT@' + after_child
                                else:
                                    after_node_parent_value = after_node.parent.text.decode('utf8')
                                    after_node_parent_value = after_node_parent_value.replace('\n',' ')
                                    after_node_parent_value = ' '.join(after_node_parent_value.split())
                                    fix_template = fix_template + ' ' + start + ' ADD ' + after_node.type + '@@' + after_node_value + \
                                    " @TO@ " + after_node.parent.type + '@@' + after_node_parent_value + ' @AT@root_node'
                                parent_node_type = after_node.type
                                parent_node_value = after_node_value
                                i+=2
                            templates.append(fix_template)

                if len(pair.status['Removed']['Totally']) + len(pair.status['Removed']['Partially']) > 0:
                    if len(pair.status['Removed']['Totally']) > 0:
                        before_subtrees = pair.status['Removed']['Totally']
                    elif len(pair.status['Removed']['Partially']) > 0:
                        before_subtrees = pair.status['Removed']['Partially']
                    for before_subtree in before_subtrees:
                            before_leaf_nodes, before_leaf_paths = get_leaf_paths(before_subtree)
                            for i, before_leaf_node in enumerate(before_leaf_nodes):
                                before_leaf_path = before_leaf_paths[before_leaf_node][::-1]
                                fix_template = ''
                                before_child = 'child'
                                i = 0
                                while i < len(before_leaf_path):
                                    start = '---' * (i//2)
                                    before_node = before_leaf_path[i]
                                    before_node_value = before_node.text.decode('utf8')
                                    before_node_value = before_node_value.replace('\n',' ')
                                    before_node_value = ' '.join(before_node_value.split())
                                    if i != 0:
                                        before_child += '_' + str(before_leaf_path[i-1])
                                        fix_template = fix_template + ' ' + start + ' REMOVE ' + before_node.type + '@@' + before_node_value + \
                                        ' @AT@' + before_child
                                    else:
                                        fix_template = fix_template + ' ' + start + ' REMOVE ' + before_node.type + '@@' + before_node_value + \
                                        ' @AT@root_node'
                                    parent_node_type = before_node.type
                                    parent_node_value = before_node_value
                                    i+=2
                                templates.append(fix_template)
                if len(pair.status['Replaced']['before']['Totally']) + len(pair.status['Replaced']['after']['Totally']) > 0 or \
                len(pair.status['Replaced']['before']['Partially']) + len(pair.status['Replaced']['after']['Partially']) > 0:
                    if len(pair.status['Replaced']['before']['Partially']) != len(pair.status['Replaced']['after']['Partially']) and\
                    len(pair.status['Replaced']['before']['Partially']) > 0 and len(pair.status['Replaced']['after']['Partially']) > 0:
                        continue    
                    if len(pair.status['Replaced']['before']['Partially']) + len(pair.status['Replaced']['after']['Partially']) > 0:
                        before_subtrees = pair.status['Replaced']['before']['Partially']
                        after_subtrees = pair.status['Replaced']['after']['Partially']
                        for i, before_subtree in enumerate(before_subtrees):
                            after_subtree = after_subtrees[i]
                            before_leaf_nodes, before_leaf_paths = get_leaf_paths(before_subtree)
                            after_leaf_nodes, after_leaf_paths = get_leaf_paths(after_subtree)
                            for bn in before_leaf_paths:   
                                for an in after_leaf_paths:
                                    if node_compare(an, bn) and compare_leaf_path(before_leaf_paths[bn], after_leaf_paths[an]):
                                        before_leaf_nodes.remove(bn)
                                        after_leaf_nodes.remove(an)
                            for i, before_leaf_node in enumerate(before_leaf_nodes):
                                after_leaf_node = after_leaf_nodes[i]
                                before_leaf_path = before_leaf_paths[before_leaf_node][::-1]
                                after_leaf_path = after_leaf_paths[after_leaf_node][::-1]
                                fix_template = ''
                                before_child = 'child'
                                after_child = 'child'
                                i = 0
                                min_len_path = min(len(before_leaf_path), len(after_leaf_path))
                                while i < min_len_path:
                                    start = '---' * (i//2)
                                    before_node = before_leaf_path[i]
                                    after_node = after_leaf_path[i]
                                    before_node_value = before_node.text.decode('utf8')
                                    before_node_value = before_node_value.replace('\n',' ')
                                    before_node_value = ' '.join(before_node_value.split())
                                    after_node_value = after_node.text.decode('utf8')
                                    after_node_value = after_node_value.replace('\n',' ')
                                    after_node_value = ' '.join(after_node_value.split())
                                    if i != 0:
                                        before_child += '_' + str(before_leaf_path[i-1])
                                        after_child += '_' + str(before_leaf_path[i-1])
                                        if before_node.type == after_node.type:
                                            if before_child == after_child:
                                                fix_template = fix_template + ' ' + start + ' UPDATE ' + before_node.type + '@@' + before_node_value + \
                                                " @TO@ " + after_node_value + ' @AT@' + before_child
                                            else:
                                                fix_template = fix_template + ' '+ start + ' REPLACE ' + after_node.type + '@@' + after_node_value + \
                                                " @TO@ " + parent_node_type + '@@' + parent_node_value + ' @AT@' + after_child
                                        else:
                                            fix_template = fix_template + ' ' + start + ' REPLACE ' + after_node.type + '@@' + after_node_value + \
                                            " @TO@ " + parent_node_type + '@@' + parent_node_value + ' @AT@' + after_child
                                    else:
                                        if before_node.type == after_node.type:
                                            fix_template = fix_template + ' ' + start + ' UPDATE ' + before_node.type + '@@' + before_node_value + \
                                            " @TO@ " + after_node_value  + ' @AT@root_node'
                                        else:
                                            after_node_parent_value = after_node.parent.text.decode('utf8')
                                            after_node_parent_value = after_node_parent_value.replace('\n',' ')
                                            after_node_parent_value = ' '.join(after_node_parent_value.split())
                                            fix_template = fix_template + ' ' + start + ' REPLACE ' + after_node.type + '@@' + after_node_value + \
                                            " @TO@ " + after_node.parent.type + '@@' + after_node_parent_value + ' @AT@root_node'    # + ' @AT@' + after_child
                                        parent_node_type = after_node.type
                                        parent_node_value = after_node_value
                                    i+=2
                                templates.append(fix_template)
                    elif len(pair.status['Replaced']['before']['Totally']) + len(pair.status['Replaced']['after']['Totally']) > 0:
                        if len(pair.status['Replaced']['before']['Totally']) > 0:
                            before_subtrees = pair.status['Replaced']['before']['Totally']
                            for before_subtree in before_subtrees:
                                before_leaf_nodes, before_leaf_paths = get_leaf_paths(before_subtree)
                                for i, before_leaf_node in enumerate(before_leaf_nodes):
                                    before_leaf_path = before_leaf_paths[before_leaf_node][::-1]
                                    fix_template = ''
                                    before_child = 'child'
                                    i = 0
                                    while i < len(before_leaf_path):
                                        start = '---' * (i//2)
                                        before_node = before_leaf_path[i]
                                        before_node_value = before_node.text.decode('utf8')
                                        before_node_value = before_node_value.replace('\n',' ')
                                        before_node_value = ' '.join(before_node_value.split())
                                        if i != 0:
                                            before_child += '_' + str(before_leaf_path[i-1])
                                            fix_template = fix_template + ' ' + start + ' REMOVE ' + before_node.type + '@@' + before_node_value + \
                                            ' @AT@' + before_child
                                        else:
                                            fix_template = fix_template + ' ' + start + ' REMOVE ' + before_node.type + '@@' + before_node_value + \
                                            ' @AT@root_node'
                                        parent_node_type = before_node.type
                                        parent_node_value = before_node_value
                                        i+=2
                                    templates.append(fix_template)
                        if len(pair.status['Replaced']['after']['Totally']) > 0:
                            after_subtrees = pair.status['Replaced']['after']['Totally']
                            for after_subtree in after_subtrees:
                                after_leaf_nodes, after_leaf_paths = get_leaf_paths(after_subtree)
                                for i, after_leaf_node in enumerate(after_leaf_nodes):
                                    after_leaf_path = after_leaf_paths[after_leaf_node][::-1]
                                    fix_template = ''
                                    after_child = 'child'
                                    i = 0
                                    while i < len(after_leaf_path):
                                        start = '---' * (i//2)
                                        after_node = after_leaf_path[i]
                                        after_node_value = after_node.text.decode('utf8')
                                        after_node_value = after_node_value.replace('\n',' ')
                                        after_node_value = ' '.join(after_node_value.split())
                                        if i != 0:
                                            after_child += '_' + str(after_leaf_path[i-1])
                                            fix_template = fix_template + ' ' + start + ' ADD ' + after_node.type + '@@' + after_node_value + \
                                            " @TO@ " + parent_node_type + '@@' + parent_node_value + ' @AT@' + after_child
                                        else:
                                            after_node_parent_value = after_node.parent.text.decode('utf8')
                                            after_node_parent_value = after_node_parent_value.replace('\n',' ')
                                            after_node_parent_value = ' '.join(after_node_parent_value.split())
                                            fix_template = fix_template + ' ' + start + ' ADD ' + after_node.type + '@@' + after_node_value + \
                                            " @TO@ " + after_node.parent.type + '@@' + after_node_parent_value + ' @AT@root_node'     # + ' @AT@' + before_child
                                        parent_node_type = after_node.type
                                        parent_node_value = after_node_value
                                        i+=2
                                    templates.append(fix_template)
                templates = '\n'.join(templates)
                if len(templates) == 0:
                    continue
                total_templates[r] = templates
                diff_codes[r] = [pair.metadata['diff_code'], pair.metadata['vul_func_code'], pair.metadata['patch_func_code']]

        except:
            continue

    return total_templates, diff_codes


def main():
    dataset = 'd2a'
    corpus = {}
    with open(f'../data/{dataset}/raw/{dataset}_train.jsonl', mode='r') as f:
        for line in f:
            row_data = json.loads(line.strip())
            filepath_func = row_data['filepath_func']
            corpus[filepath_func] = row_data
    
    targets = {}
    with open(f'../data/{dataset}/raw/{dataset}_test.jsonl', mode='r') as f:
        for line in f:
            row_data = json.loads(line.strip())
            filepath_func = row_data['filepath_func']
            targets[filepath_func] = row_data

    with open(f'../data/{dataset}/raw/retrieved_results_{dataset}_top50.json', 'r') as f:
        retrived_data = json.load(f)

    matched_templates = {}
    similar_diff_codes = {}
    for i, content in enumerate(retrived_data):
        target_id = content['target_ids']
        try:
            target_dict = targets[target_id]
        except:
            continue
        target_vul_code = target_dict['vul_func_code']
        bug_lines = target_dict['bug_lines']
        added = target_dict['added']
        filepath_f = target_dict['filepath_func']

        retrieved_funcid = []
        function_names = []
        filtered_corpus = {}
        for item in content['ctxs']:
            funcid = item['id']
            funcname = item['id'].split('/')[-1]
            retrieved_funcid.append(funcid)
            function_names.append(funcname)
            try:
                filtered_corpus[funcid] = corpus[funcid]
            except:
                continue
        start = time.time()
        a = ASTCompare()

        change_pairs = a.compare_funcs(filtered_corpus)
        templates, diff_codes = generate_templates(change_pairs)

        matched_templates[filepath_f] = list(templates.items())[:10]
        similar_diff_codes[filepath_f] = list(diff_codes.items())[:10]
        end = time.time()
        print('Template mining finished, cost {} seconds.'.format(end - start))


    with open(f'../data/{dataset}/raw/{dataset}_matched_templates_top10.json', 'w') as f:
        json.dump(matched_templates, f)
    with open(f'../data/{dataset}/raw/{dataset}_similar_codes_top10.json', 'w') as f:
        json.dump(similar_diff_codes, f)

if __name__ == "__main__":
    main()