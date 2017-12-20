from __future__ import print_function

import os
import sys

# Copyright 2016-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
# http://aws.amazon.com/apache2.0/
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

# add the lib directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "sql"))

import boto3
import base64
import pg8000
import datetime
import json

#### Static Configuration
ssl = True
interval = '1 hour'
##################

__version__ = "1.4"
debug = False
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

        try:
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
                        {'Name': 'ClusterIdentifier', 'Value': cluster}
                    ],
                    'Timestamp': t,
                    'Value': value,
                    'Unit': command['unit']
                })
            else:
                output_metrics.append({
                    'MetricName': command['name'],
                    'Dimensions': [
                        {'Name': 'ClusterIdentifier', 'Value': cluster}
                    ],
                    'Timestamp': t,
                    'Value': interval,
                    'Unit': 'Milliseconds'
                })
        except e:
            print("Exception running external command %s" % command['name'])
            print(e)

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
    runtime = run_command(cursor,
                          "SELECT service_class, num_queued_queries, num_executing_queries from stv_wlm_service_class_state w WHERE w.service_class >= 6 ORDER BY 1")
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
    run_command(cursor,
                "select /* Lambda CloudWatch Exporter */ \"schema\" || '.' || \"table\" as table, encoded, max_varchar, unsorted, stats_off, tbl_rows, skew_sortkey1, skew_rows from svv_table_info")
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
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': tables_not_compressed,
            'Unit': 'Count'
        },
        {
            'MetricName': 'MaxSkewRatio',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': max_skew_ratio,
            'Unit': 'None'
        },
        {
            'MetricName': 'AvgSkewRatio',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': avg_skew_ratio,
            'Unit': 'None'
        },
        {
            'MetricName': 'Tables',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': number_tables,
            'Unit': 'Count'
        },
        {
            'MetricName': 'MaxSkewSortRatio',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': max_skew_sort_ratio,
            'Unit': 'None'
        },
        {
            'MetricName': 'AvgSkewSortRatio',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': avg_skew_sort_ratio,
            'Unit': 'None'
        },
        {
            'MetricName': 'TablesStatsOff',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': number_tables_statsoff,
            'Unit': 'Count'
        },
        {
            'MetricName': 'MaxVarcharSize',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': max_varchar_size,
            'Unit': 'None'
        },
        {
            'MetricName': 'MaxUnsorted',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': max_unsorted_pct,
            'Unit': 'Percent'
        },
        {
            'MetricName': 'Rows',
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
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
                    print("Resolved label value %s from config" % l)

                return c[l]

    return None


def get_encryption_context(cmk, region):
    authContext = {}
    authContext["module"] = cmk
    authContext["region"] = region

    return authContext


def monitor_cluster(config_sources):
    aws_region = get_config_value(['AWS_REGION'], config_sources)

    if get_config_value(['DEBUG', 'debug', ], config_sources).upper() == 'TRUE':
        global debug
        debug = True

    kms = boto3.client('kms', region_name=aws_region)
    cw = boto3.client('cloudwatch', region_name=aws_region)

    if debug:
        print("Connected to AWS KMS & CloudWatch in %s" % aws_region)

    user = get_config_value(['DbUser', 'db_user', 'dbUser'], config_sources)
    enc_password = get_config_value(['EncryptedPassword', 'encrypted_password', 'encrypted_pwd', 'dbPassword'],
                                    config_sources)
    cmk_alias = get_config_value(['cmkAlias', 'cmk_alias'], config_sources)
    host = get_config_value(['HostName', 'cluster_endpoint', 'dbHost', 'db_host'], config_sources)
    port = int(get_config_value(['HostPort', 'db_port', 'dbPort'], config_sources))
    database = get_config_value(['DatabaseName', 'db_name', 'db'], config_sources)
    cluster = get_config_value(['ClusterName', 'cluster_name', 'clusterName'], config_sources)
    global interval
    interval = get_config_value(['AggregationInterval', 'agg_interval', 'aggregtionInterval'], config_sources)
    set_debug = get_config_value(['debug', 'DEBUG'], config_sources)
    if set_debug is not None:
        global debug
        debug = set_debug

    # decrypt the password
    auth_context = None
    if cmk_alias is not None:
        auth_context = get_encryption_context(cmk_alias, aws_region)

    try:
        if auth_context is None:
            pwd = kms.decrypt(CiphertextBlob=base64.b64decode(enc_password))[
                'Plaintext']
        else:
            pwd = kms.decrypt(CiphertextBlob=base64.b64decode(enc_password), EncryptionContext=auth_context)[
                'Plaintext']
    except:
        print('KMS access failed: exception %s' % sys.exc_info()[1])
        print('Encrypted Password: %s' % enc_password)
        print('Encryption Context %s' % auth_context)
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

    # create a new cursor for methods to run through
    cursor = conn.cursor()

    # set application name
    set_name = "set application_name to 'RedshiftAdvancedMonitoring-v%s'" % __version__

    if debug:
        print(set_name)

    cursor.execute(set_name)

    # collect table statistics
    put_metrics = gather_table_stats(cursor, cluster)

    # collect service class statistics
    put_metrics.extend(gather_service_class_stats(cursor, cluster))

    # run the externally configured commands and append their values onto the put metrics
    put_metrics.extend(run_external_commands('Redshift Diagnostic', 'monitoring-queries.json', cursor, cluster))

    # run the supplied user commands and append their values onto the put metrics
    put_metrics.extend(run_external_commands('User Configured', 'user-queries.json', cursor, cluster))

    # add a metric for how many metrics we're exporting (whoa inception)
    put_metrics.extend([{
        'MetricName': 'CloudwatchMetricsExported',
        'Dimensions': [
            {'Name': 'ClusterIdentifier', 'Value': cluster}
        ],
        'Timestamp': datetime.datetime.utcnow(),
        'Value': len(put_metrics),
        'Unit': 'Count'
    }])

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
            raise

    cursor.close()
    conn.close()
