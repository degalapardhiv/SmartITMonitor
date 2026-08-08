#!/bin/bash

DATE=$(date +"%Y-%m-%d_%H-%M-%S")

mkdir -p backups

docker exec smart-monitor-db \
pg_dump -U smartadmin smart_monitor \
> backups/smart_monitor_$DATE.sql

echo "Backup created: backups/smart_monitor_$DATE.sql"
