
import config
import sys
import pprint
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

pp = pprint.PrettyPrinter(indent=4)

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

# Recurly configuration
recurly.SUBDOMAIN = config.recurly_subdomain
recurly.API_KEY = config.recurly_apikey
recurly.DEFAULT_CURRENCY = 'USD'

##################
# Functions
##################

# Generic progress bar
def progress(count, total, status=''):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
    
# Generic upsert for adding records to the database
def get_or_create(session, model, **kwargs):
    if model.__name__ == 'Transaction':
        unique_key = kwargs['transactionid']
        instance = session.query(model).filter_by(transactionid=unique_key).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance

def check_leads_for_matching_recurly_account(lead):
    try:
        account = recurly.Account.get(lead.email)
        logging.info("Found record for %s", lead.email)
        print("Found record for", lead.email)
        return account
    except:
        logging.info("Account not found for %s", lead.email)

def update_account_status(lead, account):
    lead.recurly_entry = True
    lead.recurly_created = account.created_at
    lead.recurly_subscription = account.has_active_subscription
    session.commit()

def store_transaction(transaction, lead):
        trans_obj = get_or_create(session, Transaction, 
            transactionid=transaction.uuid,
            created_at=transaction.created_at,
            action=transaction.action,
            amount_in_dollars=transaction.amount_in_cents/100,
            status=transaction.status,
            subscriberid=lead.subscriberid
        )
        return trans_obj.transactionid


if __name__ == '__main__':
    # Get leads from db
    leads = session.query(Lead).order_by(Lead.id)
    # leads = session.query(Lead).filter(Lead.email == '')
    leads_count = leads.count()
    print("Got ", leads_count)
    logging.info("Got %s leads", leads_count)


    accounts = []
    i = 0
    for lead in leads:
        progress(i, leads_count, status="Processing...")
        i += 1
        # Get matching Recurly account
        account = check_leads_for_matching_recurly_account(lead)
        if account:
            update_account_status(lead, account)
            accounts.append(account)
    
    print("Got accounts:", len(accounts))
    
    # Store all transactions for each account found
    transactions = []
    j = 0
    for account in accounts:
        progress(j, len(accounts), status="Processing...")
        j += 1
        trans_len = 0
        for transaction in account.transactions():
            trans_len += 1
            lead = session.query(Lead).filter(Lead.email == account.account_code).first()
            trans_id = store_transaction(transaction, lead)
            transactions.append(trans_id)
        print("Stored", trans_len, "transactions for ", account.account_code  )
    print("Totoal transactions stored:", len(transactions))
    logging.info("Total transactions stored: %s", len(transactions))
