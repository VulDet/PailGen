import json
import os
import ast
import re
from graphviz import Digraph
from tqdm import tqdm
from change_tree import ChangeNode, ChangeTree, ChangePair
import traceback
import time
import pandas as pd
from tree_sitter import Language, Parser
CS_LANGUAGE = Language('/home/smm/APP/build/my-languages.so', 'c_sharp')
c_parser = Parser()
c_parser.set_language(CS_LANGUAGE)



MAX_ITERATION = 10000


def copy_context(context):
    if context is None:
        return None
    new_context = Context(context.context_tree, context.relationship, context.type)
    return new_context


def restore_code(node, source_code):
    if len(node.children) == 0:
        # Leaf node, return the original source code slice
        return source_code[node.start_byte:node.end_byte]
    
    # Non-leaf node, recursively restore code for each child
    restored_code = ''
    for child in node.children:
        restored_code += restore_code(child, source_code)
    
    return restored_code


def iter_fields(node):
    """
    Yield a tuple of ``(fieldname, value)`` for each field in ``node._fields``
    that is present on *node*.
    """
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


class ASTCompare(object):
    def __init__(self):
        self.beforeroot = None
        self.afterroot = None

    def build_change_tree(self, root, before, change_lines, raw_change_lines, always_add = False):
        nodes = {}
        change_trees = []
        for l in change_lines:
            for n in root.root_node.children:
                start_line = n.start_point[0] + 1
                end_line = n.end_point[0] + 1
                if l in range(start_line, end_line + 1):
                    if n not in nodes:
                        nodes[n] = []
                    nodes[n].append(l)
        
        raw_nodes = {}
        for l in raw_change_lines:
            for n in root.root_node.children:
                start_line = n.start_point[0] + 1
                end_line = n.end_point[0] + 1
                if l in range(start_line, end_line + 1):
                    if n not in raw_nodes:
                        raw_nodes[n] = []
                    raw_nodes[n].append(l)
        
        for n in nodes:
            c_node = ChangeNode(n, n.start_point[0]+1, n.end_point[0]+1, nodes[n], raw_nodes[n], n.text)
            c_tree = ChangeTree(c_node, before, nodes[n], raw_nodes[n])
            if always_add:
                c_tree.build()
                change_trees.append(c_tree)
            if not always_add and not c_tree.build():
                change_trees.append(c_tree)
        return change_trees


    def compare_change_tree(self, before_trees, after_trees):
        change_status = {'Added': {'Totally': [], 'Partially': []}, 'Removed': {'Totally': [], 'Partially': []}, 'Replaced': {'before': {'Totally': [], 'Partially': []}, 'after': {'Totally': [], 'Partially': []}}, 'order': {'before': [], 'after': []}}
        if len(before_trees) == 0 and len(after_trees) == 0:
            raise ValueError('Change trees before and after the commit are both empty.')
        linemap = {}
        if len(before_trees) == 0:
            linemap = {}
            for a in after_trees:
                for s in a.uppest_totally_changed_stmts:
                    s.set_status('Added')
                    s.set_status_for_childrens('Added')
                    s.set_status_for_parent('Added_Parent')
                    change_status['Added']['Totally'].append(s)
                    if s.lineno not in linemap:
                        linemap[s.lineno] = ['Totally-{}'.format(len(change_status['Added']['Totally']) - 1)]
                    else:
                        linemap[s.lineno].append('Totally-{}'.format(len(change_status['Added']['Totally']) - 1))
                for s in a.deepest_partially_changed_stmts:
                    s.set_status('Added_Parent')
                    s.set_status_for_parent('Added_Parent')
                    change_status['Added']['Partially'].append(s)
                    if s.lineno not in linemap:
                        linemap[s.lineno] = ['Partially-{}'.format(len(change_status['Added']['Partially']) - 1)]
                    else:
                        linemap[s.lineno].append('Partially-{}'.format(len(change_status['Added']['Partially']) - 1))
            orders = sorted(linemap.items(), key = lambda item:item[0])
            for line, loc in orders:
                change_status['order']['after'] += loc

        elif len(after_trees) == 0:
            linemap = {}
            for b in before_trees:
                for s in b.uppest_totally_changed_stmts:
                    s.set_status('Removed')
                    s.set_status_for_childrens('Removed')
                    s.set_status_for_parent('Removed_Parent')
                    change_status['Removed']['Totally'].append(s)
                    if s.lineno not in linemap:
                        linemap[s.lineno] = ['Totally-{}'.format(len(change_status['Removed']['Totally']) - 1)]
                    else:
                        linemap[s.lineno].append('Totally-{}'.format(len(change_status['Removed']['Totally']) - 1))
                for s in b.deepest_partially_changed_stmts:
                    s.set_status('Removed_Parent')
                    s.set_status_for_parent('Removed_Parent')
                    change_status['Removed']['Partially'].append(s)
                    if s.lineno not in linemap:
                        linemap[s.lineno] = ['Partially-{}'.format(len(change_status['Removed']['Partially']) - 1)]
                    else:
                        linemap[s.lineno].append('Partially-{}'.format(len(change_status['Removed']['Partially']) - 1))
            orders = sorted(linemap.items(), key = lambda item:item[0])
            for line, loc in orders:
                change_status['order']['before'] += loc
        
        else:
            linemap = {}
            for b in before_trees:
                for s in b.uppest_totally_changed_stmts:
                    s.set_status('Replaced')
                    s.set_status_for_childrens('Replaced')
                    s.set_status_for_parent('Replaced_Parent')
                    change_status['Replaced']['before']['Totally'].append(s)
                    if s.lineno not in linemap:
                        linemap[s.lineno] = ['Totally-{}'.format(len(change_status['Replaced']['before']['Totally']) - 1)]
                    else:
                        linemap[s.lineno].append('Totally-{}'.format(len(change_status['Replaced']['before']['Totally']) - 1))
                for s in b.deepest_partially_changed_stmts:
                    s.set_status('Replaced_Parent')
                    s.set_status_for_parent('Replaced_Parent')
                    change_status['Replaced']['before']['Partially'].append(s)
                    if s.lineno not in linemap:
                        linemap[s.lineno] = ['Partially-{}'.format(len(change_status['Replaced']['before']['Partially']) - 1)]
                    else:
                        linemap[s.lineno].append('Partially-{}'.format(len(change_status['Replaced']['before']['Partially']) - 1))
            orders = sorted(linemap.items(), key = lambda item:item[0])
            for line, loc in orders:
                change_status['order']['before'] += loc
            linemap = {}
            for a in after_trees:
                for s in a.uppest_totally_changed_stmts:
                    s.set_status('Replaced')
                    s.set_status_for_childrens('Replaced')
                    s.set_status_for_parent('Replaced_Parent')
                    change_status['Replaced']['after']['Totally'].append(s)
                    if s.lineno not in linemap:
                        linemap[s.lineno] = ['Totally-{}'.format(len(change_status['Replaced']['after']['Totally']) - 1)]
                    else:
                        linemap[s.lineno].append('Totally-{}'.format(len(change_status['Replaced']['after']['Totally']) - 1))
                for s in a.deepest_partially_changed_stmts:
                    s.set_status('Replaced_Parent')
                    s.set_status_for_parent('Replaced_Parent')
                    change_status['Replaced']['after']['Partially'].append(s)
                    if s.lineno not in linemap:
                        linemap[s.lineno] = ['Partially-{}'.format(len(change_status['Replaced']['after']['Partially']) - 1)]
                    else:
                        linemap[s.lineno].append('Partially-{}'.format(len(change_status['Replaced']['after']['Partially']) - 1))
            orders = sorted(linemap.items(), key = lambda item:item[0])
            for line, loc in orders:
                change_status['order']['after'] += loc
            if len(change_status['Replaced']['before']['Partially']) != len(change_status['Replaced']['after']['Partially']):
                print('Inconsistent number of partially changed statements before ({}) and after ({}) the commit'.format(len(change_status['Replaced']['before']['Partially']), len(change_status['Replaced']['after']['Partially'])))
        return ChangePair(before_trees, after_trees, change_status)


    def compare_loc(self, before_change_lines, raw_before_change_lines, after_change_lines, raw_after_change_lines):
        if self.beforeroot:
            before_trees = self.build_change_tree(self.beforeroot, True, before_change_lines, raw_before_change_lines)  # 从AST中找出更改语句所在的子树
        else:
            before_trees = []
        if self.afterroot:
            after_trees = self.build_change_tree(self.afterroot, False, after_change_lines, raw_after_change_lines)
        else:
            after_trees = []

        if len(before_trees) == 0 and len(after_trees) == 0:
            # logger.warning('Empty commit, skipped.')
            return None

        return self.compare_change_tree(before_trees, after_trees)


    def generate_diff_code(self, vul_code, patch_code, vul_lines, patch_lines):
        pre_statements = vul_code.split('\n')
        post_statements = patch_code.split('\n')
        change_statements = []
        for i in vul_lines:
            st = pre_statements[i - 1].strip('\t').strip()
            st = ' '.join(st.split())
            if st.startswith('/*') or st.endswith('*/'):
                continue
            change_statements.append('-' + ' ' + st)

        for j in patch_lines:
            st = post_statements[j - 1].strip('\t').strip()
            st = ' '.join(st.split())
            if st.startswith('/*') or st.endswith('*/'):
                continue
            change_statements.append('+' + ' ' + st)
        target_diff = '\n'.join(change_statements)

        return target_diff


    def compare_funcs(self, datafile):
        change_pairs = {}
        all_node_types = []
        for vul_filepath, content in datafile.items():
            beforefile = content['vul_filepath']
            afterfile = content['patch_filepath']
            beforecode = content['vul_func_code']
            aftercode = content['patch_func_code']
            function_name = content['function_name']

            before_change_lines = content['before_change_lines']
            raw_before_change_lines = content['raw_before_change_lines']
            after_change_lines = content['after_change_lines']
            raw_after_change_lines = content['raw_after_change_lines']
            diff_code = self.generate_diff_code(beforecode, aftercode, before_change_lines, after_change_lines)

            try:
                if beforefile:
                    self.beforeroot = c_parser.parse(bytes(beforecode, "utf8"))
                else:
                    self.beforeroot = None

                if afterfile:
                    self.afterroot = c_parser.parse(bytes(aftercode, "utf8"))
                else:
                    self.afterroot = None

            except Exception as e:
                logger.error(f'Cannot parse the source files, reason:{e}')
                continue

            change_pairs[vul_filepath] = []
            change_pair = self.compare_loc(before_change_lines, raw_before_change_lines, after_change_lines, raw_after_change_lines)
            if change_pair != None:
                change_pairs[vul_filepath].append(change_pair)
                change_pair.metadata = {'project': content['project'], 'vul_func_code': beforecode, 'patch_func_code': aftercode, 'bug_file': content['vul_filepath'], 'diff_code': diff_code,
                                        'function_name': content['function_name']}

        return change_pairs

    


    


        
        
                

                





    