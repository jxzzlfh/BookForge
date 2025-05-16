from flask import Flask, render_template, request, jsonify, send_file, url_for, send_from_directory
import os
import subprocess
import uuid
import shutil
import zipfile
import logging
import sys
from werkzeug.utils import secure_filename
import time

# 配置日志记录
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
CONVERTED_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'converted')
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')

# 确保目录存在
for folder in [UPLOAD_FOLDER, CONVERTED_FOLDER, DOWNLOAD_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 限制上传文件大小为100MB

# 支持的格式
ALLOWED_INPUT_EXTENSIONS = {
    'epub', 'mobi', 'azw', 'azw3', 'pdf', 'docx', 'html', 'txt', 
    'rtf', 'fb2', 'lit', 'prc', 'odt', 'cbz', 'cbr'
}

ALLOWED_OUTPUT_FORMATS = {
    'epub', 'mobi', 'azw3', 'pdf', 'docx', 'html', 'txt', 
    'rtf', 'fb2'
}

def allowed_file(filename, allowed_extensions):
    """检查文件是否有允许的扩展名"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'favicon.ico', mimetype='image/x-icon')

def check_calibre_installed():
    """检查Calibre是否已安装"""
    try:
        result = subprocess.run(['ebook-convert', '--version'], 
                               capture_output=True, 
                               text=True, 
                               encoding='utf-8', 
                               errors='replace')
        if result.returncode == 0:
            version = result.stdout.strip() if result.stdout else 'Unknown version'
            logger.info(f"Calibre已安装: {version}")
            return True
        else:
            logger.error("ebook-convert命令返回错误代码")
            return False
    except FileNotFoundError:
        logger.error("Calibre未安装或ebook-convert不在PATH中")
        return False
    except Exception as e:
        logger.error(f"检查Calibre安装时出错: {e}")
        return False

@app.route('/')
def index():
    return render_template('index.html', output_formats=ALLOWED_OUTPUT_FORMATS)

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': '找不到文件数据'}), 400
    
    files = request.files.getlist('files[]')
    output_format = request.form.get('output_format')
    
    if not output_format or output_format not in ALLOWED_OUTPUT_FORMATS:
        return jsonify({'error': '无效的输出格式'}), 400
    
    if not files or files[0].filename == '':
        return jsonify({'error': '未选择任何文件'}), 400
    
    # 为这批文件创建一个唯一的ID
    batch_id = str(uuid.uuid4())
    batch_folder = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)
    os.makedirs(batch_folder, exist_ok=True)
    os.makedirs(os.path.join(app.config['CONVERTED_FOLDER'], batch_id), exist_ok=True)
    
    file_info = []
    
    for file in files:
        if file and file.filename:
            # 保存原始文件名，不进行安全处理以保留格式
            original_filename = file.filename
            logger.debug(f"处理上传文件: {original_filename}")
            
            # 检查文件是否有扩展名
            if '.' not in original_filename:
                file_info.append({
                    'filename': original_filename,
                    'status': 'failed',
                    'error': '文件必须有扩展名'
                })
                continue
                
            # 检查扩展名是否在允许列表中
            if not allowed_file(original_filename, ALLOWED_INPUT_EXTENSIONS):
                file_info.append({
                    'filename': original_filename,
                    'status': 'failed',
                    'error': f'不支持的文件格式。支持的格式：{", ".join(ALLOWED_INPUT_EXTENSIONS)}'
                })
                continue
                
            # 提取原始扩展名
            original_ext = original_filename.rsplit('.', 1)[1].lower()
            
            # 为存储生成唯一文件名，但保留原始文件名用于后续处理
            unique_filename = f"{uuid.uuid4().hex}.{original_ext}"
            file_path = os.path.join(batch_folder, unique_filename)
            
            # 记录详细信息用于调试
            logger.debug(f"原始文件名: {original_filename}")
            logger.debug(f"存储文件名: {unique_filename}")
            logger.debug(f"保存路径: {file_path}")
            
            # 保存文件
            file.save(file_path)
            file_info.append({
                'filename': original_filename,  # 使用原始文件名
                'path': file_path,
                'status': 'uploaded'
            })
    
    if not file_info:
        return jsonify({'error': '没有有效的文件上传'}), 400
    
    # 如果有部分文件上传失败，也继续处理
    valid_files = [f for f in file_info if f['status'] == 'uploaded']
    if not valid_files:
        return jsonify({'error': '所有文件上传均无效', 'files': file_info}), 400
    
    # 开始转换过程
    converted_files = convert_files(valid_files, output_format, batch_id)
    
    # 合并上传失败和转换结果
    failed_uploads = [f for f in file_info if f['status'] == 'failed']
    all_results = failed_uploads + converted_files
    
    # 创建ZIP文件
    zip_path = create_zip_file(converted_files, batch_id)
    
    return jsonify({
        'success': True,
        'message': f'成功转换 {len([f for f in converted_files if f["status"] == "success"])} 个文件',
        'download_url': url_for('download_file', batch_id=batch_id),
        'files': all_results
    })

def convert_files(file_info, output_format, batch_id):
    converted_files = []
    # 用于跟踪已创建的输出文件名，避免冲突
    used_output_names = set()
    
    # 首先检查Calibre是否安装
    calibre_path = 'ebook-convert'
    try:
        check_result = subprocess.run([calibre_path, '--version'], 
                                     capture_output=True, 
                                     text=True, 
                                     encoding='utf-8', 
                                     errors='replace')
        logger.info(f"Calibre版本: {check_result.stdout.strip() if check_result.returncode == 0 else '未检测到'}")
    except Exception as e:
        logger.error(f"检查Calibre安装失败: {str(e)}")
    
    # 标记是否需要清理临时文件
    temp_files_to_remove = []
    
    for file in file_info:
        input_file = file['path']
        original_filename = file['filename']
        
        # 保留原始文件名，仅改变扩展名
        original_name_without_ext = os.path.splitext(original_filename)[0]
        base_output_name = f"{original_name_without_ext}.{output_format}"
        
        # 确保输出文件名唯一，但尽量保留原始名称
        output_name = base_output_name
        counter = 1
        while output_name in used_output_names:
            output_name = f"{original_name_without_ext}_{counter}.{output_format}"
            counter += 1
        
        # 添加到已使用名称集合
        used_output_names.add(output_name)
        
        # 构建完整输出路径 - 为存储生成唯一文件名，但记录原始输出名
        unique_output_filename = f"{uuid.uuid4().hex}.{output_format}"
        output_file = os.path.join(app.config['CONVERTED_FOLDER'], batch_id, unique_output_filename)
        
        # 详细记录文件信息，用于调试
        logger.debug(f"处理文件: {original_filename}")
        logger.debug(f"输入文件路径: {input_file}")
        logger.debug(f"输入文件是否存在: {os.path.exists(input_file)}")
        logger.debug(f"输入文件大小: {os.path.getsize(input_file) if os.path.exists(input_file) else 'N/A'}")
        logger.debug(f"输入文件扩展名: {os.path.splitext(input_file)[1]}")
        logger.debug(f"原始输出文件名: {output_name}")
        logger.debug(f"存储输出文件名: {unique_output_filename}")
        logger.debug(f"输出文件路径: {output_file}")
        
        # 检查文件是否存在
        if not os.path.exists(input_file):
            logger.error(f"文件不存在: {input_file}")
            converted_files.append({
                'original_name': original_filename,
                'status': 'failed',
                'error': '找不到上传的文件'
            })
            continue
        
        # 确保输入文件有正确的扩展名
        file_ext = os.path.splitext(input_file)[1].lower()
        if not file_ext:
            # 文件没有扩展名，尝试从原始文件名推断扩展名
            if '.' in original_filename:
                orig_ext = original_filename.rsplit('.', 1)[1].lower()
                if orig_ext in ALLOWED_INPUT_EXTENSIONS:
                    new_input_file = f"{input_file}.{orig_ext}"
                    logger.debug(f"文件缺少扩展名，重命名为: {new_input_file}")
                    try:
                        os.rename(input_file, new_input_file)
                        input_file = new_input_file
                        # 增加重命名成功的日志
                        logger.info(f"文件已成功重命名: {input_file}")
                    except Exception as e:
                        logger.error(f"重命名文件失败: {str(e)}")
                        converted_files.append({
                            'original_name': original_filename,
                            'status': 'failed',
                            'error': f'文件重命名失败: {str(e)}'
                        })
                        continue
                else:
                    logger.warning(f"原始文件扩展名不被支持: {orig_ext}")
                    converted_files.append({
                        'original_name': original_filename,
                        'status': 'failed',
                        'error': f'不支持的文件格式：{orig_ext}'
                    })
                    continue
            else:
                # 如果无法确定扩展名，尝试添加默认扩展名
                default_ext = 'txt'  # 使用默认扩展名
                new_input_file = f"{input_file}.{default_ext}"
                logger.warning(f"文件没有扩展名，添加默认扩展名: {default_ext}")
                try:
                    os.rename(input_file, new_input_file)
                    input_file = new_input_file
                    logger.info(f"文件已添加默认扩展名: {input_file}")
                except Exception as e:
                    logger.error(f"添加默认扩展名失败: {str(e)}")
                    converted_files.append({
                        'original_name': original_filename,
                        'status': 'failed',
                        'error': f'添加文件扩展名失败: {str(e)}'
                    })
                    continue
        
        # 额外检查 - 确保文件路径中包含扩展名
        if '.' not in os.path.basename(input_file):
            logger.error(f"文件路径不包含扩展名: {input_file}")
            converted_files.append({
                'original_name': original_filename,
                'status': 'failed',
                'error': '文件必须有扩展名'
            })
            continue
        
        try:
            # 创建每个文件专用的临时目录以避免并发问题
            temp_dir = os.path.join(app.config['CONVERTED_FOLDER'], batch_id, f"temp_{uuid.uuid4().hex}")
            os.makedirs(temp_dir, exist_ok=True)
            temp_files_to_remove.append(temp_dir)
            
            # 创建临时输出文件
            temp_output_file = os.path.join(temp_dir, unique_output_filename)
            
            # 调用Calibre的ebook-convert命令（使用完整路径）
            # 首先尝试直接调用
            cmd = [calibre_path, input_file, temp_output_file]
            logger.debug(f"执行命令: {' '.join(cmd)}")
            
            # 使用隔离的环境和更严格的超时
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace',
                timeout=300,  # 5分钟超时
                env=os.environ.copy()  # 使用隔离的环境变量
            )
            
            # 检查转换结果
            if result.returncode == 0 and os.path.exists(temp_output_file):
                # 检查临时输出文件是否有效
                if os.path.getsize(temp_output_file) > 0:
                    # 将临时文件移动到最终位置
                    shutil.move(temp_output_file, output_file)
                    logger.info(f"成功转换: {original_filename} -> {output_name}")
                    logger.debug(f"输出文件大小: {os.path.getsize(output_file)} 字节")
                    
                    converted_files.append({
                        'original_name': original_filename,
                        'converted_name': output_name,  # 使用用户可读的原始名称
                        'converted_path': output_file,  # 实际存储路径使用唯一ID
                        'status': 'success'
                    })
                else:
                    logger.error(f"转换失败: 输出文件大小为零")
                    converted_files.append({
                        'original_name': original_filename,
                        'status': 'failed',
                        'error': '转换后的文件大小为零'
                    })
            else:
                error_msg = result.stderr if result.stderr else '未知错误'
                # 记录详细错误信息
                logger.error(f"转换失败: {original_filename}")
                logger.error(f"错误信息: {error_msg}")
                
                # 简化错误消息，取最后一行作为主要错误
                if error_msg and len(error_msg) > 100:
                    error_lines = error_msg.strip().split('\n')
                    if error_lines:
                        error_msg = error_lines[-1]
                
                converted_files.append({
                    'original_name': original_filename,
                    'status': 'failed',
                    'error': error_msg
                })
        except subprocess.TimeoutExpired:
            logger.error(f"转换超时: {original_filename}")
            converted_files.append({
                'original_name': original_filename,
                'status': 'failed',
                'error': '转换操作超时'
            })
        except Exception as e:
            logger.exception(f"处理文件时发生异常: {original_filename}")
            converted_files.append({
                'original_name': original_filename,
                'status': 'failed',
                'error': str(e)
            })
    
    # 清理临时目录
    for temp_dir in temp_files_to_remove:
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"清理临时目录失败: {temp_dir}, 错误: {str(e)}")
    
    return converted_files

def create_zip_file(converted_files, batch_id):
    zip_filename = f"converted_{batch_id}.zip"
    zip_path = os.path.join(app.config['DOWNLOAD_FOLDER'], zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        # 创建一个集合来跟踪已添加的文件名，避免重复
        added_filenames = set()
        
        for file in converted_files:
            if file['status'] == 'success':
                # 使用转换后的文件名作为ZIP内的文件名
                src_path = file['converted_path']
                original_arc_name = file['converted_name']
                
                # 确保ZIP中的文件名唯一
                arc_name = original_arc_name
                counter = 1
                
                # 如果文件名已存在，添加编号后缀
                while arc_name in added_filenames:
                    name_part, ext = os.path.splitext(original_arc_name)
                    arc_name = f"{name_part}_{counter}{ext}"
                    counter += 1
                
                # 记录已添加的文件名
                added_filenames.add(arc_name)
                
                try:
                    # 检查源文件是否存在
                    if not os.path.exists(src_path):
                        logger.error(f"无法添加到ZIP，源文件不存在: {src_path}")
                        continue
                        
                    # 记录详细信息用于调试
                    file_size = os.path.getsize(src_path)
                    logger.debug(f"添加到ZIP - 源文件: {src_path} (大小: {file_size} 字节)")
                    logger.debug(f"ZIP内文件名: {arc_name}")
                    
                    # 写入ZIP文件
                    zipf.write(src_path, arc_name)
                    logger.info(f"已添加到ZIP: {arc_name}")
                except Exception as e:
                    logger.error(f"添加文件到ZIP时出错: {e}")
    
    # 验证ZIP文件
    try:
        with zipfile.ZipFile(zip_path, 'r') as check_zip:
            file_list = check_zip.namelist()
            logger.info(f"ZIP文件创建成功，包含 {len(file_list)} 个文件")
            logger.debug(f"ZIP文件内容: {', '.join(file_list)}")
    except Exception as e:
        logger.error(f"ZIP文件验证失败: {e}")
    
    return zip_path

@app.route('/download/<batch_id>', methods=['GET'])
def download_file(batch_id):
    zip_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"converted_{batch_id}.zip")
    
    if not os.path.exists(zip_path):
        return jsonify({'error': 'Download not found'}), 404
    
    # 记录 ZIP 文件路径用于下载后删除
    response = send_file(
        zip_path,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"converted_ebooks.zip"
    )
    
    # 在返回文件之前，启动异步清理过程
    # 因为我们不能立即删除zip文件(正在下载)，所以仅清理上传和转换目录
    cleanup_batch_files(batch_id)
    
    # 添加回调函数，在响应发送完毕后删除 ZIP 文件
    @response.call_on_close
    def on_close():
        try:
            if os.path.exists(zip_path):
                logger.info(f"下载完成后删除 ZIP 文件: {zip_path}")
                os.remove(zip_path)
        except Exception as e:
            logger.error(f"删除 ZIP 文件失败: {str(e)}")
    
    return response

@app.route('/formats', methods=['GET'])
def get_formats():
    return jsonify({
        'input_formats': list(ALLOWED_INPUT_EXTENSIONS),
        'output_formats': list(ALLOWED_OUTPUT_FORMATS)
    })

@app.route('/options/<output_format>', methods=['GET'])
def get_format_options(output_format):
    if output_format not in ALLOWED_OUTPUT_FORMATS:
        return jsonify({'error': 'Invalid format'}), 400
    
    # 这里可以根据输出格式返回特定的选项
    # 下面是一个示例
    common_options = [
        {'name': 'base_font_size', 'type': 'number', 'label': '基本字体大小(pts)', 'default': 0},
        {'name': 'line_height', 'type': 'number', 'label': '行高', 'default': 0}
    ]
    
    format_specific_options = {}
    format_specific_options['pdf'] = [
        {'name': 'paper_size', 'type': 'select', 'label': '纸张大小', 
         'options': ['a4', 'a5', 'letter', 'custom'], 'default': 'a4'},
        {'name': 'pdf_page_margin_left', 'type': 'number', 'label': '左边距', 'default': 72},
        {'name': 'pdf_page_margin_right', 'type': 'number', 'label': '右边距', 'default': 72}
    ]
    format_specific_options['epub'] = [
        {'name': 'epub_version', 'type': 'select', 'label': 'EPUB版本', 
         'options': ['2', '3'], 'default': '3'}
    ]
    
    options = common_options
    if output_format in format_specific_options:
        options.extend(format_specific_options[output_format])
    
    return jsonify({'options': options})

@app.route('/advanced-conversion', methods=['POST'])
def advanced_conversion():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files[]')
    output_format = request.form.get('output_format')
    options = {}
    
    # 从表单中获取选项
    for key, value in request.form.items():
        if key != 'output_format' and key != 'files[]':
            options[key] = value
    
    if not output_format or output_format not in ALLOWED_OUTPUT_FORMATS:
        return jsonify({'error': 'Invalid output format'}), 400
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected files'}), 400
    
    # 为这批文件创建一个唯一的ID
    batch_id = str(uuid.uuid4())
    batch_folder = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)
    os.makedirs(batch_folder, exist_ok=True)
    os.makedirs(os.path.join(app.config['CONVERTED_FOLDER'], batch_id), exist_ok=True)
    
    file_info = []
    
    for file in files:
        if file and file.filename:
            # 保存原始文件名
            original_filename = file.filename
            logger.debug(f"高级模式处理上传文件: {original_filename}")
            
            # 检查文件是否有扩展名
            if '.' not in original_filename:
                file_info.append({
                    'filename': original_filename,
                    'status': 'failed',
                    'error': '文件必须有扩展名'
                })
                continue
                
            # 检查扩展名是否在允许列表中
            if not allowed_file(original_filename, ALLOWED_INPUT_EXTENSIONS):
                file_info.append({
                    'filename': original_filename,
                    'status': 'failed',
                    'error': f'不支持的文件格式。支持的格式：{", ".join(ALLOWED_INPUT_EXTENSIONS)}'
                })
                continue
                
            # 提取原始扩展名
            original_ext = original_filename.rsplit('.', 1)[1].lower()
            
            # 生成安全的文件名，但保留原始扩展名
            name_part = secure_filename(os.path.splitext(original_filename)[0])
            safe_filename = f"{name_part}.{original_ext}"
            
            # 确保文件名不为空
            if not name_part:
                name_part = "unnamed_file"
                safe_filename = f"{name_part}.{original_ext}"
                
            file_path = os.path.join(batch_folder, safe_filename)
            
            # 记录详细信息用于调试
            logger.debug(f"原始文件名: {original_filename}")
            logger.debug(f"安全文件名: {safe_filename}")
            logger.debug(f"保存路径: {file_path}")
            
            # 保存文件
            file.save(file_path)
            file_info.append({
                'filename': original_filename,  # 使用原始文件名
                'path': file_path,
                'status': 'uploaded'
            })
    
    if not file_info:
        return jsonify({'error': 'No valid files uploaded'}), 400
    
    # 开始转换过程，传入高级选项
    converted_files = advanced_convert_files(file_info, output_format, batch_id, options)
    
    # 创建ZIP文件
    zip_path = create_zip_file(converted_files, batch_id)
    
    return jsonify({
        'success': True,
        'message': f'成功转换 {len([f for f in converted_files if f.get("status") == "success"])} 个文件',
        'download_url': url_for('download_file', batch_id=batch_id),
        'files': converted_files
    })

def advanced_convert_files(file_info, output_format, batch_id, options):
    converted_files = []
    # 用于跟踪已创建的输出文件名，避免冲突
    used_output_names = set()
    
    # 标记是否需要清理临时文件
    temp_files_to_remove = []
    
    # 使用与普通转换相同的Calibre路径
    calibre_path = 'ebook-convert'
    
    for file in file_info:
        input_file = file['path']
        original_filename = file['filename']
        
        # 保留原始文件名，仅改变扩展名
        original_name_without_ext = os.path.splitext(original_filename)[0]
        base_output_name = f"{original_name_without_ext}.{output_format}"
        
        # 确保输出文件名唯一，但尽量保留原始名称
        output_name = base_output_name
        counter = 1
        while output_name in used_output_names:
            output_name = f"{original_name_without_ext}_{counter}.{output_format}"
            counter += 1
        
        # 添加到已使用名称集合
        used_output_names.add(output_name)
        
        # 构建完整输出路径 - 为存储生成唯一文件名，但记录原始输出名
        unique_output_filename = f"{uuid.uuid4().hex}.{output_format}"
        output_file = os.path.join(app.config['CONVERTED_FOLDER'], batch_id, unique_output_filename)
        
        # 详细记录文件信息，用于调试
        logger.debug(f"高级转换 - 处理文件: {original_filename}")
        logger.debug(f"输入文件路径: {input_file}")
        logger.debug(f"输入文件是否存在: {os.path.exists(input_file)}")
        logger.debug(f"输入文件大小: {os.path.getsize(input_file) if os.path.exists(input_file) else 'N/A'}")
        logger.debug(f"输入文件扩展名: {os.path.splitext(input_file)[1]}")
        logger.debug(f"原始输出文件名: {output_name}")
        logger.debug(f"存储输出文件名: {unique_output_filename}")
        logger.debug(f"输出文件路径: {output_file}")
        
        # 检查文件是否存在
        if not os.path.exists(input_file):
            logger.error(f"文件不存在: {input_file}")
            converted_files.append({
                'original_name': original_filename,
                'status': 'failed',
                'error': '找不到上传的文件'
            })
            continue
        
        # 确保输入文件有正确的扩展名
        file_ext = os.path.splitext(input_file)[1].lower()
        if not file_ext:
            # 文件没有扩展名，尝试从原始文件名推断扩展名
            if '.' in original_filename:
                orig_ext = original_filename.rsplit('.', 1)[1].lower()
                if orig_ext in ALLOWED_INPUT_EXTENSIONS:
                    new_input_file = f"{input_file}.{orig_ext}"
                    logger.debug(f"文件缺少扩展名，重命名为: {new_input_file}")
                    try:
                        os.rename(input_file, new_input_file)
                        input_file = new_input_file
                        # 增加重命名成功的日志
                        logger.info(f"文件已成功重命名: {input_file}")
                    except Exception as e:
                        logger.error(f"重命名文件失败: {str(e)}")
                        converted_files.append({
                            'original_name': original_filename,
                            'status': 'failed',
                            'error': f'文件重命名失败: {str(e)}'
                        })
                        continue
                else:
                    logger.warning(f"原始文件扩展名不被支持: {orig_ext}")
                    converted_files.append({
                        'original_name': original_filename,
                        'status': 'failed',
                        'error': f'不支持的文件格式：{orig_ext}'
                    })
                    continue
            else:
                # 如果无法确定扩展名，尝试添加默认扩展名
                default_ext = 'txt'  # 使用默认扩展名
                new_input_file = f"{input_file}.{default_ext}"
                logger.warning(f"文件没有扩展名，添加默认扩展名: {default_ext}")
                try:
                    os.rename(input_file, new_input_file)
                    input_file = new_input_file
                    logger.info(f"文件已添加默认扩展名: {input_file}")
                except Exception as e:
                    logger.error(f"添加默认扩展名失败: {str(e)}")
                    converted_files.append({
                        'original_name': original_filename,
                        'status': 'failed',
                        'error': f'添加文件扩展名失败: {str(e)}'
                    })
                    continue
        
        # 额外检查 - 确保文件路径中包含扩展名
        if '.' not in os.path.basename(input_file):
            logger.error(f"文件路径不包含扩展名: {input_file}")
            converted_files.append({
                'original_name': original_filename,
                'status': 'failed',
                'error': '文件必须有扩展名'
            })
            continue
        
        try:
            # 创建每个文件专用的临时目录以避免并发问题
            temp_dir = os.path.join(app.config['CONVERTED_FOLDER'], batch_id, f"temp_{uuid.uuid4().hex}")
            os.makedirs(temp_dir, exist_ok=True)
            temp_files_to_remove.append(temp_dir)
            
            # 创建临时输出文件
            temp_output_file = os.path.join(temp_dir, unique_output_filename)
            
            # 调用Calibre的ebook-convert命令
            cmd = [calibre_path, input_file, temp_output_file]
            
            # 添加选项
            for key, value in options.items():
                if value:  # 只添加有值的选项
                    cmd.append(f'--{key.replace("_", "-")}={value}')
            
            logger.debug(f"执行命令: {' '.join(cmd)}")
            
            # 使用隔离的环境和更严格的超时
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace',
                timeout=300,  # 5分钟超时
                env=os.environ.copy()  # 使用隔离的环境变量
            )
            
            # 检查转换结果
            if result.returncode == 0 and os.path.exists(temp_output_file):
                # 检查临时输出文件是否有效
                if os.path.getsize(temp_output_file) > 0:
                    # 将临时文件移动到最终位置
                    shutil.move(temp_output_file, output_file)
                    logger.info(f"成功转换: {original_filename} -> {output_name}")
                    logger.debug(f"输出文件大小: {os.path.getsize(output_file)} 字节")
                    
                    converted_files.append({
                        'original_name': original_filename,
                        'converted_name': output_name,  # 使用用户可读的原始名称
                        'converted_path': output_file,  # 实际存储路径使用唯一ID
                        'status': 'success'
                    })
                else:
                    logger.error(f"转换失败: 输出文件大小为零")
                    converted_files.append({
                        'original_name': original_filename,
                        'status': 'failed',
                        'error': '转换后的文件大小为零'
                    })
            else:
                error_msg = result.stderr if result.stderr else '未知错误'
                # 记录详细错误信息
                logger.error(f"转换失败: {original_filename}")
                logger.error(f"错误信息: {error_msg}")
                
                # 简化错误消息，取最后一行作为主要错误
                if error_msg and len(error_msg) > 100:
                    error_lines = error_msg.strip().split('\n')
                    if error_lines:
                        error_msg = error_lines[-1]
                
                converted_files.append({
                    'original_name': original_filename,
                    'status': 'failed',
                    'error': error_msg
                })
        except subprocess.TimeoutExpired:
            logger.error(f"转换超时: {original_filename}")
            converted_files.append({
                'original_name': original_filename,
                'status': 'failed',
                'error': '转换操作超时'
            })
        except Exception as e:
            logger.exception(f"处理文件时发生异常: {original_filename}")
            converted_files.append({
                'original_name': original_filename,
                'status': 'failed',
                'error': str(e)
            })
    
    # 清理临时目录
    for temp_dir in temp_files_to_remove:
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"清理临时目录失败: {temp_dir}, 错误: {str(e)}")
    
    return converted_files

# 清理函数 - 定期运行以清理旧文件
def cleanup_old_files(max_age_hours=24):
    """清理超过一定时间的临时文件和目录"""
    logger.info(f"开始清理超过 {max_age_hours} 小时的临时文件...")
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    # 清理上传目录中的旧批次文件夹
    try:
        for batch_id in os.listdir(UPLOAD_FOLDER):
            batch_path = os.path.join(UPLOAD_FOLDER, batch_id)
            if os.path.isdir(batch_path):
                # 检查目录的修改时间
                mod_time = os.path.getmtime(batch_path)
                if (current_time - mod_time) > max_age_seconds:
                    logger.info(f"清理旧上传目录: {batch_id}")
                    shutil.rmtree(batch_path, ignore_errors=True)
    except Exception as e:
        logger.error(f"清理上传目录时出错: {str(e)}")
    
    # 清理转换目录中的旧批次文件夹
    try:
        for batch_id in os.listdir(CONVERTED_FOLDER):
            batch_path = os.path.join(CONVERTED_FOLDER, batch_id)
            if os.path.isdir(batch_path):
                mod_time = os.path.getmtime(batch_path)
                if (current_time - mod_time) > max_age_seconds:
                    logger.info(f"清理旧转换目录: {batch_id}")
                    shutil.rmtree(batch_path, ignore_errors=True)
    except Exception as e:
        logger.error(f"清理转换目录时出错: {str(e)}")
    
    # 清理下载目录中的旧ZIP文件
    try:
        for filename in os.listdir(DOWNLOAD_FOLDER):
            if filename.startswith("converted_") and filename.endswith(".zip"):
                file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                mod_time = os.path.getmtime(file_path)
                if (current_time - mod_time) > max_age_seconds:
                    logger.info(f"清理旧ZIP文件: {filename}")
                    os.remove(file_path)
    except Exception as e:
        logger.error(f"清理下载目录时出错: {str(e)}")
    
    logger.info("清理完成")

def cleanup_batch_files(batch_id):
    """清理指定批次的文件和目录"""
    logger.info(f"清理批次 {batch_id} 的文件...")
    
    # 清理上传目录
    batch_upload_path = os.path.join(UPLOAD_FOLDER, batch_id)
    if os.path.exists(batch_upload_path):
        try:
            logger.debug(f"删除上传目录: {batch_upload_path}")
            shutil.rmtree(batch_upload_path, ignore_errors=True)
        except Exception as e:
            logger.error(f"删除上传目录时出错: {str(e)}")
    
    # 清理转换目录
    batch_converted_path = os.path.join(CONVERTED_FOLDER, batch_id)
    if os.path.exists(batch_converted_path):
        try:
            logger.debug(f"删除转换目录: {batch_converted_path}")
            shutil.rmtree(batch_converted_path, ignore_errors=True)
        except Exception as e:
            logger.error(f"删除转换目录时出错: {str(e)}")
    
    # 注意：这里不删除ZIP文件，因为用户可能需要再次下载
    logger.info(f"批次 {batch_id} 清理完成")

@app.route('/clean-zip/<batch_id>', methods=['POST'])
def clean_zip_file(batch_id):
    """下载完成后清理ZIP文件的API"""
    zip_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f"converted_{batch_id}.zip")
    
    try:
        if os.path.exists(zip_path):
            logger.info(f"手动清理ZIP文件: {zip_path}")
            os.remove(zip_path)
            return jsonify({'success': True, 'message': '文件已清理'})
        else:
            return jsonify({'success': False, 'message': '文件不存在'}), 404
    except Exception as e:
        logger.error(f"清理ZIP文件失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # 检查Calibre是否已安装
    if not check_calibre_installed():
        print("警告: Calibre未安装或ebook-convert不在PATH中")
        print("请安装Calibre并确保ebook-convert命令可用")
        print("继续启动应用，但转换功能可能无法正常工作")
    
    # 清理旧文件
    cleanup_old_files()
    
    app.run(host='0.0.0.0', port=5000, debug=False) 