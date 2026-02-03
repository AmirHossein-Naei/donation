import time

from sqlalchemy import Column, Integer, String, Boolean

from ext import db

def get_current_time():
    return int(time.time())

class Payment(db.Model):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    phone = Column(String, index=True)
    description = Column(String)
    amount = Column(Integer, index=True)
    show_in_livestream = Column(Boolean, index=True)
    show_desc_in_livestream = Column(Boolean)
    show_in_list = Column(Boolean, index=True)

    gateway = Column(String)
    refid = Column(String, nullable=True)
    auth = Column(String, nullable=True)

    time_created = Column(String, default=get_current_time)

    shown_in_live_stream=Column(Boolean, index=True, default=False)

    def to_dict(self):
        data = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            data[column.name] = value
        return data