# 表格渲染工具

## 目的
工具允许用户输入一个S3桶路径，从中加载`tables.json`文件，并编译其中的LaTeX代码。用户可以在前端展示PDF，并与该路径下的图片进行比对。这有助于用户判断编译出的PDF，并对其进行分类标签打印。最终，用户可以导出不同分类的JSON文件。
- ps：首次输入路径需要点击显示PDF（后续点击上一页，下一页的时候就无需再点击），成功加载的标志是渲染出s3桶路径下的图片，

## 功能概述

- **文档编译**：
  - `compile_pdf`视图负责将LaTeX代码编译成PDF文档。它处理包括长宽表格在内的复杂表格类型，并且能够自动调整列定义以适应内容。
  - 编译过程中如果遇到错误，会尝试从日志文件中提取并返回这些错误。
  - 使用`pdflatex`命令编译LaTeX代码，这要求使用者的系统上必须安装了LaTeX环境。
  - 即便在存在编译错误的情况下，如果PDF文件生成了，该PDF文件也会被返回给用户。

- **自动表格调整**：
  - 根据表格的行数和最大列数自动确定表格类型是标准表格、长表格还是宽表格。
  - 如果表格列数不足，会自动填充额外的列，以确保表格布局正确。

- **数据加载与显示**：
  - 通过`load_json_from_s3`视图从S3桶加载JSON数据。
  - 加载数据包括图片名称、LaTeX代码等，并将图片保存到文件系统。

- **数据分类**：
  - `classify_data_item`视图允许通过POST请求对数据项进行分类。
  - 分类信息更新到数据库中。

- **数据导出**：
  - `export_classified_data`视图按分类导出数据项，以JSON格式返回。

- **PDF渲染**：
  - 用户可以查看编译后的PDF文档，PDF以Blob URL的形式在iframe中展示。

- **错误处理与显示**：
  - 显示编译过程中的错误和消息。

- **图片旋转**：
  - 支持图片旋转功能，方便用户校正图片方向。

- **分页和导航**：
  - 提供“上一个”和“下一个”按钮来浏览不同数据项。

- **分类和导出功能**：
  - 允许用户分类数据项并批量导出特定分类的数据。


## 开始

首先，请确保你已经设置了必要的环境变量。打开你的终端（在Unix-like系统中）或命令提示符/PowerShell（在Windows系统中），并输入以下命令，替换尖括号及其内容为你的实际凭证：

```bash
export AWS_ACCESS_KEY_ID=<你的访问密钥>
export AWS_SECRET_ACCESS_KEY=<你的秘密密钥>
export ENDPOINT_URL=<你的端点URL>
```

请注意，在Windows上，你应该使用 set 命令而不是 export：
```cmd
set AWS_ACCESS_KEY_ID=<你的访问密钥>
set AWS_SECRET_ACCESS_KEY=<你的秘密密钥>
set ENDPOINT_URL=<你的端点URL>
```
设置了环境变量后，继续以下步骤克隆仓库并运行项目：
```bash
git clone https://github.com/drunkpig/s3tableviewer.git
cd s3tableviewer
# 安装依赖
pip install -r requirements.txt
# 应用数据库迁移
python manage.py migrate
# 运行项目
python manage.py runserver
```