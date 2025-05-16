document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const filesInput = document.getElementById('files');
    const uploadZone = document.getElementById('upload-zone');
    const selectedFilesContainer = document.getElementById('selected-files');
    const outputFormatSelect = document.getElementById('output_format');
    const showAdvancedCheckbox = document.getElementById('show-advanced');
    const advancedOptionsDiv = document.getElementById('advanced-options');
    const formatOptionsDiv = document.getElementById('format-options');
    const convertBtn = document.getElementById('convert-btn');
    const loadingSpinner = document.getElementById('loading-spinner');
    const conversionResults = document.getElementById('conversion-results');
    const resultsTable = document.getElementById('results-table');
    const downloadLink = document.getElementById('download-link');

    // 监听文件选择
    filesInput.addEventListener('change', function(e) {
        displaySelectedFiles();
    });

    // 拖放功能 - 修复拖放区域的事件
    if (uploadZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, preventDefaults, false);
            // 防止事件冒泡到整个文档
            document.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, unhighlight, false);
        });

        function highlight() {
            uploadZone.classList.add('highlighted');
        }

        function unhighlight() {
            uploadZone.classList.remove('highlighted');
        }

        // 改进的拖放文件处理
        uploadZone.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            if (dt.files && dt.files.length > 0) {
                try {
                    // 使用浏览器兼容方法处理文件
                    const droppedFiles = Array.from(dt.files);
                    
                    // 处理拖放的文件
                    if (window.DataTransfer && window.DataTransferItemList) {
                        // 现代浏览器支持
                        try {
                            const dataTransfer = new DataTransfer();
                            
                            // 可能已有之前选择的文件，保留它们
                            if (filesInput.files) {
                                Array.from(filesInput.files).forEach(file => {
                                    try {
                                        dataTransfer.items.add(file);
                                    } catch (err) {
                                        console.warn('添加已有文件时出错:', err);
                                    }
                                });
                            }
                            
                            // 添加新拖放的文件
                            droppedFiles.forEach(file => {
                                try {
                                    dataTransfer.items.add(file);
                                } catch (err) {
                                    console.warn('添加拖放文件时出错:', err);
                                }
                            });
                            
                            // 更新文件输入
                            filesInput.files = dataTransfer.files;
                        } catch (dtError) {
                            console.warn('DataTransfer处理错误，使用回退方法:', dtError);
                            
                            // 简单回退方案：直接使用拖放的文件
                            filesInput.files = dt.files;
                        }
                    } else {
                        // 旧浏览器，直接设置
                        filesInput.files = dt.files;
                    }
                    
                    // 在UI中显示选择的文件
                    displaySelectedFiles();
                    
                    // 添加反馈
                    showAlert(`成功添加 ${droppedFiles.length} 个文件`, 'success');
                } catch (error) {
                    console.error('拖放文件处理错误:', error);
                    showAlert('添加文件时出错，请尝试直接点击选择文件', 'danger');
                }
            }
        }

        // 确保点击上传区域触发文件选择
        uploadZone.addEventListener('click', function(e) {
            // 防止事件冒泡到表单
            if (e.target === uploadZone || e.target.closest('.upload-placeholder')) {
                e.preventDefault();
                e.stopPropagation();
                filesInput.click();
            }
        });
    }

    // 显示选定的文件
    function displaySelectedFiles() {
        selectedFilesContainer.innerHTML = '';
        if (filesInput.files && filesInput.files.length > 0) {
            const fileList = Array.from(filesInput.files);
            
            // 排序文件列表，确保显示顺序一致
            fileList.sort((a, b) => a.name.localeCompare(b.name));
            
            for (let i = 0; i < fileList.length; i++) {
                const file = fileList[i];
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                
                // 获取文件扩展名
                const extension = file.name.split('.').pop().toLowerCase();
                
                // 根据文件类型选择图标
                let fileIcon = 'bi-file-earmark';
                if (['pdf'].includes(extension)) {
                    fileIcon = 'bi-file-earmark-pdf';
                } else if (['epub', 'mobi', 'azw', 'azw3'].includes(extension)) {
                    fileIcon = 'bi-book';
                } else if (['doc', 'docx', 'txt', 'rtf'].includes(extension)) {
                    fileIcon = 'bi-file-earmark-text';
                }
                
                fileItem.innerHTML = `
                    <div class="d-flex align-items-center">
                        <i class="bi ${fileIcon} me-2"></i>
                        <span class="file-name" title="${file.name}">${file.name}</span>
                    </div>
                    <div class="d-flex align-items-center">
                        <span class="file-size me-2">${formatFileSize(file.size)}</span>
                        <button type="button" class="btn-close remove-file" aria-label="删除" data-index="${i}"></button>
                    </div>
                `;
                selectedFilesContainer.appendChild(fileItem);
            }
            
            // 添加删除文件的事件处理
            document.querySelectorAll('.remove-file').forEach(button => {
                button.addEventListener('click', function() {
                    const index = parseInt(this.getAttribute('data-index'));
                    removeFile(index);
                });
            });
            
            // 如果有文件被选择，显示文件列表
            selectedFilesContainer.style.display = 'block';
        } else {
            selectedFilesContainer.style.display = 'none';
        }
    }
    
    // 增强的移除特定索引的文件函数
    function removeFile(index) {
        try {
            if (filesInput.files && filesInput.files.length > 0) {
                // 创建当前文件列表的副本，以便进行操作
                const files = Array.from(filesInput.files);
                
                // 确保索引有效
                if (index >= 0 && index < files.length) {
                    const fileToRemove = files[index];
                    
                    // 使用现代浏览器API如果可用
                    if (window.DataTransfer && window.DataTransferItemList) {
                        try {
                            const dt = new DataTransfer();
                            
                            // 添加除了要删除的文件外的所有文件
                            files.forEach((file, i) => {
                                if (i !== index) {
                                    dt.items.add(file);
                                }
                            });
                            
                            // 更新文件输入
                            filesInput.files = dt.files;
                            console.log(`已移除文件: ${fileToRemove.name}`);
                        } catch (e) {
                            console.error('使用DataTransfer移除文件失败:', e);
                            // 回退方案：清空文件列表，无法实现部分删除
                            showAlert('删除单个文件失败，请重新选择文件', 'warning');
                            filesInput.value = '';
                        }
                    } else {
                        // 不支持DataTransfer的浏览器，只能清空整个文件列表
                        console.warn('浏览器不支持DataTransfer，无法移除单个文件');
                        showAlert('您的浏览器不支持单个文件删除，请重新选择所需文件', 'warning');
                        filesInput.value = '';
                    }
                    
                    // 重新显示文件列表
                    displaySelectedFiles();
                }
            }
        } catch (error) {
            console.error('移除文件错误:', error);
            showAlert('移除文件时出错', 'danger');
        }
    }

    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        else return (bytes / 1048576).toFixed(1) + ' MB';
    }

    // 显示/隐藏高级选项
    showAdvancedCheckbox.addEventListener('change', function() {
        if (this.checked) {
            advancedOptionsDiv.style.display = 'flex';
            setTimeout(() => {
                advancedOptionsDiv.classList.add('show');
            }, 10);
        } else {
            advancedOptionsDiv.classList.remove('show');
            setTimeout(() => {
                advancedOptionsDiv.style.display = 'none';
            }, 400); // 等待动画结束
        }
    });

    // 当选择输出格式时，获取特定格式的选项
    outputFormatSelect.addEventListener('change', function() {
        const format = this.value;
        if (format) {
            // 更新选中的选项显示
            const selectedOption = this.options[this.selectedIndex];
            const iconClass = selectedOption.getAttribute('data-icon');
            
            // 显示加载中
            formatOptionsDiv.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">加载中...</span></div><p class="mt-2">加载选项中...</p></div>';
            
            // 获取该格式的特定选项
            fetch(`/options/${format}`)
                .then(response => response.json())
                .then(data => {
                    if (data.options && data.options.length > 0) {
                        displayFormatOptions(data.options);
                    } else {
                        formatOptionsDiv.innerHTML = '<div class="alert alert-info text-center"><i class="bi bi-info-circle me-2"></i>该格式没有可用的高级选项</div>';
                    }
                })
                .catch(error => {
                    console.error('获取选项出错:', error);
                    formatOptionsDiv.innerHTML = '<div class="alert alert-danger text-center"><i class="bi bi-exclamation-triangle me-2"></i>获取选项失败</div>';
                });
        } else {
            formatOptionsDiv.innerHTML = '<p class="text-muted text-center py-3">请先选择输出格式</p>';
        }
    });

    // 显示格式特定选项
    function displayFormatOptions(options) {
        formatOptionsDiv.innerHTML = '';
        
        options.forEach(option => {
            const optionGroup = document.createElement('div');
            optionGroup.className = 'option-group';
            
            let inputHtml = '';
            
            switch(option.type) {
                case 'text':
                case 'number':
                    inputHtml = `
                        <div class="input-group">
                            <input type="${option.type}" 
                                   class="form-control" 
                                   id="${option.name}" 
                                   name="${option.name}" 
                                   value="${option.default || ''}"
                                   ${option.min ? `min="${option.min}"` : ''}
                                   ${option.max ? `max="${option.max}"` : ''}>
                            ${option.type === 'number' ? 
                                `<span class="input-group-text">${option.unit || ''}</span>` : ''}
                        </div>
                    `;
                    break;
                case 'select':
                    inputHtml = `
                        <select class="form-select" id="${option.name}" name="${option.name}">
                            ${option.options.map(opt => 
                                `<option value="${opt}" ${opt === option.default ? 'selected' : ''}>${opt}</option>`
                            ).join('')}
                        </select>
                    `;
                    break;
                case 'checkbox':
                    inputHtml = `
                        <div class="form-check form-switch">
                            <input class="form-check-input" 
                                   type="checkbox" 
                                   role="switch"
                                   id="${option.name}" 
                                   name="${option.name}" 
                                   ${option.default ? 'checked' : ''}>
                            <label class="form-check-label" for="${option.name}">
                                ${option.label}
                            </label>
                        </div>
                    `;
                    break;
            }
            
            if (option.type !== 'checkbox') {
                optionGroup.innerHTML = `
                    <label for="${option.name}" class="form-label">
                        ${option.icon ? `<i class="bi ${option.icon} me-1"></i>` : ''}
                        ${option.label}
                    </label>
                    ${inputHtml}
                    ${option.description ? `<small class="text-muted d-block mt-1">${option.description}</small>` : ''}
                `;
            } else {
                optionGroup.innerHTML = inputHtml;
            }
            
            formatOptionsDiv.appendChild(optionGroup);
        });
    }

    // 表单提交
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // 检查文件是否选择
        if (filesInput.files.length === 0) {
            showAlert('请选择至少一个文件', 'danger');
            return;
        }
        
        // 检查输出格式是否选择
        const outputFormat = outputFormatSelect.value;
        if (!outputFormat) {
            showAlert('请选择输出格式', 'danger');
            return;
        }
        
        // 显示加载状态
        convertBtn.disabled = true;
        loadingSpinner.classList.remove('d-none');
        conversionResults.style.display = 'none';
        
        showAlert('开始转换，请稍候...', 'info');
        
        // 创建表单数据
        const formData = new FormData(this);
        
        // 根据是否显示高级选项决定使用哪个端点
        const endpoint = showAdvancedCheckbox.checked ? '/advanced-conversion' : '/upload';
        
        // 发送请求
        fetch(endpoint, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // 隐藏加载状态
            convertBtn.disabled = false;
            loadingSpinner.classList.add('d-none');
            
            if (data.success) {
                // 显示转换结果
                displayConversionResults(data);
                showAlert('转换完成！', 'success');
            } else {
                showAlert('转换失败: ' + (data.error || '未知错误'), 'danger');
            }
        })
        .catch(error => {
            console.error('转换请求出错:', error);
            showAlert('转换请求出错，请查看控制台获取详细信息', 'danger');
            convertBtn.disabled = false;
            loadingSpinner.classList.add('d-none');
        });
    });

    // 显示转换结果
    function displayConversionResults(data) {
        // 清空结果表格
        resultsTable.innerHTML = '';
        
        // 遍历文件并添加到表格
        data.files.forEach(file => {
            const row = document.createElement('tr');
            
            const statusClass = file.status === 'success' ? 'status-success' : 'status-failed';
            const statusIcon = file.status === 'success' ? 
                '<i class="bi bi-check-circle-fill me-1"></i>' : 
                '<i class="bi bi-x-circle-fill me-1"></i>';
            const statusText = file.status === 'success' ? '成功' : '失败';
            
            row.innerHTML = `
                <td><i class="bi bi-file-earmark me-2"></i>${file.original_name}</td>
                <td class="${statusClass}">${statusIcon}${statusText} ${file.error ? `<small>(${file.error})</small>` : ''}</td>
                <td>${file.status === 'success' ? `<i class="bi bi-file-earmark-text me-2"></i>${file.converted_name}` : '-'}</td>
            `;
            
            resultsTable.appendChild(row);
        });
        
        // 更新下载链接
        downloadLink.href = data.download_url;
        
        // 添加下载完成后的清理功能
        const batchId = data.download_url.split('/').pop();
        downloadLink.setAttribute('data-batch-id', batchId);
        
        // 监听下载链接的点击事件
        downloadLink.addEventListener('click', function(e) {
            // 捕获批次ID
            const batchId = this.getAttribute('data-batch-id');
            
            // 设置一个延时调用清理接口（给用户足够时间下载）
            setTimeout(() => {
                // 调用清理接口
                fetch(`/clean-zip/${batchId}`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    console.log('清理结果:', data);
                })
                .catch(error => {
                    console.error('清理请求出错:', error);
                });
            }, 3000); // 3秒延时，给用户足够时间开始下载
        }, { once: true }); // 使用 {once: true} 确保事件只触发一次
        
        // 显示结果区域
        conversionResults.style.display = 'block';
        
        // 滚动到结果区域
        setTimeout(() => {
            conversionResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 300);
    }
    
    // 显示提示消息
    function showAlert(message, type = 'info') {
        // 移除旧的提示
        const oldAlert = document.querySelector('.alert-message');
        if (oldAlert) {
            oldAlert.remove();
        }
        
        // 创建新提示
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show alert-message`;
        alertDiv.innerHTML = `
            ${type === 'info' ? '<i class="bi bi-info-circle me-2"></i>' : 
              type === 'success' ? '<i class="bi bi-check-circle me-2"></i>' : 
              '<i class="bi bi-exclamation-triangle me-2"></i>'}
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // 添加到页面
        const container = document.querySelector('.card-body');
        container.insertBefore(alertDiv, container.firstChild);
        
        // 自动关闭
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => {
                alertDiv.remove();
            }, 300);
        }, 5000);
    }
}); 