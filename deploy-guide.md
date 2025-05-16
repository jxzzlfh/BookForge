# BookForge 项目 Docker 部署指南

这份指南将帮助你使用 docker-compose 在安装了 1panel 面板的云服务器上部署 BookForge 应用。

## 准备工作

1. 确保您的云服务器已安装 1panel 面板和 docker-compose
2. 准备好您的 BookForge 项目文件

## 部署步骤

### 1. 在服务器上创建项目目录

登录您的服务器，创建一个用于部署 BookForge 的目录：

```bash
mkdir -p /opt/bookforge
cd /opt/bookforge
```

### 2. 上传项目文件到服务器

您可以通过 1panel 面板的文件管理功能或使用 SFTP 工具（如 FileZilla）将项目文件上传到服务器的 `/opt/bookforge` 目录。需要上传的关键文件包括：

- `app.py`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `static` 目录（包含 CSS、JS 和图片文件）
- `templates` 目录（包含 HTML 模板）

### 3. 创建数据目录

在服务器上创建持久化数据目录：

```bash
mkdir -p /opt/bookforge/uploads
mkdir -p /opt/bookforge/converted
mkdir -p /opt/bookforge/downloads
chmod -R 777 /opt/bookforge/uploads /opt/bookforge/converted /opt/bookforge/downloads
```

### 4. 通过 1panel 面板部署

1. 登录 1panel 面板
2. 进入"应用商店" -> "Docker 应用" -> "自定义应用"
3. 点击"添加应用"，选择"本地 docker-compose.yml"
4. 配置应用名称为"BookForge"，选择工作目录为"/opt/bookforge"
5. 点击"保存"开始部署

或者，也可以直接通过命令行部署：

```bash
cd /opt/bookforge
docker-compose up -d
```

### 5. 验证部署

部署完成后，您可以通过以下方式验证应用是否成功运行：

1. 检查容器是否正常运行：

```bash
docker ps | grep bookforge
```

2. 查看容器日志：

```bash
docker logs bookforge
```

3. 在浏览器中访问应用：`http://服务器IP:5000`

### 6. 配置反向代理（可选但推荐）

为了通过域名访问应用并启用 HTTPS，建议配置反向代理。在 1panel 面板中：

1. 进入"网站" -> "网站管理" -> "添加网站"
2. 填写您的域名信息
3. 应用类型选择"反向代理"
4. 代理地址填写：`http://127.0.0.1:5000`
5. 开启 HTTPS（可选）

### 7. 故障排除

如果遇到问题，请检查：

1. 容器日志是否显示错误：
```bash
docker logs bookforge
```

2. 确认 Calibre 是否在容器中正确安装：
```bash
docker exec -it bookforge which ebook-convert
docker exec -it bookforge ebook-convert --version
```

3. 检查目录权限：
```bash
docker exec -it bookforge ls -la /app/uploads
docker exec -it bookforge ls -la /app/converted
docker exec -it bookforge ls -la /app/downloads
```

## 更新应用

当您需要更新应用时，可以按照以下步骤操作：

1. 备份旧版本文件（如有必要）
2. 上传新版本文件到服务器
3. 重新构建并启动容器：

```bash
cd /opt/bookforge
docker-compose down
docker-compose up -d --build
```

## 常用维护命令

- 启动应用：`docker-compose up -d`
- 停止应用：`docker-compose down`
- 查看日志：`docker logs bookforge`
- 重启应用：`docker-compose restart`
- 重新构建镜像：`docker-compose build` 