
import config
import sys
import requests
import json
from datetime import datetime
import logging
from models import Base, Lead, Event, Transaction
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from sqlalchemy.schema import CreateSchema
from sqlalchemy import DDL
import recurly

# Logging set-up
today = datetime.now().isoformat(timespec='minutes')
logfilename = f'rucurly-{today}.log'
logging.basicConfig(filename=logfilename, level=logging.INFO)

db_url = f'postgresql+psycopg2://{config.db_user}:{config.db_pass}@localhost/{config.db_name}'
engine = sqlalchemy.create_engine(db_url)

# Database session
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()

recurly.SUBDOMAIN = config.recurly_subdomain
recurly.API_KEY = config.recurly_apikey
recurly.DEFAULT_CURRENCY = 'USD'

for instance in session.query(Lead).order_by(Lead.id):
    try:
        account = recurly.Account.get(instance.email)
        logging.info("Found record for %s", instance.email)
    except:
        logging.info("Account not found for %s", instance.email)
    else: 
        instance.recurly_entry = True
        instance.recurly_created = account.created_at
        instance.recurly_subscription = account.has_active_subscription
        for transaction in account.transactions():
            instance.transactions.append(Transaction(
                transactionid=transaction.uuid,
                created_at=transaction.created_at,
                action=transaction.action,
                amount_in_cents=transaction.amount_in_cents,
                status=transaction.status
            ))
            session.commit()