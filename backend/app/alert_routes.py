from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .database import SessionLocal
from .alert_model import Alert


router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()



@router.get("/")
def get_alerts(
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db)
):

    offset = (page - 1) * limit


    alerts = (
        db.query(Alert)
        .order_by(
            Alert.created_at.desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


    return alerts


    return (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(100)
        .all()
    )



@router.get("/history")
def alert_history(
    db: Session = Depends(get_db)
):

    alerts = (
        db.query(Alert)
        .order_by(Alert.created_at.asc())
        .all()
    )

    return [
        {
            "id": alert.id,
            "hostname": alert.hostname,
            "type": alert.alert_type,
            "value": alert.value,
            "severity": alert.severity,
            "created_at": alert.created_at
        }
        for alert in alerts
    ]


@router.patch("/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):

    alert = (
        db.query(Alert)
        .filter(
            Alert.id == alert_id
        )
        .first()
    )


    if not alert:

        return {
            "error":"Alert not found"
        }


    alert.status = "RESOLVED"


    db.commit()


    return {
        "status":"resolved",
        "id":alert_id
    }


from datetime import datetime, timedelta


@router.delete("/cleanup")
def cleanup_alerts(
    db: Session = Depends(get_db)
):

    old_date = (
        datetime.utcnow()
        -
        timedelta(days=30)
    )


    deleted = (
        db.query(Alert)
        .filter(
            Alert.created_at < old_date,
            Alert.status == "RESOLVED"
        )
        .delete()
    )


    db.commit()


    return {
        "deleted": deleted
    }


@router.get("/analytics")
def alert_analytics(
    db: Session = Depends(get_db)
):

    from sqlalchemy import func


    severity = (
        db.query(
            Alert.severity,
            func.count(Alert.id)
        )
        .group_by(
            Alert.severity
        )
        .all()
    )


    alert_types = (
        db.query(
            Alert.alert_type,
            func.count(Alert.id)
        )
        .group_by(
            Alert.alert_type
        )
        .all()
    )


    return {

        "severity": [
            {
                "name":x[0],
                "value":x[1]
            }
            for x in severity
        ],


        "types": [
            {
                "name":x[0],
                "value":x[1]
            }
            for x in alert_types
        ]

    }


@router.get("/notifications/history")
def notification_history(
    db: Session = Depends(get_db)
):

    from app.notification_history_model import NotificationHistory


    return (

        db.query(NotificationHistory)

        .order_by(
            NotificationHistory.created_at.desc()
        )

        .limit(100)

        .all()

    )
