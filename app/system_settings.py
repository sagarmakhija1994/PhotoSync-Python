# app/system_settings.py

from sqlalchemy.orm import Session
from app.models import SystemSetting


def get_setting(db: Session, key: str, default: str | None = None) -> str | None:
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = SystemSetting(key=key, value=value)
        db.add(setting)
