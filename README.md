# Geek Toolbox Pro 🛠️

**Geek Toolbox Pro** 是一个基于 Python 和 Web 技术栈构建的现代化、跨平台桌面工具箱。它结合了 FastAPI 的高性能后端与 Vue 3 + Element Plus 的精美前端，通过 PyWebView 封装为原生桌面应用，支持纯离线环境运行。

## ✨ 核心功能

### 📝 个人效能

- **待办清单 (Todo List)**
  - 支持 Markdown 语法（标题、粗体、列表等）。
  - 智能状态追踪：区分创建时间、更新时间、完成时间。
  - 数据持久化存储（SQLite）。
- **密码保险柜 (Password Vault)**
  - **AES 加密**存储，确保数据安全。
  - 支持记录账号、密码、URL、标签。
  - 默认隐藏密码，支持一键复制和显隐切换。
  - 支持按标题或标签快速检索。

### 💻 开发者工具

- **Curl 转 Python**智能正则解析
  - 完美支持 Bilibili 等复杂 Cookie/Header 的 Curl 命令。
  - 一键生成 requests 代码。
- **JSON 格式化**
  - 支持标准 JSON 及 Python Dict 字符串（如 {'a': True, 'b': None}）。
  - **树形可视化**：支持节点折叠/展开、全屏分栏布局。
  - **高亮检索**：快速查找 Key 或 Value。
- **文件 Hash 计算**
  - **流式读取**：支持 GB 级大文件，内存占用极低。
  - 一次计算同时输出 MD5、SHA1、SHA256。
- **时间工具**
  - **时间计算器**：推算未来/过去的时间点。
  - **时间戳转换**：支持秒/毫秒级双向转换。
- **编码转换**
  - Base64 编解码、URL 编解码、Unicode (\uXXXX) 编解码。

## 🏗️ 技术栈

- **后端**: Python, FastAPI, Uvicorn, SQLite, Cryptography
- **前端**: HTML5, Vue 3, Element Plus, Axios, Marked.js
- **GUI 容器**: PyWebView (基于 Edge WebView2)
- **打包**: PyInstaller

## 🚀 开发环境搭建

### 1. 克隆项目

```
git clone https://github.com/your-repo/toolbox.git
cd toolbox
```

### 2. 安装依赖

推荐使用 uv 或 pip 安装 Python 依赖：

```
pip install fastapi uvicorn pywebview cryptography requests python-multipart pyinstaller
```

### 3. 静态资源离线化 (关键步骤)

为了支持纯内网/离线环境运行，请下载以下依赖并放入` static/lib/ `目录：

> **目录结构**:
>
> ```
> static/
> ├── lib/
> │   ├── vue.js            (https://unpkg.com/vue@3/dist/vue.global.prod.js)
> │   ├── element-plus.js   (https://unpkg.com/element-plus/dist/index.full.min.js)
> │   ├── element-plus.css  (https://unpkg.com/element-plus/dist/index.css)
> │   ├── icons.js          (https://unpkg.com/@element-plus/icons-vue/dist/index.iife.min.js)
> │   ├── axios.js          (https://unpkg.com/axios/dist/axios.min.js)
> │   └── marked.js         (https://cdn.jsdelivr.net/npm/marked/marked.min.js)
> └── index.html
> ```

### 4. 运行开发版

```
python main.py
```

## 📦 打包发布 (Windows EXE)

本项目经过特殊配置，解决了 PyInstaller 打包后的静态资源路径问题和数据丢失问题。

在项目根目录下运行以下命令：

```
# -F: 生成单文件
# -w: 隐藏控制台窗口 (调试时可去掉)
# --add-data: 将 static 文件夹打包进 exe
pyinstaller -F -w --add-data "static;static" main.py
```

打包完成后，可执行文件位于 dist/main.exe。

> **注意**：生成的 toolbox.db 数据库文件会自动保存在 main.exe 同级目录下，确保数据在软件更新或重启后不丢失。

## 📂 项目结构

```
toolbox/
├── main.py              # 后端核心逻辑 (FastAPI + PyWebView)
├── toolbox.db           # SQLite 数据库 (自动生成)
├── static/              # 前端资源目录
│   ├── index.html       # 单页应用入口 (Vue + Element Plus)
│   └── lib/             # 本地化的第三方库 (Vue, Axios 等)
└── README.md            # 说明文档
```

## ⚠️ 常见问题

1. **打包后运行报错？**

   尝试去掉打包命令中的 -w 参数，重新打包并运行，查看控制台输出的错误信息。确保 static/lib 下的所有 JS/CSS 文件都已下载齐全。

2. **杀毒软件误报？**

   PyInstaller 打包的单文件 EXE 可能会被部分杀毒软件误报，属于正常现象，可添加信任或使用文件夹模式打包 (-D)。

3. **数据去哪了？**

   用户数据存储在运行目录下的 toolbox.db 中。请勿随意删除该文件，否则会导致待办事项和密码记录丢失。

## 📄 License

MIT License © 2023 Geek Toolbox Pro