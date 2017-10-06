#!/usr/bin/python

import boto3
import csv
import time
import simplejson as json
from dateutil.parser import parse
import datetime
import logging
import botocore
import getopt
import sys
import os

logging.basicConfig(
    filename='/tmp/aws_credentials_report.log',
    level=logging.WARN,
    format='%(asctime)s %(levelname)s: [aws_credentials_report:%(lineno)d] %(message)s')
logfile = '/var/log/aws/aws_credentials-' + str(datetime.datetime.now().date()) + '.log'


def init_session(account):
        logging.info('Initiating new session. aws_account=' + account)
        s = boto3.session.Session(profile_name=account, region_name='us-east-1')
        return s.client('iam')


def get_cred_report(account):
    client = init_session(account)
    # TODO Check if credit report already exist
    try:
        client.generate_credential_report()
    except botocore.exceptions.ClientError as e:
        raise e
    # sleep for 3 seconds to wait for report
    time.sleep(3)
    try:
        csv_report = client.get_credential_report()['Content']
    except botocore.exceptions.ClientError as e:
        raise e
    return csv_report


def get_access_keys(account, user):
    keys = ''
    client = init_session(account)
    paginator = client.get_paginator('list_access_keys')
    response_iterator = paginator.paginate(UserName=user)
    for row in response_iterator:
        keys = row['AccessKeyMetadata']
    return keys


def get_user_groups(account, user):
    client = init_session(account)
    groups = client.list_groups_for_user(UserName=user)['Groups']
    return groups


def main():
    now = datetime.datetime.now()
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ha:", ['account=', 'logfile='])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
        elif opt in ('-a', '--account'):
            account = arg
        else:
            assert False, "unhandled option"
    if 'account' in locals():
        # field_names=tuple(csv_report.split('\n')[0].split(','))
        csv_report = get_cred_report(account)
        reader = csv.DictReader(csv_report.split('\n'), delimiter=',')
        log_buffer = list()
        for line in reader:
            user = line['user']
            line['timestamp'] = str(now)
            line['account'] = account
            if user == '<root_account>':
                line['access_key_1_id'] = 'N/A'
                line['access_key_2_id'] = 'N/A'
            line['user_groups'] = 'N/A'
            if line['access_key_1_active'] == 'true':
                access_key1_create = parse(line['access_key_1_last_rotated'])
            else:
                access_key1_create = 'N/A'
            if line['access_key_2_active'] == 'true':
                access_key2_create = parse(line['access_key_2_last_rotated'])
            else:
                access_key2_create = 'N/A'
            if user != '<root_account>':
                user_keys = get_access_keys(account, user)
                no_of_keys = len(user_keys)
                if no_of_keys == 1:
                    for k in user_keys:
                        line['access_key_1_id'] = k['AccessKeyId']
                        line['access_key_2_id'] = 'N/A'
                elif no_of_keys == 2:
                    for k in user_keys:
                        if k['CreateDate'] == access_key1_create and k['Status'] == 'Active':
                            line['access_key_1_id'] = k['AccessKeyId']
                        elif k['CreateDate'] == access_key2_create and k['Status'] == 'Active':
                            line['access_key_2_id'] = k['AccessKeyId']
                else:
                    line['access_key_1_id'] = 'N/A'
                    line['access_key_2_id'] = 'N/A'
                user_groups = list()
                groups = get_user_groups(account, user)
                for group in groups:
                    user_groups.append(group['GroupName'])
                line['user_groups'] = ', '.join(user_groups)
            log_buffer.append(line)
        with open(logfile, 'a') as creds_log:
            for item in log_buffer:
                # creds_log.write("%s\n" % item)
                json.dump(item, creds_log)
                creds_log.write("\n")
    else:
        usage()


def usage():
    print 'Usage:'
    print os.path.basename(__file__) + ' -a <aws_account> (from ~/.aws/credentials)'
    sys.exit(0)

if __name__ == "__main__":
    main()
