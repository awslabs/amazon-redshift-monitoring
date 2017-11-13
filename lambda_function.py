#!/usr/bin/env python

from __future__ import print_function

# Copyright 2016-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
# http://aws.amazon.com/apache2.0/
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

import sys
import os

# add the lib directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "sql"))

import boto3
import base64
import pg8000
import datetime
import json

__version__ = "1.3"

debug = False

aws_region = os.environ['AWS_REGION']
if 'DEBUG' in os.environ:
    if os.environ['DEBUG'].upper() == 'TRUE':
        debug = True
        
kms = boto3.client('kms', region_name=aws_region)
cw = boto3.client('cloudwatch', region_name=aws_region
                  )
if debug:
    print("Connected to AWS KMS & CloudWatch in %s" % aws_region)

#### Static Configuration
ssl = True
interval = '1 hour'
##################

pg8000.paramstyle = "qmark"

def run_external_commands(command_set_type, file_name, cursor, cluster):
    if not os.path.exists(file_name):
        return []
    
    external_commands = None
    try:
        external_commands = json.load(open(file_name, 'r'))
    except ValueError as e:
        # handle a malformed user query set gracefully
        if e.message == "No JSON object could be decoded":
            return []
        else:
            raise
       
    output_metrics = []
    
    for command in external_commands:
        if command['type'] == 'value':
            cmd_type = "Query"
        else:
            cmd_type = "Canary"
            
        print("Executing %s %s: %s" % (command_set_type, cmd_type, command['name']))
        
        t = datetime.datetime.now()
        interval = run_command(cursor, command['query'])
        value = cursor.fetchone()[0]            
        
        if value == None:
            value = 0
        
        # append a cloudwatch metric for the value, or the elapsed interval, based upon the configured 'type' value
        if command['type'] == 'value':
            output_metrics.append({
                                    'MetricName': command['name'],
                                    'Dimensions': [
                                        { 'Name': 'ClusterIdentifier', 'Value': cluster}
                                    ],
                                    'Timestamp': t,
                                    'Value': value,
                                    'Unit': command['unit']
                                })
        else:
            output_metrics.append({
                                    'MetricName': command['name'],
                                    'Dimensions': [
                                        { 'Name': 'ClusterIdentifier', 'Value': cluster}
                                    ],
                                    'Timestamp': t,
                                    'Value': interval,
                                    'Unit': 'Milliseconds'
                                })
        
    return output_metrics
    
    
def run_command(cursor, statement):
    if debug:
        print("Running Statement: %s" % statement)
        
    t = datetime.datetime.now()
    cursor.execute(statement)
    interval = (datetime.datetime.now() - t).microseconds / 1000
    
    return interval 
            

def gather_service_class_stats(cursor, cluster):
    metrics = []
    poll_ts = datetime.datetime.utcnow()
    runtime = run_command(cursor, "SELECT service_class, num_queued_queries, num_executing_queries from stv_wlm_service_class_state w WHERE w.service_class >= 6 ORDER BY 1")
    service_class_info = cursor.fetchall()
        
    for service_class in service_class_info:
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

    return metrics


def gather_table_stats(cursor, cluster):
    run_command(cursor, "select /* Lambda CloudWatch Exporter */ \"schema\" || '.' || \"table\" as table, encoded, max_varchar, unsorted, stats_off, tbl_rows, skew_sortkey1, skew_rows from svv_table_info")
    tables_not_compressed = 0
    max_skew_ratio = 0
    total_skew_ratio = 0
    number_tables_skew = 0
    number_tables = 0
    max_skew_sort_ratio = 0
    total_skew_sort_ratio = 0
    number_tables_skew_sort = 0
    number_tables_statsoff = 0
    max_varchar_size = 0
    max_unsorted_pct = 0
    total_rows = 0
    
    result = cursor.fetchall()
    
    for table in result:
        table_name, encoded, max_varchar, unsorted, stats_off, tbl_rows, skew_sortkey1, skew_rows = table
        number_tables += 1
        if encoded == 'N':
            tables_not_compressed += 1
        if skew_rows != None:
            if skew_rows > max_skew_ratio:
                max_skew_ratio = skew_rows
            total_skew_ratio += skew_rows
            number_tables_skew += 1
        if skew_sortkey1 != None:
            if skew_sortkey1 > max_skew_sort_ratio:
                max_skew_sort_ratio = skew_sortkey1
            total_skew_sort_ratio += skew_sortkey1
            number_tables_skew_sort += 1
        if stats_off != None and stats_off > 5:
            number_tables_statsoff += 1
        if max_varchar != None and max_varchar > max_varchar_size:
            max_varchar_size = max_varchar
        if unsorted != None and unsorted > max_unsorted_pct:
            max_unsorted_pct = unsorted
        if tbl_rows != None:
            total_rows += tbl_rows

    if number_tables_skew > 0:
        avg_skew_ratio = total_skew_ratio / number_tables_skew
    else:
        avg_skew_ratio = 0

    if number_tables_skew_sort > 0:
        avg_skew_sort_ratio = total_skew_sort_ratio / number_tables_skew_sort
    else:
        avg_skew_sort_ratio = 0
    
    # build up the metrics to put in cloudwatch
    return [
            {
                'MetricName': 'TablesNotCompressed',
                'Dimensions': [
                    { 'Name': 'ClusterIdentifier', 'Value': cluster}
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': tables_not_compressed,
                'Unit': 'Count'
            },
            {
                'MetricName': 'MaxSkewRatio',
                'Dimensions': [
                    { 'Name': 'ClusterIdentifier', 'Value': cluster}
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': max_skew_ratio,
                'Unit': 'None'
            },
            {
                'MetricName': 'AvgSkewRatio',
                'Dimensions': [
                    { 'Name': 'ClusterIdentifier', 'Value': cluster}
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': avg_skew_ratio,
                'Unit': 'None'
            },
            {
                'MetricName': 'Tables',
                'Dimensions': [
                    { 'Name': 'ClusterIdentifier', 'Value': cluster}
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': number_tables,
                'Unit': 'Count'
            },
            {
                'MetricName': 'MaxSkewSortRatio',
                'Dimensions': [
                    { 'Name': 'ClusterIdentifier', 'Value': cluster}
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': max_skew_sort_ratio,
                'Unit': 'None'
            },
            {
                'MetricName': 'AvgSkewSortRatio',
                'Dimensions': [
                    { 'Name': 'ClusterIdentifier', 'Value': cluster}
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': avg_skew_sort_ratio,
                'Unit': 'None'
            },
            {
                'MetricName': 'TablesStatsOff',
                'Dimensions': [
                    { 'Name': 'ClusterIdentifier', 'Value': cluster}
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': number_tables_statsoff,
                'Unit': 'Count'
            },
            {
                'MetricName': 'MaxVarcharSize',
                'Dimensions': [
                    { 'Name': 'ClusterIdentifier', 'Value': cluster}
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': max_varchar_size,
                'Unit': 'None'
            },
            {
                'MetricName': 'MaxUnsorted',
                'Dimensions': [
                    { 'Name': 'ClusterIdentifier', 'Value': cluster}
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': max_unsorted_pct,
                'Unit': 'Percent'
            },
            {
                'MetricName': 'Rows',
                'Dimensions': [
                    { 'Name': 'ClusterIdentifier', 'Value': cluster}
                ],
                'Timestamp': datetime.datetime.utcnow(),
                'Value': total_rows,
                'Unit': 'Count'
            }
        ] 
    
# nasty hack for backward compatiblility, to extract label values from os.environ or event
def get_config_value(labels, configs):
    for l in labels:
        for c in configs:
            if l in c:
                if debug:
                    print ("Resolved label value %s from config" % l)
                    
                return c[l]
    
    return None


def lambda_handler(event, context):
    # resolve the configuration from the sources required
    config_sources = [event, os.environ]
    user = get_config_value(['DbUser', 'db_user'], config_sources)
    enc_password = get_config_value(['EncryptedPassword', 'encrypted_password' ], config_sources)
    host = get_config_value(['HostName', 'cluster_endpoint'], config_sources)
    port = int(get_config_value(['HostPort', 'db_port' ], config_sources))
    database = get_config_value(['DatabaseName', 'db_name'], config_sources)
    cluster = get_config_value(['ClusterName', 'cluster_name'], config_sources)
    global interval
    interval = get_config_value(['AggregationInterval', 'agg_interval'], config_sources)
    
        
    # decrypt the password
    try:
        pwd = kms.decrypt(CiphertextBlob=base64.b64decode(enc_password))['Plaintext']
    except:
        print('KMS access failed: exception %s' % sys.exc_info()[1])
        print('Encrypted Password: %s' % enc_password)
        raise
        
    # Connect to the cluster
    try:
        if debug:
            print('Connecting to Redshift: %s' % host)
        
        conn = pg8000.connect(database=database, user=user, password=pwd, host=host, port=port, ssl=ssl)
    except:
        print('Redshift Connection Failed: exception %s' % sys.exc_info()[1])
        raise

    if debug:
        print('Successfully Connected to Cluster')
    cursor = conn.cursor()

    # collect table statistics
    put_metrics = gather_table_stats(cursor, cluster)
        
    # collect service class statistics
    put_metrics.extend(gather_service_class_stats(cursor, cluster))
    
    # run the externally configured commands and append their values onto the put metrics
    put_metrics.extend(run_external_commands('Redshift Diagnostic', 'monitoring-queries.json', cursor, cluster))
    
    # run the supplied user commands and append their values onto the put metrics
    put_metrics.extend(run_external_commands('User Configured', 'user-queries.json', cursor, cluster))
    
    max_metrics = 20
    group = 0
    print("Publishing %s CloudWatch Metrics" % (len(put_metrics)))
    
    for x in range(0, len(put_metrics), max_metrics):
        group += 1

        # slice the metrics into blocks of 20 or just the remaining metrics
        put = put_metrics[x:(x + max_metrics)]
        
        if debug:
            print("Metrics group %s: %s Datapoints" % (group, len(put)))
            print(put)
        try:  
            cw.put_metric_data(
                Namespace='Redshift',
                MetricData=put
            )
        except:
            print('Pushing metrics to CloudWatch failed: exception %s' % sys.exc_info()[1])

    cursor.close()
    conn.close()
    return 'Finished'

if __name__ == "__main__":
    lambda_handler(sys.argv[0], None)
