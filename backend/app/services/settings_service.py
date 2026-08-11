from sqlalchemy.orm import Session

from ..monitor_settings_model import MonitorSetting


DEFAULT_SETTINGS = {
    "cpu_threshold": "80",
    "ram_threshold": "90",
    "disk_threshold": "90",
    "alert_cooldown_minutes": "5",
    "scan_ranges": "{}",
}


def get_setting(db: Session, key):
    setting = (
        db.query(MonitorSetting)
        .filter(MonitorSetting.key == key)
        .first()
    )

    if setting:
        return setting.value

    return None


def set_setting(db: Session, key, value):
    setting = (
        db.query(MonitorSetting)
        .filter(MonitorSetting.key == key)
        .first()
    )

    if setting is None:
        setting = MonitorSetting(
            key=key,
            value=str(value),
        )
        db.add(setting)
    else:
        setting.value = str(value)

    db.commit()

    return setting.value


def _ensure_defaults(db: Session):
    for key, default in DEFAULT_SETTINGS.items():
        if get_setting(db, key) is None:
            set_setting(db, key, default)


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_alert_thresholds(db: Session):
    _ensure_defaults(db)

    return {
        "cpu_threshold": _parse_int(
            get_setting(db, "cpu_threshold"),
            80,
        ),
        "ram_threshold": _parse_int(
            get_setting(db, "ram_threshold"),
            90,
        ),
        "disk_threshold": _parse_int(
            get_setting(db, "disk_threshold"),
            90,
        ),
        "alert_cooldown_minutes": _parse_int(
            get_setting(db, "alert_cooldown_minutes"),
            5,
        ),
    }


def save_alert_thresholds(db: Session, cpu, ram, disk, cooldown):
    set_setting(db, "cpu_threshold", cpu)
    set_setting(db, "ram_threshold", ram)
    set_setting(db, "disk_threshold", disk)
    set_setting(db, "alert_cooldown_minutes", cooldown)

    return get_alert_thresholds(db)


def get_scan_ranges(db: Session):
    _ensure_defaults(db)

    raw = get_setting(db, "scan_ranges")

    import json

    try:
        ranges = json.loads(raw)
    except (TypeError, ValueError):
        ranges = []

    if not isinstance(ranges, list):
        ranges = []

    return [
        item
        for item in ranges
        if isinstance(item, str) and item.strip()
    ]


def save_scan_ranges(db: Session, ranges):
    import json

    clean = [
        item.strip()
        for item in ranges
        if isinstance(item, str) and item.strip()
    ]

    set_setting(db, "scan_ranges", json.dumps(clean))

    return clean