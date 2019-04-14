import config
import sys
import csv
import requests
import json
from datetime import datetime
import logging
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from sqlalchemy.schema import CreateSchema
from sqlalchemy import DDL

#Logging set-up
today =  datetime.now().isoformat(timespec='minutes')
logfilename = f'import-{today}.log'
logging.basicConfig(filename=logfilename,level=logging.INFO)

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
    ad_name = Column(String)
    edition = Column(String)
    lead_source = Column(String)

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

def progress(count, total, status=''):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))

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

def get_data_from_csv(filename, lead_source):
    with open(filename, 'rt') as csvfile:
        reader = csv.DictReader(csvfile)
        leads = []
        for row in reader:
            lead = {
                'email': row['email'], 
                'ad_name': row['ad_name'], 
                'edition': row['which_edition_would_you_like?'],
                'lead_source': lead_source
            }
            leads.append(lead) 
    return leads

def search_for_subscriber(lead):
    email = lead['email']
    searchforsub = {'email': email}
    endpointforsubs = 'https://secure.whatcounts.net/rest/subscribers'

    r = requests.get(endpointforsubs, params=searchforsub, auth=(config.wc_realm, config.wc_realmpw))
    # Request returns a list with one object
    subscriber_data = r.json()
    return subscriber_data

def store_subscriber_data(lead):
    s = lead['wc_data'][0]
    new_lead = get_or_create(session, Lead, 
        email=lead['email'],
        subscriberid=s['subscriberId'],
        ad_name=lead['ad_name'],
        edition=lead['edition'],
        lead_source=lead['lead_source']
    )
    return new_lead

def get_subscriber_events(subscriberid):
    # Docs: https://support.whatcounts.com/hc/en-us/articles/210396566-Report-Subscriber-Events-by-Subscriber-ID
    # Endpoint: https://[siteurl]/rest/subcribers/[subscriberId]/events?querystring
    # Query options: 
    # start=[yyyy-mm-dd]
    # end=[yyyy-mm-dd]
    # eventType=[eventType]
    searchforevents = {'start': '2019-03-01'}
    endpointforevents = f'https://secure.whatcounts.net/rest/subscribers/{subscriberid}/events'
    r = requests.get(endpointforevents, params=searchforevents, auth=(config.wc_realm, config.wc_realmpw))
    events_obj = r.json()
    return events_obj

def store_events_data(events_obj):
    records = []
    events = events_obj["events"]
    for event in events:
        record = get_or_create(session, Event, 
            trackingid = event["trackingId"],
            subscriberid = events_obj["subscriberId"],
            trackingeventdate = event["trackingEventDate"],
            trackingcampaign = event["trackingCampaignId"],
            trackingeventtype = event["eventType"],
            trackingclickthroughid = event["trackingClickthroughId"]
        )
    records.append(record)
    return records
    
if __name__ == '__main__':
    emails_not_in_wc = []
    emails_already_seen = []
    emails_no_events = []
    email_duplicates = []
    # TODO Set a default filename, e.g., leads.csv
    filename = sys.argv[1]
    lead_source = sys.argv[2]
    leads = get_data_from_csv(filename, lead_source)
    i = 0
    for lead in leads:
        progress(i, len(leads), status="Processing...")
        i += 1
        logging.info("========================================================================")
        logging.info("Lead: %s", lead['email'])
        # Check that we're not trying to re-process a duplicate email
        if lead['email'] in emails_already_seen:
            email_duplicates.append(lead['email'])
            logging.info("Already processed %s", lead['email'])
            continue
        emails_already_seen.append(lead['email'])
        # Search for a match in WC
        lead['wc_data'] = search_for_subscriber(lead)
        if len(lead['wc_data']) > 0:
            logging.info("Found a sub for %s", lead['email'])
        else:
            emails_not_in_wc.append(lead['email'])
            logging.info("No WC record found for %s ... moving on", lead['email'])
            continue
        #If matched, store the data, get back the id
        lead_record = store_subscriber_data(lead)
        # print("Stored:", lead_record)
        # # Lookup the events for the id
        events_obj = get_subscriber_events(lead_record.subscriberid)
        if len(events_obj['events']) > 0:
            logging.info("We got %s events", len(events_obj["events"]))
        else:
            emails_no_events.append(lead_record.email)
            logging.info("No events found for %s", lead_record.email)
            continue
        results = store_events_data(events_obj)
        count = session.query(Event).filter(Event.subscriberid == lead_record.subscriberid).count()
        logging.info("We stored %s events for %s in the db", count, lead['email'])
    # Finishing up with a summary
    logging.info("////////////////////////////////////////////////////////////////////////////////")
    logging.info("We saw %s emails and %s duplicates on this run", len(emails_already_seen), len(email_duplicates))
    if len(email_duplicates) > 0: 
        logging.info("Duplicates found in import file:")
        for dup in email_duplicates:
            logging.info("* %s", dup)
    if len(emails_no_events) > 0:
        logging.info("No events found for these leads:")
        for ne in emails_no_events:
            logging.info("* %s", ne)
    if len(emails_not_in_wc) > 0:
        logging.info("Not found in WhatCounts:")
        for missing in emails_not_in_wc:
            logging.info("* %s", missing)