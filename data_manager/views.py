import boto3
from django.http import JsonResponse
import json
import base64
from django.views.decorators.clickjacking import xframe_options_exempt
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from .latex_compiler import compile_latex_to_pdf
from .models import DataItem
from django.shortcuts import render
from django.http import JsonResponse
import re
# import os




# AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY').strip()
# ENDPOINT_URL = os.environ.get('ENDPOINT_URL').strip()
# AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID').strip()

@xframe_options_exempt
def index(request):
    return render(request, 'index.html') 

@require_http_methods(["POST"])

def compile_pdf(request):
    try:
        data = json.loads(request.body)
        latex_code = data.get('pred_tex_code')
        
        compile_result = compile_latex_to_pdf(latex_code)

        if compile_result.get('success'):
            pdf_data = compile_result.get('pdf_data')
            # 创建HttpResponse对象，直接返回PDF二进制数据
            response = HttpResponse(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="compiled_document.pdf"'            
            # 检查是否有编译消息或错误信息需要传递
            if compile_result.get('message'):
                encoded_message = base64.b64encode(compile_result.get('message', '').encode('utf-8')).decode('ascii')
                response['X-Compile-Message'] = encoded_message
            
            # 错误信息，直接转为JSON字符串
            if compile_result.get('errors'):
                response['X-Compile-Errors'] = json.dumps(compile_result.get('errors', []))
            
            return response
        else:
            return JsonResponse({
                'success': False, 
                'message': compile_result.get('message', '编译失败。'), 
                'errors': compile_result.get('errors', [])
            }, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '无效的请求格式'}, status=400)



@require_http_methods(["POST"])
def set_aws_credentials(request):
    try:
        # 获取前端发送的数据
        data = json.loads(request.body)
        aws_access_key_id = data.get('aws_access_key_id')
        aws_secret_access_key = data.get('aws_secret_access_key')
        endpoint_url = data.get('endpoint_url')

        # 将凭证存储在会话中
        request.session['aws_access_key_id'] = aws_access_key_id
        request.session['aws_secret_access_key'] = aws_secret_access_key
        request.session['endpoint_url'] = endpoint_url

        return JsonResponse({'message': 'AWS credentials set successfully.'})
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=500)



@require_http_methods(["POST"])
def load_json_from_s3(request):
    """从S3桶动态加载并返回JSON数据，数据存储到数据库中。"""
    body = json.loads(request.body)
    s3_path = body.get('s3_path', '')
    
    # 解析S3路径获取bucket名称和前缀以及文件名
    match = re.match(r's3://([^/]+)/(.+)/([^/]+\.json)$', s3_path)
    if not match:
        return JsonResponse({'status': 'error', 'message': '提供的S3路径格式不正确。'}, status=400)
    bucket_name, prefix, json_filename = match.groups()
    print(bucket_name, prefix, json_filename)

    aws_access_key_id = request.session.get('aws_access_key_id')
    aws_secret_access_key = request.session.get('aws_secret_access_key')
    endpoint_url = request.session.get('endpoint_url')

    # 确保凭证已设置
    if not all([aws_access_key_id, aws_secret_access_key, endpoint_url]):
        return JsonResponse({'message': 'AWS credentials not provided or session expired.'}, status=400)

    # 使用会话中的凭证初始化 S3 客户端
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=endpoint_url
    )
    
    json_key = f"{prefix}/{json_filename}"
    try:
        # 读取并加载JSON文件
        json_object = s3_client.get_object(Bucket=bucket_name, Key=json_key)
        json_data = json.loads(json_object['Body'].read().decode('utf-8'))
        updated_data_items = []
    
        for item in json_data:
            image_name = item['image_name']
            image_key = f"{prefix}/{image_name}"  # S3中的完整key路径
            # 生成预签名URL
            image_url = s3_client.generate_presigned_url('get_object',
                                                        Params={'Bucket': bucket_name, 'Key': image_key},
                                                        ExpiresIn=3600)  # URL有效期为3600秒（1小时）
            # 保存图片名称和其他信息到数据库
            DataItem.objects.update_or_create(
                image_name=image_name,
                defaults={
                    'pred_tex_code': item['pred_tex_code'],
                    'image_path': image_url,  # 使用预签名URL保存图片的路径
                    'category': item.get('category', ''),
                    'is_annotated': item.get('is_annotated', False),
                }
            )
            updated_data_items.append({
                'image_name': image_name,
                'pred_tex_code': item['pred_tex_code'],
                'image_path': image_url,
                'category': item.get('category', ''),
                'is_annotated': item.get('is_annotated', False),
            })

        return JsonResponse(updated_data_items, safe=False)
    except s3_client.exceptions.NoSuchKey:
        return JsonResponse({'status': 'error', 'message': '未找到JSON文件。'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'加载JSON文件失败: {str(e)}'}, status=500)



@require_http_methods(["POST"])
def classify_data_item(request):
    try:
        data = json.loads(request.body)
        image_name = data['image_name']
        category = data['category']

        # 根据 image_name 查找对应的数据项
        try:
            data_item = DataItem.objects.get(image_name=image_name)
            # 更新分类信息
            data_item.category = category
            data_item.is_annotated = True 
            data_item.save()
            return JsonResponse({'status': 'success', 'message': '分类成功'})
        except DataItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '未找到指定的数据项'}, status=404)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    

CATEGORY_MAPPING = {
    'compilable_consistent': '可编译表一致',
    'compilable_slightly_inconsistent': '可编译表轻微不一致',
    'compilable_inconsistent': '可编译表不一致',
    'non_compilable': '不可编译',
}

def export_classified_data(request):
    # 根据分类查询数据项
    data_items = DataItem.objects.filter(is_annotated=True).values('image_name', 'pred_tex_code','category')

    # 转换queryset为list，仅包含需要的字段
    data_list = [
        {
            'image_name': item['image_name'],
            'pred_tex_code': item['pred_tex_code'],
            'category': CATEGORY_MAPPING.get(item['category'], item['category']),  # 使用映射转换分类
        }
        for item in data_items
     ]
    # 转换为 JSON 字符串
    data_json = json.dumps(data_list, ensure_ascii=False, indent=4)

    # 设置响应内容类型为 JSON 并设置一个合适的文件名
    response = HttpResponse(data_json, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="all_classified_data.json"'
 
    return response

