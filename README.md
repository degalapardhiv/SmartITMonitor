# 🚀 Smart IT Monitor

<p align="center">
<b>Enterprise Real-Time IT Infrastructure Monitoring Platform</b>
</p>

Smart IT Monitor is a full-stack monitoring platform for managing devices, collecting system metrics, monitoring infrastructure health, and handling alerts in real time.

---

# 📌 Overview

Smart IT Monitor provides a centralized dashboard to monitor IT infrastructure using modern web technologies.

The platform supports:

- Real-time device monitoring
- CPU, RAM and Disk tracking
- Device health monitoring
- Alert management
- WebSocket live updates
- Infrastructure analytics
- Containerized deployment

---

# ✨ Features

## 🖥 Device Monitoring

- Device registration
- Device status tracking
- Online/offline detection
- Heartbeat monitoring
- CPU monitoring
- RAM monitoring
- Disk monitoring


## 📊 Dashboard

- Total devices overview
- Online devices
- Offline devices
- Performance statistics
- Alert analytics
- Real-time updates


## 🚨 Alert System

- Automatic alert creation
- Alert severity management
- Alert history
- Open and resolved states


## 🔐 Security

- JWT authentication
- Protected API routes
- Device agent token validation
- Role-based access control


## ⚡ Real-Time Updates

- WebSocket communication
- Live metric broadcasting
- Instant dashboard updates

---

# 🏗 Architecture

```
                 Users

                   |

                   |

            React Dashboard

                   |

                   |

            FastAPI Backend

                   |

        -------------------------

        |                       |

 PostgreSQL Database     WebSocket Server

        |

        |

 Monitoring Agents

        |

        |

 CPU / RAM / Disk Metrics
```

---

# 🛠 Tech Stack

## Frontend

- React.js
- Vite
- Tailwind CSS
- Axios
- WebSocket


## Backend

- Python
- FastAPI
- SQLAlchemy
- JWT
- Uvicorn


## Database

- PostgreSQL


## Monitoring

- Prometheus
- Grafana


## Deployment

- Docker
- Docker Compose

---

# 📂 Project Structure

```
SmartITMonitor/

├── backend/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
│
├── prometheus/
├── grafana/
├── screenshots/
├── demo/
├── docker-compose.yml
├── README.md
└── LICENSE
```

---

# 🚀 Installation

## Clone Repository

```bash
git clone https://github.com/degalapardhiv/SmartITMonitor.git

cd SmartITMonitor
```

---

# 🐳 Docker Deployment

## Build and Start

```bash
docker compose up -d --build
```

## Check Containers

```bash
docker ps
```

## Stop Application

```bash
docker compose down
```

## Restart Services

```bash
docker compose restart
```

---

# 🔧 Environment Configuration

Backend `.env`

```env
DATABASE_URL=postgresql://username:password@db:5432/database
SECRET_KEY=your_secret_key
ALGORITHM=HS256
```

Frontend `.env`

```env
VITE_API_URL=http://localhost:8000
```

---

# 🌐 Services

## Frontend Dashboard

```
http://localhost
```

## Backend API

```
http://localhost:8000
```

## API Documentation

```
http://localhost:8000/docs
```

## Grafana

```
http://localhost:3000
```

## Prometheus

```
http://localhost:9090
```

---

# 🔌 API Endpoints

## Authentication

```
POST /register

POST /login
```


## Devices

```
GET /devices

POST /devices/{id}/metrics
```


## Dashboard

```
GET /dashboard
```


## Monitoring

```
GET /metrics

GET /health
```

---

# 📡 WebSocket

Endpoint:

```
/ws
```

Used for:

- Live device updates
- Metric broadcasting
- Dashboard refresh events

---

# 📊 Monitoring Workflow

```
Device Agent

     |

Collect Metrics

     |

FastAPI Backend

     |

PostgreSQL Database

     |

WebSocket Update

     |

React Dashboard
```

---

# 📸 Screenshots

Add screenshots:

```
screenshots/dashboard.png
screenshots/devices.png
screenshots/alerts.png
```

---

# 🎥 Demo

Add demo:

```
demo/demo.gif
```

---

# 👥 Team Collaboration

| Member | GitHub | Role |
|---|---|---|
| Degala Pardhiv | https://github.com/degalapardhiv | Full Stack Development, Architecture, Deployment |
| K Maruthi Srikar | https://github.com/kmaruthisrikar | Frontend Development, UI/UX |
| Srinidhi | https://github.com/srinidhi-06-m | Backend Development, Database, Monitoring |

---

# ✅ Completion Checklist

- [x] React dashboard completed
- [x] FastAPI backend completed
- [x] PostgreSQL database integrated
- [x] JWT authentication completed
- [x] Device monitoring completed
- [x] WebSocket updates completed
- [x] Alert system completed
- [x] Prometheus integration completed
- [x] Grafana monitoring completed
- [x] Docker deployment completed
- [x] Documentation completed

---

# 🚀 Future Improvements

- Mobile application
- AI anomaly detection
- Cloud deployment
- Kubernetes support
- Email notifications
- Telegram alerts

---

# 📄 License

MIT License

---

# 👨‍💻 Author

## Degala Pardhiv

GitHub:
https://github.com/degalapardhiv

Project:
https://github.com/degalapardhiv/SmartITMonitor

---

Built with ❤️ by Smart IT Monitor Team
