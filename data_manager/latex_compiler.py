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

 

def create_column_definition(original_def, max_cols, table_type, replace_with='X'):
    # 检查原始定义中的分隔符位置
    separators = [i for i, char in enumerate(original_def) if char == '|']

    # 如果是宽表格类型，生成新的列定义
    if table_type == "wide_table":
        new_col_defs = [replace_with] * max_cols
    else:
        # 对于其他类型，使用原始定义中的列类型
        new_col_defs = list(original_def.replace('|', ''))

        # 如果原始列数少于max_cols，用 'l' 填充剩余列
        while len(new_col_defs) < max_cols:
            new_col_defs.append('l')

    # 将分隔符插回适当的位置
    for sep_index in separators:
        new_col_defs.insert(sep_index, '|')

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

def generate_latex_table_code(original_table_code, table_type, column_definition):
    """
    根据表格类型和列定义生成LaTeX表格代码。

    :param original_table_code: 原始的LaTeX表格代码。
    :param table_type: 表格类型，可以是'longtable'、'wide_table'或其他（标准tabular）。
    :param column_definition: 列定义，用于指定表格的列格式。
    :return: 根据指定类型和列定义修改后的LaTeX表格代码。
    """
    if table_type == "longtable":
        table_latex_code = re.sub(r"\\begin{tabular}{.*?}", rf"\\begin{{longtable}}{{{column_definition}}}", original_table_code)
        table_latex_code = re.sub(r"\\end{tabular}", r"\\end{longtable}", table_latex_code)
    elif table_type == "wide_table":
        table_latex_code = re.sub(r"\\begin{tabular}{.*?}", rf"\\begin{{tabularx}}{{\\textwidth}}{{{column_definition}}}", original_table_code)
        table_latex_code = re.sub(r"\\end{tabular}", r"\\end{tabularx}", table_latex_code)
    else:
        # 对于标准 tabular，更新列定义
        table_latex_code = re.sub(r"\\begin{tabular}{.*?}", rf"\\begin{{tabular}}{{{column_definition}}}", original_table_code)
        table_latex_code = re.sub(r"\\end{tabular}", r"\\end{tabular}", table_latex_code)

    return table_latex_code



def compile_latex_to_pdf(original_table_code):
    # 生成 LaTeX 文档
    
    temp_dir = os.path.join(settings.BASE_DIR, 'temp')  # 假设你已经在settings.py中定义了BASE_DIR
    os.makedirs(temp_dir, exist_ok=True)

    result = {"success": False, "error": "初始化错误"}  # 默认返回值

    original_col_def_match = re.search(r"\\begin{tabular}{(.*?)}", original_table_code)
    original_col_def = original_col_def_match.group(1)
    table_type = determine_table_type(original_table_code)
    max_cols = max(row.count('&') for row in original_table_code.split("\\\\")) + 1
    column_definition = create_column_definition(original_col_def, max_cols, table_type)
    table_latex_code = generate_latex_table_code(original_table_code, table_type, column_definition)
    latex_document = create_latex_document(table_latex_code)
    
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
