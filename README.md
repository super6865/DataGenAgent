# DataGenAgent

![TypeScript](https://img.shields.io/badge/TypeScript-5.3-007ACC?logo=TypeScript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=Python&logoColor=white)
![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=React&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=FastAPI&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-5.7+-4479A1?logo=MySQL&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

> 🚀 An AI-powered test data generation platform built on the AutoGen framework. Generate high-quality test data through natural language queries, with support for document parsing, template-based generation, and multiple output formats.

<div align="center">
  🌐 <strong>English</strong> | <a href="README.zh.md">简体中文</a>
</div>

---

## 🌟 Project Overview

**DataGenAgent** is an intelligent test data generation platform designed for developers, QA engineers, and product managers. Built on a modern architecture with **FastAPI + React + TypeScript**, it enables efficient test data generation through natural language queries, document parsing, and template-based workflows.

🎯 Core Capabilities:

- **Natural Language Data Generation**: Generate test data through simple natural language queries
- **Document Parsing**: Automatically extract data structures from API documentation, requirement documents, and other formats
- **Template Management**: Create and manage reusable data templates with JSON Schema support
- **Multi-Format Export**: Support JSON, CSV, Excel, and other output formats
- **Model Configuration**: Flexible LLM model configuration with API key management
- **Generation History**: Track and manage all data generation history
- **Observability**: Distributed tracing with OpenTelemetry integration

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18.2 + TypeScript 5.3 + Vite 5.0 |
| **UI Library** | Ant Design 5.12 |
| **Backend** | FastAPI 0.109 + Python 3.8+ |
| **Database** | MySQL 5.7+ (SQLAlchemy 2.0) |
| **LLM Framework** | AutoGen 0.2.12 |
| **Observability** | OpenTelemetry 1.22 |

---

## 🧠 Typical Use Cases

| Scenario | Description |
|----------|-------------|
| **Natural Language Generation** | Generate test data by describing requirements in natural language |
| **Document-Based Generation** | Parse API documentation or requirement documents to extract data structures and generate test data |
| **Template-Based Generation** | Use predefined data templates to generate consistent test data |
| **Multi-Format Export** | Export generated data in JSON, CSV, Excel formats for different testing needs |
| **Batch Data Generation** | Generate large volumes of test data with customizable parameters |
| **Data Validation** | Validate generated data against JSON Schema or business rules |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- MySQL 5.7+ or 8.0+

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/DataGenAgent.git
cd DataGenAgent
```

### 2. Backend Setup

#### Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Configure Environment Variables

Create a `.env` file in the `backend` directory:

```bash
# Application Configuration
APP_NAME=DataGenAgent
DEBUG=False

# Database Configuration
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/datagenagent

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Security Configuration
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# LLM Configuration (Optional, can be configured via API)
OPENAI_API_KEY=your-openai-api-key
DEFAULT_LLM_MODEL=gpt-4

# Document Upload Configuration
DOCUMENT_UPLOAD_DIR=uploads/documents
MAX_DOCUMENT_SIZE=52428800  # 50MB in bytes
ALLOWED_DOCUMENT_TYPES=[".md", ".docx", ".pdf", ".txt"]
```

#### Initialize Database

1. **Create MySQL Database**:

```sql
CREATE DATABASE datagenagent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. **Initialize Database Schema**:

```bash
cd backend
alembic upgrade head
```

#### Start Backend Server

```bash
uvicorn main:app --reload --port 8000
```

Backend API documentation:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### 3. Frontend Setup

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Start Development Server

```bash
npm run dev
```

Frontend application: http://localhost:5173

---

## 📁 Project Structure

```
DataGenAgent/
├── backend/                    # Python Backend
│   ├── app/
│   │   ├── api/v1/            # API Routes
│   │   │   ├── data_generation.py     # Data generation API
│   │   │   ├── data_templates.py      # Template management API
│   │   │   ├── documents.py           # Document management API
│   │   │   ├── history.py             # Generation history API
│   │   │   ├── model_config.py        # Model configuration API
│   │   │   ├── resource_library.py    # Resource library API
│   │   │   └── observability.py       # Observability API
│   │   ├── agents/           # AI Agents
│   │   │   ├── data_structure_agent.py    # Data structure extraction agent
│   │   │   ├── field_parser_agent.py      # Field parsing agent
│   │   │   ├── intent_recognition_agent.py # Intent recognition agent
│   │   │   └── test_point_agent.py        # Test point extraction agent
│   │   ├── core/              # Core Configuration
│   │   │   ├── config.py      # App Configuration
│   │   │   └── database.py    # Database Configuration
│   │   ├── models/            # Database Models
│   │   ├── services/          # Business Logic Services
│   │   └── utils/             # Utility Functions
│   ├── alembic/               # Database Migrations
│   ├── main.py                # Application Entry Point
│   └── requirements.txt       # Python Dependencies
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/        # React Components
│   │   ├── pages/             # Page Components
│   │   ├── services/          # API Services
│   │   ├── stores/            # State Management
│   │   └── utils/             # Utility Functions
│   ├── package.json
│   └── vite.config.ts
│
└── README.md                   # Project Documentation
```

---

## 📝 Features

### v1.0 (Current)

- ✅ **Natural Language Data Generation**: Generate test data through natural language queries
- ✅ **Document Parsing**: Parse API documentation and requirement documents to extract data structures
- ✅ **Template Management**: Create, manage, and reuse data templates with JSON Schema
- ✅ **Multi-Format Export**: Support JSON, CSV, Excel, and Text formats
- ✅ **Model Configuration**: Manage multiple LLM model configurations with secure API key storage
- ✅ **Generation History**: Track and manage all data generation history
- ✅ **Data Validation**: Validate generated data against JSON Schema
- ✅ **Observability**: Distributed tracing with OpenTelemetry integration
- ✅ **Resource Library**: Manage documents and templates in a centralized library

---

## 📚 API Documentation

After starting the backend service, access the API documentation:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Main API Endpoints

#### Data Generation
- `POST /api/v1/data-generation/generate` - Generate test data

#### Template Management
- `GET /api/v1/data-templates` - Get template list
- `GET /api/v1/data-templates/{id}` - Get template details
- `POST /api/v1/data-templates` - Create template
- `PUT /api/v1/data-templates/{id}` - Update template
- `DELETE /api/v1/data-templates/{id}` - Delete template

#### Document Management
- `GET /api/v1/documents` - Get document list
- `POST /api/v1/documents` - Upload document
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document

#### Model Configuration
- `GET /api/v1/model-config` - Get configuration list
- `POST /api/v1/model-config` - Create configuration
- `PUT /api/v1/model-config/{id}` - Update configuration
- `DELETE /api/v1/model-config/{id}` - Delete configuration
- `PUT /api/v1/model-config/{id}/set-default` - Set default configuration

#### Generation History
- `GET /api/v1/history` - Get history list
- `GET /api/v1/history/{id}` - Get history details
- `DELETE /api/v1/history/{id}` - Delete history
- `POST /api/v1/history/{id}/regenerate` - Regenerate data

#### Resource Library
- `GET /api/v1/resource-library/documents` - Get document resources
- `GET /api/v1/resource-library/templates` - Get template resources

---

## 💻 Development

### Backend Development

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
pytest  # Run tests (if available)
```

### Frontend Development

```bash
cd frontend
npm run dev
npm run build  # Build for production
npm run lint   # Lint code
```

### Database Migrations

Create a new migration:

```bash
cd backend
alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
alembic upgrade head
```

### Code Style

- **Python**: Follow PEP 8 style guide
- **TypeScript/React**: Use ESLint configuration

---

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Failed
**Problem**: Cannot connect to MySQL database  
**Solution**:
- Check if MySQL service is running
- Verify database connection parameters in `.env`
- Check firewall settings
- Verify database user permissions

#### Frontend API Errors
**Problem**: Frontend cannot connect to backend  
**Solution**:
- Verify backend is running on port 8000
- Check CORS configuration in backend
- Verify API base URL in frontend configuration

#### Document Upload Failed
**Problem**: Document upload fails  
**Solution**:
- Check file size (max 50MB)
- Verify file type is allowed (.md, .docx, .pdf, .txt)
- Check upload directory permissions

---

## 🤝 Contributing

We welcome all forms of contributions!

### Contribution Process

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Reporting Issues

If you find bugs or have feature suggestions, please submit them in [GitHub Issues](https://github.com/your-username/DataGenAgent/issues).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

- [AutoGen](https://github.com/microsoft/autogen) - Microsoft's AutoGen framework
- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [React](https://react.dev/) - UI library
- [Ant Design](https://ant.design/) - Enterprise-class UI component library

---

## 🌟 Support the Project

If you find DataGenAgent helpful, please give it a ⭐ **Star**!  
Your support motivates us to keep improving and maintaining the project 💙

> GitHub: [https://github.com/your-username/DataGenAgent](https://github.com/your-username/DataGenAgent)

---

## 📞 Contact

For questions or suggestions, please contact us through:

- GitHub Issues: [Submit an Issue](https://github.com/your-username/DataGenAgent/issues)
