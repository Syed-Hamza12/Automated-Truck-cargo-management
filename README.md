<div align="center">

# 🚛 TruckFlow

### Fleet Management System with AI, Celery Automation & RAG Intelligence

[Django] [Celery] [Redis] [PostgreSQL] [Docker] [WebSocket] [RAG]

---

</div>

## 📌 Overview

TruckFlow is a **role-based fleet management system** designed for cargo logistics operations.

It integrates:

- Real-time fleet tracking
- Automated maintenance workflows
- Celery-based background processing
- AI chatbot with RAG-based fleet intelligence
- Multi-role dashboards (Driver, Dispatcher, Fleet Manager, Owner)

---

## 🧠 Key Features

### 🚚 Fleet Operations
- Truck lifecycle management
- Driver assignment system
- Load dispatching workflow
- Vendor & parts tracking

### 🔧 Maintenance Automation
- Preventive maintenance scheduling (Celery Beat)
- Repair workflow system
- Downtime tracking & cost calculation
- Automatic alerts for overdue maintenance

### 📊 Business Intelligence
- Fleet cost per truck calculation
- Downtime revenue loss estimation
- Utilization analytics
- Vendor performance tracking

### ⚙️ AI System (RAG + Agent)
- Natural language fleet queries
- Maintenance & cost reports generation
- Dispatch recommendations
- Anomaly detection on truck cost behavior
- Context-aware responses using PostgreSQL + pgvector

---

## 🤖 AI Capabilities

### Example Queries:

- “Which trucks need maintenance this week?”
- “Show cost breakdown for TRK-12”
- “Why did downtime increase last month?”
- “Assign best truck for 800kg shipment”

### AI Pipeline:
User Query
↓
RAG Retriever (pgvector)
↓
Django ORM Live Data
↓
LLM Agent (tool-based reasoning)
↓
Action / Report / Response


---

## ⚙️ System Architecture


Frontend (React)
↓
Django API 
↓
PostgreSQL (Core Data)
Redis (Queue + Cache)
↓
Celery Workers
├── Alerts Worker
├── Maintenance Worker
├── ML Worker
├── Report Worker
└── RAG Indexer
↓
AI Layer (Agent + RAG + Tools)


---

## 👥 Role-Based Dashboards

| Role | Dashboard | Responsibilities |
|------|----------|------------------|
| Driver | `/dashboard/driver` | Trip updates, issue reporting |
| Dispatcher | `/dashboard/dispatcher` | Load assignment |
| Maintenance | `/dashboard/maintenance` | Repairs & servicing |
| Fleet Manager | `/dashboard/fleet` | Fleet health monitoring |
| Operations | `/dashboard/operations` | KPIs & cost tracking |
| Owner | `/dashboard/owner` | Business intelligence |

---

## ⚙️ Async Task System (Celery)

- PM scheduling automation
- Downtime calculation
- Alert generation engine
- ML prediction jobs
- Nightly RAG indexing

Priority queues:
- Critical (truck breakdowns)
- High (maintenance overdue)
- Normal (reports & scheduling)
- Low (analytics & cleanup)

---

## 🧠 AI Modules


ai/
├── agent.py # LLM orchestration layer
├── rag.py # vector retrieval system
├── tools/ # DB, alerts, report tools
└── prompts/ # role-based system prompts


---

## 🔄 Event-Driven Design

- Django Signals trigger business events
- Celery processes async workflows
- WebSocket updates dashboards in real-time

Example:

Truck breakdown → Event → Alert → Downtime → AI analysis → Dashboard update


---

## 🐳 Tech Stack

- Django 4.2 + DRF
- Celery + Redis
- PostgreSQL + pinecorn_vector_db
- WebSockets (Django Channels)
- Docker 
- LangChain (AI Agent layer)
- OpenAI / LLM API
- Machine Learning model
---
