#!/usr/bin/env python

from __future__ import print_function
from __future__ import division


# Copyright 2016-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
# http://aws.amazon.com/apache2.0/
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

import sys
import boto3
import base64
import pg8000
import datetime
import ConfigParser

poll_ts = datetime.datetime.utcnow()

# Configuration

config = ConfigParser.ConfigParser()
config.read('config.ini')

def ConfigSectionMap(section):
    dict1 = {}
    options = config.options(section)
    for option in options:
        try:
            dict1[option] = config.get(section, option)
            if dict1[option] == -1:
                print("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

# Cluster Info

user = ConfigSectionMap("cluster_info")['user']
enc_password = ConfigSectionMap("cluster_info")['enc_password']
host = ConfigSectionMap("cluster_info")['host']
port = int(ConfigSectionMap("cluster_info")['port'])
database = ConfigSectionMap("cluster_info")['database']
ssl = ConfigSectionMap("cluster_info")['ssl']
cluster = ConfigSectionMap("cluster_info")['cluster']

# Development

debug = ConfigSectionMap("development")['debug']

##################



def sql_from_file(file):
    with open(file, 'r') as sql_file:
        sql = sql_file.read()

    return sql

def run_command(cursor, statement):
    # if debug:
    #     print("Running Statement: %s" % statement)

    return cursor.execute(statement)


def lambda_handler(event, context):
    try:
        kms = boto3.client('kms')
        password = kms.decrypt(CiphertextBlob=base64.b64decode(enc_password))['Plaintext']
    except:
        raise Exception('KMS access failed: exception %s' % sys.exc_info()[1])
        print('KMS access failed: exception %s' % sys.exc_info()[1])

    pg8000.paramstyle = "qmark"

    try:
        # if debug:
        #     print('Connect to Redshift: %s' % host)
        conn = pg8000.connect(database=database, user=user, password=password, host=host, port=port, ssl=ssl)
    except:
        print('Redshift Connection Failed: exception %s' % sys.exc_info()[1])
        return 'Failed'

    # if debug:
    #     print('Succesfully Connected Redshift Cluster')

    cursor = conn.cursor()
    poll_start = datetime.datetime.utcnow()
    run_command(cursor, sql_from_file('sql/ungranted_locks.sql'))
    ungranted_locks = cursor.fetchone()[0]
    run_command(cursor, sql_from_file('sql/open_transactions.sql'))
    open_transactions = cursor.fetchone()[0]
    run_command(cursor, sql_from_file('sql/vacuum_in_progress.sql'))
    vacuum_in_progress = cursor.fetchone()[0]
    run_command(cursor, sql_from_file('sql/idle_check.sql'))
    is_idle = cursor.fetchone()[0]

    run_command(cursor, sql_from_file('sql/wlm_activity.sql'))
    result = cursor.fetchall()

    poll_end = datetime.datetime.utcnow()
    tdelta = poll_end - poll_start
    poll_runtime = tdelta.microseconds / 1000000

    metrics = [
        {
            'MetricName': 'PollRuntime',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': poll_ts,
            'Value': poll_runtime,
            'Unit': 'Seconds'
        },
        {
            'MetricName': 'IsIdle',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': poll_ts,
            'Value': is_idle
            # 'Unit': 'Count'
        },
        {
            'MetricName': 'RunningVacuum',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': poll_ts,
            'Value': vacuum_in_progress
            # 'Unit': 'Count'
        },
        {
            'MetricName': 'UngrantedLocks',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': poll_ts,
            'Value': ungranted_locks,
            'Unit': 'Count'
        },
        {
            'MetricName': 'OpenTransactions',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': poll_ts,
            'Value': open_transactions,
            'Unit': 'Count'
        }
    ]

    for service_class in result:
        queued_metric = {}
        queued_metric['MetricName'] = 'ServiceClass%s-Queued' % service_class[0]
        queued_metric['Dimensions'] = [{'Name': 'ClusterIdentifier', 'Value': cluster}]
        queued_metric['Timestamp'] = poll_ts
        queued_metric['Value'] = service_class[1]
        metrics.append(queued_metric.copy())

        executing_metric = {}
        executing_metric['MetricName'] = 'ServiceClass%s-Executing' % service_class[0]
        executing_metric['Dimensions'] = [{'Name': 'ClusterIdentifier', 'Value': cluster}]
        executing_metric['Timestamp'] = poll_ts
        executing_metric['Value'] = service_class[2]
        metrics.append(executing_metric.copy())

    # if debug:
    #     print("Publishing CloudWatch Metrics")

    try:
        cw = boto3.client('cloudwatch')
        cw.put_metric_data(
            Namespace='Redshift',
            MetricData=metrics
        )
    except:
        print('Pushing metrics to CloudWatch failed: exception %s' % sys.exc_info()[1])

    cursor.close()
    conn.close()
    # print('End Run: %s ' % poll_ts)
    return 'Finished'


if __name__ == "__main__":
    lambda_handler(sys.argv[0], None)
