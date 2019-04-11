import config
import sys
import csv
import requests
import json
import datetime
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from sqlalchemy.schema import CreateSchema
from sqlalchemy import DDL

# Database set-up
Base = declarative_base()

# Don't try to re-create the schema if it exists
event.listen(Base.metadata, 'before_create', DDL("CREATE SCHEMA IF NOT EXISTS whatcounts"))
db_url = f'postgresql+psycopg2://{config.db_user}:{config.db_pass}@localhost/{config.db_name}'
engine = sqlalchemy.create_engine(db_url)

Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

# Database classes
class Lead(Base):
    __tablename__ = 'leads'
    __table_args__ = {'schema': 'whatcounts'}

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    subscriberid = Column(Integer, unique=True)

    def __repr__(self):
        return "<Lead(email='%s', subscriberId='%s')>" % (self.email, self.subscriberid)

class Event(Base):
    __tablename__ = 'events'
    __table_args__ = {'schema': 'whatcounts'}
    
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

# Create the relationship between tables
Lead.events = relationship("Event", order_by=Event.trackingid, back_populates="lead")

# Create the tables (and schema) if necessary
Base.metadata.create_all(engine)

##################
# Functions
##################

# Generic upsert for adding records to the database
def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance

def get_data_from_csv(filename):
    with open(filename, 'rt') as csvfile:
        reader = csv.DictReader(csvfile)
        leads = []
        for row in reader:
            leads.append(row['email']) 
    return leads

def search_for_subscriber(identifier):
    searchforsub = {'email': ''}
    endpointforsubs = 'https://secure.whatcounts.net/rest/subscribers'

    r = requests.get(endpointforsubs, params=searchforsub, auth=(config.wc_realm, config.wc_realmpw))

    # Request returns a list with one object
    subscribers = r.json()
    # Get the object
    subscriber = subscribers[0]

    # Get the ID
    subscriberid = subscriber["subscriberId"]
    email = subscriber["email"]

def store_subscriber_data(subscriber):
    new_lead = get_or_create(session, Lead, email=email, subscriberid=subscriberid)

def get_subscriber_events(subscriberid):
    # TODO Move into function
    # Docs: https://support.whatcounts.com/hc/en-us/articles/210396566-Report-Subscriber-Events-by-Subscriber-ID
    # Endpoint: https://[siteurl]/rest/subcribers/[subscriberId]/events?querystring
    # Query options: 
    # start=[yyyy-mm-dd]
    # end=[yyyy-mm-dd]
    # eventType=[eventType]
    searchforevents = {'start': '2019-03-01'}
    endpointforevents = f'https://secure.whatcounts.net/rest/subscribers/{subscriberid}/events'
    r = requests.get(endpointforevents, params=searchforevents, auth=(config.wc_realm, config.wc_realmpw))
    eventsjson = r.json()
    events = eventsjson["events"]

def store_events_data(events):
    for event in events:
        records = get_or_create(session, Event, 
            trackingid = event["trackingId"],
            subscriberid = subscriberid,
            trackingeventdate = event["trackingEventDate"],
            trackingcampaign = event["trackingCampaignId"],
            trackingeventtype = event["eventType"],
            trackingclickthroughid = event["trackingClickthroughId"]
        )

if __name__ == '__main__':
    # TODO
    # Set a default filename, e.g., leads.csv
    filename = sys.argv[1]
    leads = get_data_from_csv(filename)
    for lead in leads:
        # Search for a match in WC
        # If matched, store the data, get back the id
        # Lookup the events for the id
        # Store the events
        print("WIP")