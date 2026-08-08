# 🚀 Smart IT Monitor

<p align="center">
  <b>Enterprise Real-Time IT Infrastructure Monitoring Dashboard</b>
</p>

<p align="center">
  A full-stack monitoring platform for tracking devices, system performance, alerts, and infrastructure health in real time.
</p>

<p align="center">

![Status](https://img.shields.io/badge/Status-Production%20Ready-success)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)
![React](https://img.shields.io/badge/Frontend-React-blue)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue)
![Prometheus](https://img.shields.io/badge/Monitoring-Prometheus-orange)
![Grafana](https://img.shields.io/badge/Visualization-Grafana-red)

</p>

---

# 📌 Overview

Smart IT Monitor is an enterprise-style IT infrastructure monitoring system designed to monitor connected devices, collect performance metrics, manage alerts, and visualize infrastructure health through a modern dashboard.

The platform provides real-time visibility into:

- Device health
- CPU usage
- RAM utilization
- Disk usage
- Alerts
- System performance
- Infrastructure status

Built using modern full-stack technologies, Smart IT Monitor combines a React dashboard, FastAPI backend, PostgreSQL database, WebSocket communication, and containerized deployment.

---

# ✨ Features

## 📊 Real-Time Monitoring

- Live CPU monitoring
- RAM usage tracking
- Disk usage tracking
- Device health monitoring
- Real-time WebSocket updates
- Live dashboard statistics
- Performance history tracking


## 🖥️ Device Management

- Device registration
- Device information tracking
- Online/offline status
- Last heartbeat monitoring
- Agent-based metric collection
- Device performance monitoring


## 🚨 Alert Management

- Automatic alert creation
- Alert severity levels
- Alert history tracking
- Open and resolved alerts
- Alert analytics dashboard


## 🔐 Authentication & Security

- JWT authentication
- Protected API routes
- Role-based access control
- Secure device agent tokens


------

# 🏗️ System Architecture

                     Users
                       |
                       |
               React Dashboard
                       |
                       |
                FastAPI Backend
                       |
    ------------------------------------
    |                                  |
    PostgreSQL Database WebSocket Server
| |
| |
Device Monitoring Agents Real-Time Updates
|
|
CPU / RAM / Disk Metrics


---

# 🛠️ Technology Stack


## Frontend

| Technology | Purpose |
|---|---|
| React.js | Dashboard Interface |
| Vite | Frontend Build Tool |
| Tailwind CSS | UI Styling |
| Axios | API Communication |
| WebSocket | Real-Time Updates |


## Backend

| Technology | Purpose |
|---|---|
| Python | Backend Language |
| FastAPI | REST API Framework |
| SQLAlchemy | Database ORM |
| JWT | Authentication |
| Uvicorn | API Server |


## Database

| Technology | Purpose |
|---|---|
| PostgreSQL | Data Storage |


## Monitoring

| Technology | Purpose |
|---|---|
| Prometheus | Metrics Collection |
| Grafana | Visualization |


## Deployment

| Technology | Purpose |
|---|---|
| Docker | Containerization |
| Docker Compose | Multi-Service Deployment |

---

# 📂 Project Structure


```text
SmartITMonitor/

│
├── backend/
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth.py
│   │   ├── security.py
│   │   └── services/
│   │
│   ├── Dockerfile
│   └── requirements.txt
│
│
├── frontend/
│   │
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── assets/
│   │
│   ├── Dockerfile
│   └── package.json
│
│
├── screenshots/
│
├── demo/
│
├── docker-compose.yml
│
├── README.md
│
└── LICENSE

🚀 Installation & Setup
Clone Repository
git clone https://github.com/degalapardhiv/SmartITMonitor.git

cd SmartITMonitor

Start Application Using Docker

Build and start all services:

docker compose up -d

Check running containers:

docker ps

Stop services:

docker compose down

---

# 🌐 Application Services


## Frontend Dashboard

Access:

```text
http://localhost

The dashboard provides:

Device overview
Live monitoring
Performance statistics
Alert information
System analytics
Backend API

Access:

http://localhost:8000

FastAPI documentation:

http://localhost:8000/docs

Available API features:

Authentication
Device management
Metrics collection
Dashboard data
Alert management

Grafana Monitoring

Access:

http://localhost:3000

Used for:

Infrastructure visualization
Metrics dashboards
Performance analytics

Prometheus Monitoring

Access:

http://localhost:9090

Used for:

Metrics collection
Monitoring queries
System health tracking

🔌 API Endpoints
Authentication

Register user:

POST /register

Login:

POST /login

Returns:

{
  "access_token": "JWT_TOKEN",
  "token_type": "bearer"
}

Device APIs

Get devices:

GET /devices

Send device metrics:

POST /devices/{id}/metrics

Example:

curl -X POST \
"http://localhost:8000/devices/1/metrics?cpu=20&ram=60&disk=40" \
-H "x-agent-token: DEVICE_TOKEN"

Dashboard API

Get dashboard statistics:

GET /dashboard

Response example:

{
 "total":10,
 "online":8,
 "offline":2,
 "alerts":5
}

Monitoring API

Prometheus metrics:

GET /metrics

Health check:

GET /health

📊 Dashboard Modules
Device Overview

Displays:

Total devices
Online devices
Offline devices
Device status
Performance Monitoring

Displays:

CPU usage
RAM usage
Disk usage
Live updates
Alert Dashboard

Displays:

Alert count
Severity
Alert history
Alert status

---

# 📸 Project Screenshots


## Dashboard Overview

![Dashboard](screenshots/dashboard.png)


## Device Monitoring

![Devices](screenshots/devices.png)


## Alert Management

![Alerts](screenshots/alerts.png)


---

# 🎥 Demo Preview


Live dashboard demonstration:


![Smart IT Monitor Demo](demo/demo.gif)


---

# 🔒 Security Features


Smart IT Monitor includes multiple security mechanisms:


## Authentication Security

- JWT-based authentication
- Secure user sessions
- Protected API routes
- Token verification


## Device Security

- Unique agent tokens
- Secure metric submission
- Device authentication


## Access Control

- Role-based permissions
- Authorized dashboard access
- Protected monitoring endpoints


---

# 📈 Monitoring Workflow

 |
 Device Agent

 |
 |

Collect Metrics

 |
 |

FastAPI Backend

 |
 |

Store Data

 |
 |

PostgreSQL Database

 |
 |

React Dashboard

 |
 |

Real-Time Visualization



---

# ⚙️ Configuration


## Environment Variables


Backend configuration example:


```env
DATABASE_URL=postgresql://username:password@db:5432/database

SECRET_KEY=your_secret_key

ALGORITHM=HS256

Frontend configuration:

VITE_API_URL=http://localhost:8000
🐳 Docker Services

The application runs using multiple containers:

Container	Purpose
Frontend	React Dashboard
Backend	FastAPI API Server
Database	PostgreSQL
Prometheus	Metrics Collection
Grafana	Monitoring Dashboard

🧪 Testing

Health check:

curl http://localhost:8000/health

Dashboard API:

curl http://localhost:8000/dashboard

Check containers:

docker ps

View backend logs:

docker logs smart-monitor-api

View frontend logs:

docker logs smart-monitor-ui

---

# 👥 Team Collaboration


Smart IT Monitor was collaboratively developed by a team of three members.

The project was built through teamwork involving frontend development, backend engineering, database design, monitoring integration, testing, and deployment.


## Team Members


| Member | GitHub | Contribution |
|---|---|---|
| Degala Pardhiv | https://github.com/degalapardhiv | Full Stack Development, Backend Architecture, Integration, Deployment |
| K Maruthi Srikar | https://github.com/kmaruthisrikar | Frontend Development, UI/UX Design, Testing |
| Srinidhi | https://github.com/srinidhi-06-m | Backend Development, Database Management, Monitoring Features |


---

# 🤝 Collaboration Areas


The team worked together on:


### System Design

- Application architecture planning
- Database structure design
- API workflow planning


### Frontend Development

- Dashboard interface
- Responsive UI
- Device monitoring views
- Data visualization


### Backend Development

- FastAPI services
- Authentication system
- Device APIs
- WebSocket implementation


### Database

- PostgreSQL integration
- Data models
- Device and alert storage


### Monitoring

- Prometheus integration
- Grafana dashboards
- Performance tracking


### Deployment

- Docker configuration
- Container management
- Production setup


---

# ✅ Project Completion Checklist


- [x] Project architecture designed
- [x] React dashboard completed
- [x] FastAPI backend completed
- [x] PostgreSQL database integrated
- [x] JWT authentication implemented
- [x] User management implemented
- [x] Device monitoring completed
- [x] Device agent integration completed
- [x] Real-time WebSocket updates completed
- [x] CPU monitoring completed
- [x] RAM monitoring completed
- [x] Disk monitoring completed
- [x] Alert management completed
- [x] Prometheus metrics completed
- [x] Grafana monitoring completed
- [x] Docker deployment completed
- [x] Documentation completed


---

# 🚀 Future Improvements


Planned enhancements:


## Mobile Application

- Android application
- Push notifications
- Mobile monitoring


## AI Monitoring

- Anomaly detection
- Predictive analysis
- Smart alerts


## Cloud Deployment

- AWS deployment
- Kubernetes support
- Scalable infrastructure


## Advanced Security

- Two-factor authentication
- Improved access control
- Security audit logs


## More Integrations

- Email notifications
- Telegram alerts
- Slack notifications


---
---

# 📄 License


This project is licensed under the MIT License.


MIT License allows you to:

- Use the software
- Modify the software
- Distribute the software
- Use it for personal and commercial projects


See the `LICENSE` file for more details.


---

# 👨‍💻 Author


## Degala Pardhiv


GitHub:

https://github.com/degalapardhiv


LinkedIn:

(Add your LinkedIn profile link)


---

# 📌 Project Repository


GitHub:

https://github.com/degalapardhiv/SmartITMonitor


---

# ⭐ Support


If you find this project useful:

- Star the repository
- Share the project
- Provide feedback
- Contribute improvements


---

# 🙏 Acknowledgements


Special thanks to:

- Open-source community
- FastAPI community
- React community
- Docker community
- Prometheus and Grafana communities


---

# 🏆 Project Highlights


Smart IT Monitor demonstrates practical implementation of:


✅ Full-stack web development  
✅ Backend API engineering  
✅ Database architecture  
✅ Real-time communication  
✅ System monitoring  
✅ DevOps practices  
✅ Container deployment  
✅ Team collaboration  


---

<p align="center">

<b>Built with ❤️ by the Smart IT Monitor Team</b>

</p>

---
