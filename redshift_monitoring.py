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
import pgpasslib

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

            if value is None:
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
        except Exception as e:
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
    runtime = run_command(cursor,'''
        SELECT DATE_TRUNC('hour', a.service_class_start_time) AS metrics_ts,
               TRIM(d.name) as service_class, 
               COUNT(a.query) AS query_count,
               SUM(a.total_exec_time) AS sum_exec_time,
               sum(case when a.total_queue_time > 0 then 1 else 0 end) count_queued_queries,
               SUM(a.total_queue_time) AS sum_queue_time,        
               count(c.is_diskbased) as count_diskbased_segments
        FROM stl_wlm_query a 
        JOIN stv_wlm_classification_config b ON a.service_class = b.action_service_class
        LEFT OUTER JOIN (select query, SUM(CASE when is_diskbased = 't' then 1 else 0 end) is_diskbased 
                         from svl_query_summary 
                         group by query) c on a.query = c.query
        JOIN stv_wlm_service_class_config d on a.service_class = d.service_class
        WHERE a.service_class > 5
          AND a.service_class_start_time > DATEADD(hour, -2, current_date)
        GROUP BY DATE_TRUNC('hour', a.service_class_start_time),
                 d.name
    ''')
    service_class_info = cursor.fetchall()

    def add_metric(metric_name, service_class_id, metric_value, ts):
        metrics.append({
            'MetricName': metric_name,
            'Dimensions': [{'Name': 'ClusterIdentifier', 'Value': cluster},
                           {'Name': 'ServiceClassID', 'Value': str(service_class_id)}],
            'Timestamp': ts,
            'Value': metric_value
        })

    for service_class in service_class_info:
        add_metric('ServiceClass-Queued', service_class[1], service_class[4], service_class[0])
        add_metric('ServiceClass-QueueTime', service_class[1], service_class[5], service_class[0])
        add_metric('ServiceClass-Executed', service_class[1], service_class[2], service_class[0])
        add_metric('ServiceClass-ExecTime', service_class[1], service_class[3], service_class[0])
        add_metric('ServiceClass-DiskbasedQuerySegments', service_class[1], service_class[6], service_class[0])

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
        if skew_rows is not None:
            if skew_rows > max_skew_ratio:
                max_skew_ratio = skew_rows
            total_skew_ratio += skew_rows
            number_tables_skew += 1
        if skew_sortkey1 is not None:
            if skew_sortkey1 > max_skew_sort_ratio:
                max_skew_sort_ratio = skew_sortkey1
            total_skew_sort_ratio += skew_sortkey1
            number_tables_skew_sort += 1
        if stats_off is not None and stats_off > 5:
            number_tables_statsoff += 1
        if max_varchar is not None and max_varchar > max_varchar_size:
            max_varchar_size = max_varchar
        if unsorted is not None and unsorted > max_unsorted_pct:
            max_unsorted_pct = unsorted
        if tbl_rows is not None:
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
    metrics = []

    def add_metric(metric_name, value, unit):
        metrics.append({
            'MetricName': metric_name,
            'Dimensions': [
                {'Name': 'ClusterIdentifier', 'Value': cluster}
            ],
            'Timestamp': datetime.datetime.utcnow(),
            'Value': value,
            'Unit': unit
        })

    units_count = 'Count'
    units_none = 'None'
    units_pct = 'Percent'

    add_metric('TablesNotCompressed', tables_not_compressed, units_count)
    add_metric('MaxSkewRatio', max_skew_ratio, units_none)
    add_metric('MaxSkewSortRatio', max_skew_sort_ratio, units_none)
    add_metric('AvgSkewRatio', avg_skew_ratio, units_none)
    add_metric('AvgSkewSortRatio', avg_skew_sort_ratio, units_none)
    add_metric('Tables', number_tables, units_count)
    add_metric('Rows', total_rows, units_count)
    add_metric('TablesStatsOff', number_tables_statsoff, units_count)
    add_metric('MaxVarcharSize', max_varchar_size, units_none)
    add_metric('MaxUnsorted', max_unsorted_pct, units_pct)

    return metrics


# nasty hack for backward compatibility, to extract label values from os.environ or event
def get_config_value(labels, configs):
    for l in labels:
        for c in configs:
            if l in c:
                if debug:
                    print("Resolved label value %s from config" % l)

                return c[l]

    return None


def monitor_cluster(config_sources):
    aws_region = get_config_value(['AWS_REGION'], config_sources)

    set_debug = get_config_value(['DEBUG', 'debug', ], config_sources)
    if set_debug is not None and ((isinstance(set_debug,bool) and set_debug) or set_debug.upper() == 'TRUE'):
        global debug
        debug = True

    kms = boto3.client('kms', region_name=aws_region)
    cw = boto3.client('cloudwatch', region_name=aws_region)

    if debug:
        print("Connected to AWS KMS & CloudWatch in %s" % aws_region)

    user = get_config_value(['DbUser', 'db_user', 'dbUser'], config_sources)
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

    # we may have been passed the password in the configuration, so extract it if we can
    pwd = get_config_value(['db_pwd'], config_sources)

    # override the password with the contents of .pgpass or environment variables
    pwd = None
    try:
        pwd = pgpasslib.getpass(host, port, database, user)
    except pgpasslib.FileNotFound as e:
        pass

    if pwd is None:
        enc_password = get_config_value(['EncryptedPassword', 'encrypted_password', 'encrypted_pwd', 'dbPassword'],
                                        config_sources)
        # resolve the authorisation context, if there is one, and decrypt the password
        auth_context = get_config_value('kms_auth_context', config_sources)

        if auth_context is not None:
            auth_context = json.loads(auth_context)

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
