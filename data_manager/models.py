from django.db import models

class DataItem(models.Model):
    image_name = models.CharField(max_length=255)  # 存储图片名称
    pred_tex_code = models.TextField()  # 存储LaTeX代码
    category = models.CharField(max_length=50, blank=True)  # 用于分类的字段
    is_annotated = models.BooleanField(default=False)  # 是否已标注
    image_path = models.CharField(max_length=1024, blank=True, null=True)  # 存储图片路径

    def __str__(self):
        return self.image_name
