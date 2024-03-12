import subprocess
import os
import re
import tempfile
from django.conf import settings

def determine_table_type(table_latex_code):
    long_table_threshold = 30  
    wide_table_threshold = 6   

    rows = table_latex_code.split("\\\\")
    max_cols = max(row.count('&') for row in rows) + 1

    if len(rows) > long_table_threshold:
        return "longtable"
    elif max_cols > wide_table_threshold:
        return "wide_table"
    else:
        return "standard"

def extract_and_preserve_at_contents(original_def):
    at_contents = []
    non_at_parts = []
    i = 0
    while i < len(original_def):
        if original_def[i:i+2] == "@{":  # 检测到@{开始
            start = i
            i += 2  # 跳过"@{"
            balance = 1  # 跟踪括号平衡
            while i < len(original_def) and balance > 0:
                if original_def[i] == "{":
                    balance += 1
                elif original_def[i] == "}":
                    balance -= 1
                i += 1
            at_contents.append(original_def[start:i])  # 包括闭合的}
        else:
            start = i
            while i < len(original_def) and not (original_def[i] == "@" and original_def[i+1:i+2] == "{"):
                i += 1
            non_at_parts.append(original_def[start:i])
    
    # 移除空字符串
    non_at_parts = [part for part in non_at_parts if part.strip()]
    return at_contents, non_at_parts


def create_column_definition(original_def, max_cols, table_type, replace_with='X'):
    at_contents, non_at_parts = extract_and_preserve_at_contents(original_def)
    
    # 初始化新的列定义列表
    new_col_defs = []
    # 计算已经存在的列数（考虑到@{}内容不计入列数）
    existing_cols = sum(len(part.replace('|', '')) for part in non_at_parts)

    # 交错重组@{}内容和非@{}内容
    for i, non_at_part in enumerate(non_at_parts):
        new_col_defs.extend(list(non_at_part.replace('|', '')))  # 添加非@{}部分
        
        if i < len(at_contents):
            new_col_defs.append(at_contents[i])  # 添加@{}内容
    
    # 检查是否需要添加额外的列来满足max_cols的要求
    while existing_cols < max_cols:
        if table_type == "wide_table":
            # 对于宽表格，在末尾添加replace_with（通常为'X'）
            new_col_defs.append(replace_with)
        else:
            # 对于其他类型的表格，使用'l'填充剩余的列
            new_col_defs.append('l')
        existing_cols += 1  # 更新现有的列数

    return ''.join(new_col_defs)

 
def create_latex_document(table_environment):
    latex_code = rf'''
    \documentclass[10pt]{{article}}
    \usepackage[a3paper, margin=1in]{{geometry}}
    \usepackage[table,dvipsnames]{{xcolor}}
    \usepackage{{booktabs}}
    \usepackage{{tabularx, makecell, multirow}}
    \usepackage{{graphicx}}
    \usepackage{{array}}
    \usepackage{{longtable}}
    \usepackage{{amsmath}}
    \usepackage{{amssymb}}
    \usepackage{{amsbsy}}
    \pagenumbering{{gobble}}
    \begin{{document}}
    {table_environment}
    \end{{document}}
    '''
    return latex_code

def extract_column_definition_with_indices(latex_code):
    """
    从LaTeX代码中提取列定义及其在字符串中的位置。

    :param latex_code: 包含 LaTeX 表格定义的字符串。
    :return: 列定义字符串及其开始和结束索引的元组。如果未找到，返回None。
    """
    start = latex_code.find(r"\begin{tabular}{")
    if start == -1:
        return None, None, None  # 未找到 \begin{tabular}{
    
    start += len(r"\begin{tabular}{")
    end = start
    balance = 1  # 初始时，我们已经遇到了一个左大括号

    while end < len(latex_code) and balance > 0:
        if latex_code[end] == '{':
            balance += 1
        elif latex_code[end] == '}':
            balance -= 1
        end += 1

    if balance == 0:
        return latex_code[start:end-1], start, end-1  # 返回列定义及其索引范围
    else:
        return None, None, None  # 括号未正确闭合
    
def generate_modified_latex_table_code(original_table_code, max_cols, replace_with='X'):
    """
    根据表格类型替换LaTeX代码中的列定义，并根据需要替换表格的开始和结束标签。

    :param latex_code: 原始的LaTeX代码。
    :param max_cols: 最大列数。
    :param replace_with: 宽表格中用于填充的字符。
    :return: 修改后的LaTeX代码。
    """
    table_type = determine_table_type(original_table_code)
    original_col_def, start_index, end_index = extract_column_definition_with_indices(original_table_code)
    if original_col_def is None:
        return original_table_code  # 如果未找到列定义，返回原始代码

    new_column_definition = create_column_definition(original_col_def, max_cols, table_type, replace_with)
    # 根据表格类型替换表格的开始标签和结束标签
    if table_type == "wide_table":
        start_tag = r"\begin{tabularx}{\textwidth}{"
        end_tag = r"\end{tabularx}"
    elif table_type == "longtable":
        start_tag = r"\begin{longtable}{"
        end_tag = r"\end{longtable}"
    else:  # standard table
        start_tag = r"\begin{tabular}{"
        end_tag = r"\end{tabular}"

    # 构造新的LaTeX代码
    before_start_tag = original_table_code[:start_index-len(r"\begin{tabular}{")]
    after_end_tag = original_table_code[end_index+1:]
    new_latex_code = before_start_tag + start_tag + new_column_definition + "}" + after_end_tag

    # 替换结束标签
    new_latex_code = new_latex_code.replace(r"\end{tabular}", end_tag)

    return new_latex_code

def extract_and_save_all_errors(log_file_path):
    error_pattern = re.compile(r"! .*?^.*?$", re.MULTILINE | re.DOTALL)
    errors = []
    
    with open(log_file_path, 'r',encoding='utf-8') as file:
        log_content = file.read()
    
    error_matches = error_pattern.findall(log_content)
    for error in error_matches:
        errors.append(error.strip())
    
    if not errors:
        return ["无错误"]
    
    return errors


def compile_latex_to_pdf(original_table_code):
    # 生成 LaTeX 文档
    
    temp_dir = os.path.join(settings.BASE_DIR, 'temp')  # 假设你已经在settings.py中定义了BASE_DIR
    os.makedirs(temp_dir, exist_ok=True)

    result = {"success": False, "error": "初始化错误"}  # 默认返回值
    max_cols = max(row.count('&') for row in original_table_code.split("\\\\")) + 1
    modified_latex_code = generate_modified_latex_table_code(original_table_code, max_cols)
    latex_document = create_latex_document(modified_latex_code)

    # original_col_def_match = re.search(r"\\begin{tabular}{(.*?)}", original_table_code)
    # original_col_def = original_col_def_match.group(1)
    # table_type = determine_table_type(original_table_code)
    # max_cols = max(row.count('&') for row in original_table_code.split("\\\\")) + 1
    # column_definition = create_column_definition(original_col_def, max_cols, table_type)
    # table_latex_code = generate_latex_table_code(original_table_code, table_type, column_definition)
    # latex_document = create_latex_document(table_latex_code)
    
    # 使用临时文件来处理LaTeX文档和PDF输出
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tex", dir=temp_dir) as tex_file:
        tex_file_path = tex_file.name
        tex_file.write(latex_document.encode('utf-8'))
    log_file_path = tex_file_path.replace('.tex', '.log')
    pdf_file_path = tex_file_path.replace('.tex', '.pdf')  # 定义日志文件路径
    # 编译LaTeX文档到PDF
    try:
        process = subprocess.run(['pdflatex', '-interaction=nonstopmode', tex_file_path],
                                 check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_dir)
    
        # 检查PDF是否生成
        pdf_file_path = tex_file_path.replace('.tex', '.pdf')
        

        if os.path.exists(pdf_file_path):
            with open(pdf_file_path, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
            result = {"success": True, "pdf_data": pdf_data, "message": "编译成功，PDF文件已生成。"}
        else:
            result = {"success": False, "error": "PDF文件未生成。"}

    except subprocess.CalledProcessError:
        try:
            errors = extract_and_save_all_errors(log_file_path)
        except UnicodeDecodeError as decode_error:
            errors = [f"日志文件解码错误: {decode_error}"]
        if os.path.exists(pdf_file_path):
            # 编译过程中出现错误，但PDF文件仍然生成了
            with open(pdf_file_path, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
            result = {
                "success": True, 
                "pdf_data": pdf_data, 
                "message": "编译出错，但PDF文件已生成，请查看错误信息。",
                "errors": errors
            }
        else:
            # 编译失败，且PDF文件未生成
            result = {
                "success": False, 
                "message": "编译出错，PDF文件未生成，请查看错误信息。",
                "errors": errors
            }
# 在 finally 块之后返回结果
    finally:
        # 清理生成的辅助文件
        for ext in ['.aux', '.log', '.out', '.tex', '.pdf']:
            file_to_remove = tex_file_path.replace('.tex', ext)
            if os.path.exists(file_to_remove):
                os.remove(file_to_remove)

    return result



# def process_latex_codes_from_json(json_file_path):
#     """
#     从JSON文件读取LaTeX代码并尝试编译成PDF。
#     返回一个包含每个项目处理结果的列表。
#     """
#     with open(json_file_path, 'r',encoding='utf-8') as file:
#         data = json.load(file)

#     results = []  # 用于存储每个项目的处理结果
#     compiled_pdfs_dir = "pdf_test"  # PDF 文件存储目录

#     if not os.path.exists(compiled_pdfs_dir):
#         os.makedirs(compiled_pdfs_dir)
#     for index, item in enumerate(data, start=1):
#         image_name = item['image_name']
#         pred_tex_code = item['pred_tex_code']
#         base_name = os.path.splitext(image_name)[0]

#         # 编译 LaTeX 代码为 PDF
#         result = compile_latex_to_pdf(pred_tex_code, base_name,compiled_pdfs_dir)
#         result["image_name"] = image_name  # 添加图片名称到结果中，以便于识别

#         # 添加处理结果到列表中
#         results.append(result)

#         # 更新进度信息，这里不再直接打印进度，而是将进度信息包含在返回的结果中
#         progress_message = f"正在处理第{index}/{len(data)}项..."
#         results[-1]["progress"] = progress_message
        

#     return results

# results = process_latex_codes_from_json('your_json_file_path.json')
# for result in results:
#     print(result.get("error", "No error message"))  # 如果没有错误消息，则打印 "No error message"
