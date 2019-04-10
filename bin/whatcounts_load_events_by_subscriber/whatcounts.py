import config
import sys
import requests
import json
import datetime
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
Session = sessionmaker()

Base = declarative_base()
db_url = f'postgresql+psycopg2://{config.db_user}:{config.db_pass}@localhost/{config.db_name}'

engine = sqlalchemy.create_engine(db_url)
Session.configure(bind=engine)
session = Session()

class Lead(Base):
    __tablename__ = 'leads'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    subscriberid = Column(Integer, unique=True)

    def __repr__(self):
        return "<Lead(email='%s', subscriberId='%s')>" % (self.email, self.subscriberid)

class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    trackingid = Column(Integer, unique=True)
    subscriberid = Column(Integer, ForeignKey(Lead.subscriberid))
    trackingeventdate = Column(DateTime())
    trackingcampaign = Column(Integer)
    trackingeventtype = Column(String)
    trackingclickthroughid = Column(Integer)

    lead = relationship("Lead", back_populates="events")

    def __repr__(self):
        return "<Event(subscriberid='%s', eventtype='%s')>" % (self.subscriberid, self.eventtype)

Lead.events = relationship("Event", order_by=Event.trackingid, back_populates="lead")

Base.metadata.create_all(engine)

# Generic upsert
def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance

# TODO 
# - Load records from CSV
# - Search for each record in WC
# - If it's there, store the record's event


# TODO move into function
searchforsub = {'email': ''}
endpointforsubs = 'https://secure.whatcounts.net/rest/subscribers'

r = requests.get(endpointforsubs, params=searchforsub, auth=(config.wc_realm, config.wc_realmpw))

# Request returns a list with one object
subscribers = r.json()
# Get the object
subscriber = subscribers[0]
print(subscriber)

# Get the ID
subscriberid = subscriber["subscriberId"]
email = subscriber["email"]

# new_lead = Lead(email=email, subscriberid=subscriberid)
new_lead = get_or_create(session, Lead, email=email, subscriberid=subscriberid)
print(new_lead)

# TODO Move into function
# Docs: https://support.whatcounts.com/hc/en-us/articles/210396566-Report-Subscriber-Events-by-Subscriber-ID
# Endpoint: https://[siteurl]/rest/subcribers/[subscriberId]/events?querystring
# Query options: 
# start=[yyyy-mm-dd]
# end=[yyyy-mm-dd]
# eventType=[eventType]
searchforevents = {'start': '2019-03-01', 'eventType': 'SENT'}
endpointforevents = f'https://secure.whatcounts.net/rest/subscribers/{subscriberid}/events'
r = requests.get(endpointforevents, params=searchforevents, auth=(config.wc_realm, config.wc_realmpw))
eventsjson = r.json()
events = eventsjson["events"]

for event in events:
    print (event)
    get_or_create(session, Event, 
        trackingid = event["trackingId"],
        subscriberid = subscriberid,
        trackingeventdate = event["trackingEventDate"],
        trackingcampaign = event["trackingCampaignId"],
        trackingeventtype = event["eventType"],
        trackingclickthroughid = event["trackingClickthroughId"]
    )