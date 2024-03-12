document.addEventListener('DOMContentLoaded', function() {
    let currentIndex = 0; // 当前数据的索引
    let totalItems = 0; // 总数据条目数
    let dataItems = []; // 存储从后端加载的数据项

    const pathInput = document.getElementById('path-input');
    const loadButton = document.getElementById('load');
    const prevButton = document.getElementById('prev');
    const nextButton = document.getElementById('next');
    const exportButton = document.getElementById('export');
    const counter = document.getElementById('counter');
    const imageDisplay = document.getElementById('image-display');
    const errorMessages = document.getElementById('error-messages');
    const errorDisplayArea = document.getElementById('error-display-area');
    const pdfDisplayArea = document.getElementById('pdf-display-area');
    const latexDisplayArea = document.getElementById('latex-display-area');
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const loadError = document.getElementById('load-error');
    const setCredentials = document.getElementById('set-credentials');
    const cancel = document.getElementById('cancel');

    pathInput.value = 's3://bucket-name/prefix';
    
    function base64DecodeUnicode(str) {
        // 将Base64编码的字节转换为百分比编码，然后获取原始字符串。
        percentEncodedStr = atob(str).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join('');
    
        return decodeURIComponent(percentEncodedStr);
    }
    
    function showPopup() {
        document.getElementById('awsCredentialsPopup').style.display = 'flex';
    }
    
    function closePopup() {
        document.getElementById('awsCredentialsPopup').style.display = 'none';
    }
    document.getElementById('awsCredentialsForm').addEventListener('submit', function(e) {
        e.preventDefault(); // 阻止表单默认提交行为
    
        const awsAccessKeyId = document.getElementById('awsAccessKeyId').value;
        const awsSecretAccessKey = document.getElementById('awsSecretAccessKey').value;
        const endpointUrl = document.getElementById('endpointUrl').value;
    
        // 使用 fetch API 发送数据到后端
        fetch('/set_aws_credentials/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken, // 确保这里使用了正确的 CSRF Token
            },
            body: JSON.stringify({
                aws_access_key_id: awsAccessKeyId,
                aws_secret_access_key: awsSecretAccessKey,
                endpoint_url: endpointUrl,
            }),
        })
        .then(response => response.json())
        .then(data => {
            console.log(data.message); // 处理响应数据
            closePopup(); // 关闭弹窗
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });
    
  
     
    
    

    function loadDataItems(s3Path) {
        // 使用传入的S3路径发送请求
        fetch('/api/load-json-from-s3/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken, // 确保这里使用了正确的CSRF Token
            },
            body: JSON.stringify({ s3_path: s3Path }), // 使用用户输入的S3路径
        })
        .then(response => {
            if (!response.ok) {
              // 如果响应状态码不是2xx，则抛出错误以进入catch块
              return response.json().then(errData => {
                throw new Error(errData.message || 'Server responded with an error.');
              });
            }
            return response.json();
          })
        .then(data => {
            dataItems = data; // 直接赋值
            totalItems = dataItems.length;
            currentIndex = 0; // 重置索引
            updateDisplay(); // 更新显示
            loadError.textContent='';
        })
        .catch(error => {
            console.error('Error loading data:', error);
            loadError.textContent = '加载数据失败: ' + error.message; // 显示错误信息
            // 可以在这里添加额外的逻辑，例如让输入框获得焦点以便用户重新输入
            pathInput.focus();
        });
    }
    
    function hideAllDisplayAreas() {
        errorDisplayArea.style.display = 'none';
        pdfDisplayArea.style.display = 'none';
        latexDisplayArea.style.display = 'none';
    }

    function compileAndDisplayPDF() {
        const currentItem = dataItems[currentIndex];
        if (!currentItem) {
            console.error('No current item available for PDF compilation');
            return;
        }
        const latexCode = currentItem.pred_tex_code;
        const filename=currentItem.image_name
        if (!latexCode) {
            console.error('No LaTeX code available for the current item');
            return;
        }

        const requestBody = {
            file_name: filename, 
            pred_tex_code: latexCode,
        };

        fetch('/compile_pdf/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken, 
            },
            body: JSON.stringify(requestBody),
        })
        .then(response => {
            const messageEncoded = response.headers.get('X-Compile-Message') || '';
            const compileMessage = base64DecodeUnicode(messageEncoded);
            const compileErrorsJson = response.headers.get('X-Compile-Errors');
            const compileErrors = compileErrorsJson ? JSON.parse(compileErrorsJson) : [];
            currentItem.compileMessage = compileMessage;
            currentItem.compileErrors = compileErrors;
            if (response.ok) {
                return response.blob();
            } else {
                // 编译失败，提取错误信息后抛出错误
                return response.json().then(err => {
                    throw err;
                });
            }
        })
        .then(blob => {
            // 创建 Blob URL 并保存到当前数据项
            const pdfUrl = URL.createObjectURL(blob);
            currentItem.pdf_url = pdfUrl;
            updateDisplay();
            const pdfIframe = document.getElementById('pdf-render');
            pdfIframe.src = currentItem.pdf_url; // 直接设置 iframe 的 src 属性
            pdfDisplayArea.style.display = 'block'; // 显示 PDF 区域
            
        })
        .catch(error => {
            console.error('Error compiling or displaying PDF:', error);
            currentItem.compileMessage = error.message || '编译失败';
            currentItem.compileErrors = error.errors || [];
            updateDisplay(); // 即使编译失败也更新显示，以显示错误信息

        });
    }
    
    
    function adjustImageOnRotation(imgElement, rotationAngle) {
        const parent = imgElement.parentElement;
        const isPortrait = (rotationAngle / 90) % 2 !== 0; // 图像垂直时（90或270度）
         // 重置样式，以便在未旋转时图片可以自然填充其容器
        imgElement.style.width = '';
        imgElement.style.height = '';
        // 旋转前的图片宽度与高度比较
        if (isPortrait) {
            // 当图片垂直旋转时，其宽度（在未旋转状态下的高度）可能会超出容器的最大高度
            let scaleRatio = parent.offsetHeight / (imgElement.naturalHeight*0.7);
            let scaledWidth = imgElement.naturalWidth * scaleRatio;
    
            // 如果缩放后的宽度仍然超出容器的宽度，需要进一步调整
            if (scaledWidth > parent.offsetWidth) {
                imgElement.style.width = parent.offsetWidth + 'px';
                imgElement.style.height = 'auto';
            } else {
                imgElement.style.width = (imgElement.naturalWidth * scaleRatio) + 'px';
                imgElement.style.height = 'auto';
            }
        } else {
            // 图像非垂直旋转时，重置图片尺寸为自然尺寸
            imgElement.style.width = '';
            imgElement.style.height = 'auto';
        }
    
    }
    
    // 绑定旋转按钮事件
    document.getElementById('rotate-image').addEventListener('click', function() {
        var imgDisplay = document.getElementById('image-display');
        var currentRotation = parseInt(imgDisplay.getAttribute('data-rotation')) || 0;
        var newRotation = (currentRotation + 90) % 360;
    
        // 旋转图片并调整旋转原点
        imgDisplay.style.transform = `rotate(${newRotation}deg)`;
        imgDisplay.setAttribute('data-rotation', newRotation);
        adjustImageOnRotation(imgDisplay, newRotation);
    });
        

    
    // 显示错误信息区域的按钮事件
    document.getElementById('show-errors').addEventListener('click', function() {
        hideAllDisplayAreas();
        errorDisplayArea.style.display = 'block';
    });
    

    document.getElementById('show-pdf').addEventListener('click', function() {
        hideAllDisplayAreas();
        const currentItem = dataItems[currentIndex];
        if (!currentItem) {
            console.error('No current item available for PDF display');
            errorMessages.textContent = '当前没有可用的数据项用于显示 PDF';
            return;
        }
    
        // 检查当前项是否包含预编译的 PDF URL
        if (currentItem.pdf_url) {
            const pdfIframe = document.getElementById('pdf-render');
            pdfIframe.src = currentItem.pdf_url;
            pdfDisplayArea.style.display = 'block';
        } else {
            compileAndDisplayPDF();
        }
    });
    

    // 显示LaTeX源码区域的按钮事件
    document.getElementById('show-latex').addEventListener('click', function() {
        hideAllDisplayAreas();
        latexDisplayArea.style.display = 'block';
    });

    function updateDisplay() {
        if (dataItems.length > 0 && currentIndex < dataItems.length) {
            const item = dataItems[currentIndex];
            imageDisplay.onload = null;
            //重置旋转状态
            imageDisplay.style.transform = 'rotate(0deg)';
            imageDisplay.setAttribute('data-rotation', '0');
            imageDisplay.src = item.image_path;
            // 图片加载完成后的操作
            imageDisplay.onload = function() {
                this.style.maxWidth = '70%'; // 限制最大宽度
                this.style.height = 'auto'; // 高度自动
                adjustImageOnRotation(this, 0); // 调整图片尺寸为初始状态
            };

            // 如果图片已经加载（例如从缓存中），立即执行onload操作
            if (imageDisplay.complete && imageDisplay.naturalHeight) {
                imageDisplay.onload();
            }
            const pdfIframe = document.getElementById('pdf-render');
            if (item.pdf_url) {
                pdfIframe.src = item.pdf_url; // 使用更新后的 PDF URL 或 Blob URL
            } else {
                pdfIframe.src = ''; // 如果没有 URL，清空之前的 PDF 显示
            }
                 
            // 显示 LaTeX 代码
            const latexCodeElement = document.getElementById('latex-code');
            latexCodeElement.textContent = item.pred_tex_code;

            counter.textContent = `${currentIndex + 1}/${totalItems}`;
            const compileMessageDisplay = document.getElementById('compile-message-display');
            const compileErrorDisplay = document.getElementById('error-messages');
            compileMessageDisplay.innerHTML = ''; 
            compileErrorDisplay.innerHTML = '';// 清空之前的内容
            if (item.compileMessage) {
                compileMessageDisplay.innerHTML += `<div>Compile Message: ${item.compileMessage}</div>`;
            }
            if (item.compileErrors && item.compileErrors.length > 0) {
                compileErrorDisplay.innerHTML += `<div>Errors:<ul>${item.compileErrors.map(error => `<li>${error}</li>`).join('')}</ul></div>`;
            }
            compileMessageDisplay.style.display = compileMessageDisplay.innerHTML ? 'block' : 'none';
            compileErrorDisplay.style.display = compileMessageDisplay.innerHTML ? 'block' : 'none';
        }
    }
    
    cancel.addEventListener('click', function() {
        closePopup();
    });
    
    
    setCredentials.addEventListener('click', function() {
        showPopup();  // 假设showPopup是您已经定义好的用于显示AWS凭证输入表单的函数
    });

    loadButton.addEventListener('click', function() {
        // showPopup();
        loadDataItems(pathInput.value);
    });

    prevButton.addEventListener('click', function() {
        if (currentIndex > 0) {
            currentIndex--;
            updateDisplay();
            document.getElementById('show-pdf').click();
        }
    });

    nextButton.addEventListener('click', function() {
        if (currentIndex < totalItems - 1) {
            currentIndex++;
            updateDisplay();
            document.getElementById('show-pdf').click();
        }
    });

    // 实现分类按钮的事件监听
    const classifyButtons = document.querySelectorAll('.classify');
    classifyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const category = this.getAttribute('data-category');
            const currentItem = dataItems[currentIndex]; // 从当前索引获取数据项
            const imageName = currentItem.image_name; // 获取数据项的 image_name

            fetch('/classify_data_item/', { // 确保这个URL与你的Django路由匹配
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken, // 从HTML中获取CSRF token
                },
                body: JSON.stringify({
                    image_name: imageName, // 发送 image_name 和 category
                    category: category,
                    
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    console.log('分类成功:', data);
                    currentItem.category = category; // 更新当前项的分类信息
                } else {
                    console.error('分类失败:', data.message);
                    // 显示错误信息
                }
            })
            .catch(error => {
                console.error('请求失败:', error);
            });
        });
    });

    exportButton.addEventListener('click', function() {
        // 构建导出数据的 URL
        const exportUrl = '/export_all_classified_data/'; 

        // 发起请求以触发文件下载
        window.location.href = exportUrl;
    });

});
