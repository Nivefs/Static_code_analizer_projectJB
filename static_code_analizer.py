import argparse
import os
import re
import ast

parser = argparse.ArgumentParser()
parser.add_argument('path', type=str)
args = parser.parse_args()


def check_path():
    global level
    global multi_file
    if args.path[-3:] == '.py':
        for line in open(args.path, 'r'):
            yield line, f'{args.path}:', open(args.path).read()
        return

    multi_file = True
    python_files = [entry.name for entry in os.scandir(args.path) if entry.name[-3:] == '.py']
    # python_files.remove('tests.py')
    for file in python_files:
        global check_def_err

        level = 1
        for line in open(rf'{args.path}\{file}', 'r'):
            yield line, rf'{args.path}\{file}:', open(rf'{args.path}\{file}').read()
        if global_errors:
            for err in global_errors:
                print(err)
            global_errors.clear()
        check_def_err = False


def too_long_err():
    errors.append(f'Line {level}: S001 Too long')


def indent_err():
    indent = 0
    for letter in lines:
        if letter != ' ':
            break
        indent += 1
    if indent % 4 != 0:
        errors.append(f'Line {level}: S002 Indentation is not a multiple of four')


def extra_semicolon_err():
    semi_colon_re = False
    in_qoutes = False
    for letter in lines:
        if letter == '#':
            break
        if letter == "'":
            if in_qoutes == True:
                in_qoutes = False
            else:
                in_qoutes = True
        if letter == ';':
            if not in_qoutes and not semi_colon_re:
                errors.append(f'Line {level}: S003 Unnecessary semicolon')
                semi_colon_re = True


def todo_err():
    if 'todo' in lines[lines.find('#'):].lower():
        errors.append(f'Line {level}: S005 TODO found')


def err_post_coment():
    if lines.startswith('#'):
        return
    count_space = 0
    str_pre_hash = lines[:lines.find('#')][::-1]
    for letter in str_pre_hash:
        if letter != ' ':
            break
        count_space += 1
    if count_space < 2:
        errors.append(f'Line {level}: S004 At least two spaces required before inline comments')


def sort_func(elem):
    number = re.search(r'[0-9]+', re.search(r'S00?[0-9]+', elem).group()).group()
    zero_count = 0
    for x in number:
        if x != '0':
            break
        zero_count += 1
    return int(number[zero_count:])


def sort_by_line(elem):
    number = re.search(r'[0-9]+', re.search(r'Line [0-9]+', elem).group()).group()
    return int(number)


class FunctionErr(ast.NodeVisitor):
    def visit_FunctionDef(self, node):

        for sn_arg in node.args.args:
            if arg_match := re.match(re_snake_for_def, sn_arg.arg):
                errors.append(f'Line {node.lineno}: S010 Argument name \'{arg_match.group()}\' should be snake_case')

        for section in node.body:
            name_errors = []
            if isinstance(section, ast.Assign):
                if isinstance(section.targets[0], ast.Attribute):
                    if name_match := re.match(re_snake_for_def, section.targets[0].attr):
                        if name_match.group() not in name_errors:
                            errors.append(
                                f'Line {section.targets[0].lineno}: S011 Varible \'{name_match.group()}\' in function should be snake_case')
                            name_errors.append(name_match.group())

                else:
                    if name_match := re.match(re_snake_for_def, section.targets[0].id):
                        if name_match.group() not in name_errors:
                            errors.append(
                                f'Line {section.targets[0].lineno}: S011 Varible \'{name_match.group()}\' in function should be snake_case')
                            name_errors.append(name_match.group())

        for default_arg in node.args.defaults:
            if isinstance(default_arg, (ast.Set, ast.List, ast.Dict)):
                errors.append(f'Line {node.lineno}: S012 Default argument is mutable')


level = 1
multi_file = False
start_file_n = True
count_n = 0
errors = []
global_errors = []
check_def_err = False
count_iter = 0
space_err = ''
indent_active = False
re_snake_for_def = r'(?P<function>[A-Z]*[a-z]+[A-Z]|[A-Z][a-z]+)'
re_snake = r'def (?P<function>[A-Z][a-z]+[A-Z1-9a-z]*)'
re_camel2 = r'class [a-z]+|class [a-z]+[_a-z]+:$|class [A-Z]?[a-z]+[_][A-Za-z_]*'
for lines, path, file in check_path():
    strip_line = lines.strip()
    temp_line = lines
    if len(lines) > 79:
        too_long_err()

    if not lines.startswith(' '):
        indent_active = False

    if lines.startswith(' '):
        indent_err()

    if ';' in lines:
        extra_semicolon_err()

    if '#' in lines:
        err_post_coment()
        todo_err()

    if '\n' in lines:
        if not lines.startswith('\n'):
            start_file_n = False
            count_n = 0
        if lines.startswith('\n') and start_file_n == False:
            count_n += 1
        if count_n > 2:
            space_err = f'Line {level + 1}: S006 More than two blank lines used before this line'
    if strip_line.startswith('def'):
        if m := re.match(r'def[ ]{2,}', strip_line):
            errors.append(f'Line {level}: S007 Too many spaces after def')
        if m := re.match(re_snake, strip_line):
            errors.append(f"Line {level}: S009 Function name '{m.group('function')}' should use snake_case")
    if strip_line.startswith('class'):
        if m := re.match(re_camel2, strip_line):
            errors.append(
                f"Line {level}: S008 Class name '{m.group().replace('class ', '')}' should be written in CamelCase")
        if m := re.match(r'class[ ]{2,}', strip_line):
            errors.append(f'Line {level}: S007 Too many spaces after class')

    if space_err:
        count_iter += 1

    if count_iter > 1 and not lines.startswith('\n'):
        errors.append(space_err)
        count_iter = 0
        space_err = ''
    # print(space_err, level)
    if not check_def_err:
        tree = ast.parse(file)
        FunctionErr().visit(tree)
        check_def_err = True

    if errors:

        sorted_errors = sorted(errors, key=sort_func)
        for err in sorted_errors:
            # print(path, err)
            global_errors.append(path + ' ' + err)
        # print(sorted_errors)
        errors.clear()
        sorted_errors.clear()
    level += 1

if not multi_file:

    for errors in sorted(global_errors, key=sort_by_line):
        print(errors)
