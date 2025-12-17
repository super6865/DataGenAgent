# DataGenAgent

![TypeScript](https://img.shields.io/badge/TypeScript-5.3-007ACC?logo=TypeScript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=Python&logoColor=white)
![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=React&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=FastAPI&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-5.7+-4479A1?logo=MySQL&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

> 🚀 一个基于 AutoGen 框架的 AI 驱动测试数据生成平台。通过自然语言查询生成高质量测试数据，支持文档解析、模板生成和多种输出格式。

<div align="center">
  🌐 <a href="README.md"><strong>English</strong></a> | <strong>简体中文</strong>
</div>

---

## 🌟 项目简介

**DataGenAgent** 是一个面向开发人员、QA 工程师和产品经理的智能测试数据生成平台。基于 **FastAPI + React + TypeScript** 的现代化架构，通过自然语言查询、文档解析和模板工作流实现高效的测试数据生成。

🎯 核心能力：

- **自然语言数据生成**：通过简单的自然语言查询生成测试数据
- **文档解析**：自动从 API 文档、需求文档等格式中提取数据结构
- **模板管理**：创建和管理可复用的数据模板，支持 JSON Schema
- **多格式导出**：支持 JSON、CSV、Excel 等多种输出格式
- **模型配置**：灵活的 LLM 模型配置，支持 API 密钥管理
- **生成历史**：追踪和管理所有数据生成历史
- **可观测性**：基于 OpenTelemetry 的分布式追踪

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React 18.2 + TypeScript 5.3 + Vite 5.0 |
| **UI 组件库** | Ant Design 5.12 |
| **后端** | FastAPI 0.109 + Python 3.8+ |
| **数据库** | MySQL 5.7+ (SQLAlchemy 2.0) |
| **LLM 框架** | AutoGen 0.2.12 |
| **可观测性** | OpenTelemetry 1.22 |

---

## 🧠 典型使用场景

| 场景 | 描述 |
|------|------|
| **自然语言生成** | 通过自然语言描述需求生成测试数据 |
| **基于文档生成** | 解析 API 文档或需求文档，提取数据结构并生成测试数据 |
| **基于模板生成** | 使用预定义的数据模板生成一致的测试数据 |
| **多格式导出** | 以 JSON、CSV、Excel 格式导出生成的数据，满足不同测试需求 |
| **批量数据生成** | 使用自定义参数生成大量测试数据 |
| **数据验证** | 根据 JSON Schema 或业务规则验证生成的数据 |

---

## 🚀 快速开始

### 前置要求

- Python 3.8+
- Node.js 18+
- MySQL 5.7+ 或 8.0+

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/DataGenAgent.git
cd DataGenAgent
```

### 2. 后端设置

#### 安装依赖

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 配置环境变量

在 `backend` 目录下创建 `.env` 文件：

```bash
# 应用配置
APP_NAME=DataGenAgent
DEBUG=False

# 数据库配置
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/datagenagent

# CORS 配置
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# 安全配置
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# LLM 配置（可选，可通过 API 配置）
OPENAI_API_KEY=your-openai-api-key
DEFAULT_LLM_MODEL=gpt-4

# 文档上传配置
DOCUMENT_UPLOAD_DIR=uploads/documents
MAX_DOCUMENT_SIZE=52428800  # 50MB，单位：字节
ALLOWED_DOCUMENT_TYPES=[".md", ".docx", ".pdf", ".txt"]
```

#### 初始化数据库

1. **创建 MySQL 数据库**：

```sql
CREATE DATABASE datagenagent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. **初始化数据库结构**：

```bash
cd backend
alembic upgrade head
```

#### 启动后端服务

```bash
uvicorn main:app --reload --port 8000
```

后端 API 文档：
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### 3. 前端设置

#### 安装依赖

```bash
cd frontend
npm install
```

#### 启动开发服务器

```bash
npm run dev
```

前端应用：http://localhost:5173

---

## 📁 项目结构

```
DataGenAgent/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── api/v1/            # API 路由
│   │   │   ├── data_generation.py     # 数据生成 API
│   │   │   ├── data_templates.py      # 模板管理 API
│   │   │   ├── documents.py           # 文档管理 API
│   │   │   ├── history.py             # 生成历史 API
│   │   │   ├── model_config.py        # 模型配置 API
│   │   │   ├── resource_library.py    # 资源库 API
│   │   │   └── observability.py       # 可观测性 API
│   │   ├── agents/           # AI 智能体
│   │   │   ├── data_structure_agent.py    # 数据结构提取智能体
│   │   │   ├── field_parser_agent.py      # 字段解析智能体
│   │   │   ├── intent_recognition_agent.py # 意图识别智能体
│   │   │   └── test_point_agent.py        # 测试点提取智能体
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 应用配置
│   │   │   └── database.py    # 数据库配置
│   │   ├── models/            # 数据库模型
│   │   ├── services/          # 业务逻辑服务
│   │   └── utils/             # 工具函数
│   ├── alembic/               # 数据库迁移
│   ├── main.py                # 应用入口
│   └── requirements.txt       # Python 依赖
│
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/        # React 组件
│   │   ├── pages/             # 页面组件
│   │   ├── services/          # API 服务
│   │   ├── stores/            # 状态管理
│   │   └── utils/             # 工具函数
│   ├── package.json
│   └── vite.config.ts
│
└── README.md                   # 项目文档
```

---

## 📝 功能特性

### v1.0 (当前版本)

- ✅ **自然语言数据生成**：通过自然语言查询生成测试数据
- ✅ **文档解析**：解析 API 文档和需求文档，提取数据结构
- ✅ **模板管理**：创建、管理和复用数据模板，支持 JSON Schema
- ✅ **多格式导出**：支持 JSON、CSV、Excel 和文本格式
- ✅ **模型配置**：管理多个 LLM 模型配置，支持安全的 API 密钥存储
- ✅ **生成历史**：追踪和管理所有数据生成历史
- ✅ **数据验证**：根据 JSON Schema 验证生成的数据
- ✅ **可观测性**：基于 OpenTelemetry 的分布式追踪
- ✅ **资源库**：在集中式资源库中管理文档和模板

---

## 📚 API 文档

启动后端服务后，访问 API 文档：

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### 主要 API 端点

#### 数据生成
- `POST /api/v1/data-generation/generate` - 生成测试数据

#### 模板管理
- `GET /api/v1/data-templates` - 获取模板列表
- `GET /api/v1/data-templates/{id}` - 获取模板详情
- `POST /api/v1/data-templates` - 创建模板
- `PUT /api/v1/data-templates/{id}` - 更新模板
- `DELETE /api/v1/data-templates/{id}` - 删除模板

#### 文档管理
- `GET /api/v1/documents` - 获取文档列表
- `POST /api/v1/documents` - 上传文档
- `GET /api/v1/documents/{id}` - 获取文档详情
- `DELETE /api/v1/documents/{id}` - 删除文档

#### 模型配置
- `GET /api/v1/model-config` - 获取配置列表
- `POST /api/v1/model-config` - 创建配置
- `PUT /api/v1/model-config/{id}` - 更新配置
- `DELETE /api/v1/model-config/{id}` - 删除配置
- `PUT /api/v1/model-config/{id}/set-default` - 设置默认配置

#### 生成历史
- `GET /api/v1/history` - 获取历史列表
- `GET /api/v1/history/{id}` - 获取历史详情
- `DELETE /api/v1/history/{id}` - 删除历史
- `POST /api/v1/history/{id}/regenerate` - 重新生成数据

#### 资源库
- `GET /api/v1/resource-library/documents` - 获取文档资源
- `GET /api/v1/resource-library/templates` - 获取模板资源

---

## 💻 开发

### 后端开发

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
pytest  # 运行测试（如果可用）
```

### 前端开发

```bash
cd frontend
npm run dev
npm run build  # 构建生产版本
npm run lint   # 代码检查
```

### 数据库迁移

创建新迁移：

```bash
cd backend
alembic revision --autogenerate -m "description"
```

应用迁移：

```bash
alembic upgrade head
```

### 代码风格

- **Python**: 遵循 PEP 8 代码风格指南
- **TypeScript/React**: 使用 ESLint 配置

---

## 🔧 故障排除

### 常见问题

#### 数据库连接失败
**问题**：无法连接到 MySQL 数据库  
**解决方案**：
- 检查 MySQL 服务是否运行
- 验证 `.env` 中的数据库连接参数
- 检查防火墙设置
- 验证数据库用户权限

#### 前端 API 错误
**问题**：前端无法连接到后端  
**解决方案**：
- 确认后端在 8000 端口运行
- 检查后端的 CORS 配置
- 验证前端配置中的 API 基础 URL

#### 文档上传失败
**问题**：文档上传失败  
**解决方案**：
- 检查文件大小（最大 50MB）
- 验证文件类型是否允许（.md, .docx, .pdf, .txt）
- 检查上传目录权限

---

## 🤝 贡献

我们欢迎各种形式的贡献！

### 贡献流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 报告问题

如果发现 bug 或有功能建议，请在 [GitHub Issues](https://github.com/your-username/DataGenAgent/issues) 中提交。

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

---

## 🙏 致谢

- [AutoGen](https://github.com/microsoft/autogen) - Microsoft 的 AutoGen 框架
- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Web 框架
- [React](https://react.dev/) - UI 库
- [Ant Design](https://ant.design/) - 企业级 UI 组件库

---

## 🌟 支持项目

如果您觉得 DataGenAgent 有帮助，请给它一个 ⭐ **Star**！  
您的支持激励我们持续改进和维护项目 💙

> GitHub: [https://github.com/your-username/DataGenAgent](https://github.com/your-username/DataGenAgent)

---

## 📞 联系方式

如有问题或建议，请通过以下方式联系我们：

- GitHub Issues: [提交问题](https://github.com/your-username/DataGenAgent/issues)
- Email: 15979193012@163.com

