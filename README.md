# BookForge - 电子书格式批量转换工具

这是一个基于Calibre的`ebook-convert`命令行工具开发的Web应用，提供了电子书格式批量转换功能，方便用户通过浏览器界面转换多个电子书文件并下载。

![](https://cdn.statically.io/gh/jxzzlfh/picx-images-hosting@master/image.7w71ntiqmj.webp)

## 功能特点

- 多文件批量上传与转换
- 支持多种电子书格式之间的互相转换
- 提供基本和高级转换选项
- 结果以ZIP文件打包下载
- 美观的用户界面，支持响应式设计
- 显示转换详细结果和状态
- 自动清理临时文件，提高磁盘利用率
- 支持Docker容器化部署

## 支持的格式

**输入格式**：EPUB, MOBI, AZW, AZW3, PDF, DOCX, HTML, TXT, RTF, FB2, LIT, PRC, ODT, CBZ, CBR

**输出格式**：EPUB, MOBI, AZW3, PDF, DOCX, HTML, TXT, RTF, FB2

## 部署方式

### 方式一：本地部署

#### 依赖条件

1. Python 3.6+
2. Flask
3. Calibre（必须安装并确保`ebook-convert`命令可用）

#### 安装步骤

1. 确保已安装Calibre，并且`ebook-convert`命令可以从命令行访问
2. 克隆本仓库或下载源代码
3. 安装Python依赖：
   ```
   pip install -r requirements.txt
   ```
4. 启动应用：
   ```
   python app.py
   ```
5. 在浏览器中访问：`http://localhost:5000`

### 方式二：Docker部署（推荐）

使用Docker可以快速部署应用，无需手动安装Calibre和依赖项。

1. 确保已安装Docker和docker-compose
2. 克隆本仓库或下载源代码
3. 在项目根目录运行：
   ```
   docker-compose up -d
   ```
4. 在浏览器中访问：`http://localhost:5000`

更详细的Docker部署指南请参考`deploy-guide.md`文件。

## 使用方法

1. 在首页选择要转换的电子书文件（可多选）
2. 选择目标输出格式
3. 如需高级选项，勾选"显示高级选项"并设置相应参数
4. 点击"开始转换"按钮
5. 待转换完成后，点击"下载所有转换文件"获取ZIP压缩包
6. 下载完成后，系统会自动清理临时文件

## 项目结构

```
BookForge/
├── app.py           # Flask应用主文件
├── static/          # 静态资源
│   ├── css/         # CSS样式
│   ├── js/          # JavaScript脚本
│   └── img/         # 图片资源
├── templates/       # HTML模板
├── uploads/         # 上传文件临时目录
├── converted/       # 转换后文件临时目录
├── downloads/       # 打包下载文件临时目录
├── Dockerfile       # Docker镜像构建文件
├── docker-compose.yml # Docker Compose配置文件
├── deploy-guide.md  # 部署指南
└── requirements.txt # Python依赖列表
```

## 高级用法

可通过选择高级选项，使用Calibre的各种参数来自定义转换过程，比如设置字体大小、页边距、目录生成等。这些选项直接传递给Calibre的`ebook-convert`工具，提供专业级的电子书格式转换能力。

## 数据处理说明

- 上传的文件会分配唯一ID并保存在临时目录
- 转换完成后的文件会打包为ZIP供下载
- 用户下载文件后，系统会自动清理对应批次的临时文件
- 系统会定期清理超过24小时的所有临时文件

## 许可证

MIT 
