#import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

# Database classes
class Lead(Base):
    __tablename__ = 'leads'
    __table_args__ = {'schema': 'leadtracking'}

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    subscriberid = Column(Integer, unique=True)
    ad_name = Column(String)
    edition = Column(String)
    lead_source = Column(String)
    wc_data = Column(JSON)
    recurly_entry = Column(Boolean, default=False)
    recurly_created = Column(DateTime())
    recurly_subscription = Column(Boolean, default=False)

    def __repr__(self):
        return "<Lead(email='%s', subscriberId='%s')>" % (self.email, self.subscriberid)

class Event(Base):
    __tablename__ = 'events'
    __table_args__ = {'schema': 'leadtracking'}
    
    id = Column(Integer, primary_key=True)
    trackingid = Column(Integer, unique=True)
    subscriberid = Column(Integer, ForeignKey(Lead.subscriberid))
    trackingeventdate = Column(DateTime())
    trackingcampaign = Column(Integer)
    trackingeventtype = Column(String)
    trackingclickthroughid = Column(Integer)

    lead = relationship("Lead", back_populates="events")

    def __repr__(self):
        return "<Event(subscriberid='%s', eventtype='%s')>" % (self.subscriberid, self.trackingeventtype)

class Transaction(Base):
    __tablename__ = 'transactions'
    __table_args__ = {'schema': 'leadtracking'}
    
    id = Column(Integer, primary_key=True)
    transactionid = Column(String, unique=True)
    subscriberid = Column(Integer, ForeignKey(Lead.subscriberid))
    created_at = Column(DateTime())
    action = Column(String)
    amount_in_dollars = Column(Integer)
    status = Column(String)

    lead = relationship("Lead", back_populates="transactions")

# Create the relationship between tables
Lead.events = relationship("Event", order_by=Event.trackingid, back_populates="lead")
Lead.transactions = relationship("Transaction", order_by=Transaction.transactionid, back_populates="lead")