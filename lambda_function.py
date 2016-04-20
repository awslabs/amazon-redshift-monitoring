#!/usr/bin/env python

from __future__ import print_function

# Copyright 2016-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
# http://aws.amazon.com/apache2.0/
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

import json
import boto3
import base64
import pg8000
import datetime

#### Configuration

user = 'dbuser'
enc_password = 'CiC5vxxxxxNg=='
host = 'endpoint'
port = 8192
database = 'dbname'
ssl = True
cluster = 'clustername'
interval = '1 hour'

##################

print('Loading function')

kms = boto3.client('kms')
password = kms.decrypt(CiphertextBlob=base64.b64decode(enc_password))['Plaintext']
cw = boto3.client('cloudwatch')

pg8000.paramstyle = "qmark"

def lambda_handler(event, context):
    conn = pg8000.connect(database=database, user=user, password=password, host=host, port=port, ssl=ssl)
    cursor = conn.cursor()

    cursor.execute("select \"schema\" || '.' || \"table\" as table, encoded, max_varchar, unsorted, stats_off, tbl_rows, skew_sortkey1, skew_rows from svv_table_info")
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

    cursor.execute("SELECT count(a.attname) FROM pg_namespace n, pg_class c, pg_attribute a  WHERE n.oid = c.relnamespace AND c.oid = a.attrelid AND a.attnum > 0 AND NOT a.attisdropped and n.nspname NOT IN ('information_schema','pg_catalog','pg_toast') AND format_encoding(a.attencodingtype::integer) = 'none' AND c.relkind='r' AND a.attsortkeyord != 1")
    columns_not_compressed = cursor.fetchone()[0]
    if columns_not_compressed == None:
    	columns_not_compressed = 0

    cursor.execute("SELECT sum(nvl(s.num_qs,0)) FROM svv_table_info t LEFT JOIN (SELECT tbl, COUNT(distinct query) num_qs FROM stl_scan s WHERE s.userid > 1 AND starttime >= GETDATE() - INTERVAL '%s' GROUP BY tbl) s ON s.tbl = t.table_id WHERE t.sortkey1 IS NULL" % interval)
    queries_scan_no_sort = cursor.fetchone()[0]
    if queries_scan_no_sort == None:
    	queries_scan_no_sort = 0

    cursor.execute("SELECT SUM(w.total_queue_time) / 1000000.0 FROM stl_wlm_query w WHERE w.queue_start_time >= GETDATE() - INTERVAL '%s' AND w.total_queue_time > 0" % interval)
    total_wlm_queue_time = cursor.fetchone()[0]
    if total_wlm_queue_time == None:
    	total_wlm_queue_time = 0

    cursor.execute("SELECT count(distinct query) FROM svl_query_report WHERE is_diskbased='t' AND (LABEL LIKE 'hash%%' OR LABEL LIKE 'sort%%' OR LABEL LIKE 'aggr%%') AND userid > 1 AND start_time >= GETDATE() - INTERVAL '%s'" % interval)
    total_disk_based_queries = cursor.fetchone()[0]
    if total_disk_based_queries == None:
    	total_disk_based_queries = 0

    cursor.execute("select avg(datediff(ms,startqueue,startwork)) from stl_commit_stats  where startqueue >= GETDATE() - INTERVAL '%s'" % interval)
    avg_commit_queue = cursor.fetchone()[0]
    if avg_commit_queue == None:
    	avg_commit_queue = 0

    cursor.execute("select count(distinct l.query) from stl_alert_event_log as l where l.userid >1 and l.event_time >= GETDATE() - INTERVAL '%s'" % interval)
    total_alerts = cursor.fetchone()[0]
    if total_alerts == None:
    	total_alerts = 0

    cursor.execute("select avg(datediff(ms, starttime, endtime)) from stl_query where starttime >= GETDATE() - INTERVAL '%s'" % interval)
    avg_query_time = cursor.fetchone()[0]
    if avg_query_time == None:
    	avg_query_time = 0

    cursor.execute("select sum(packets) from stl_dist where starttime >= GETDATE() - INTERVAL '%s'" % interval)
    total_packets = cursor.fetchone()[0]
    if total_packets == None:
    	total_packets = 0

    cursor.execute("select sum(total) from (select count(query) total from stl_dist where starttime >= GETDATE() - INTERVAL '%s' group by query having sum(packets) > 1000000)" % interval)
    queries_traffic = cursor.fetchone()[0]
    if queries_traffic == None:
    	queries_traffic = 0

    cw.put_metric_data(
    	Namespace='Redshift',
    	MetricData=[
    		{
	    		'MetricName': 'TablesNotCompressed',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': tables_not_compressed,
	    		'Unit': 'Count'
	    	},
	    	{
	    		'MetricName': 'ColumnsNotCompressed',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': columns_not_compressed,
	    		'Unit': 'Count'
	    	},
	    	{
	    		'MetricName': 'MaxSkewRatio',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': max_skew_ratio,
	    		'Unit': 'None'
	    	},
	    	{
	    		'MetricName': 'AvgSkewRatio',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': avg_skew_ratio,
	    		'Unit': 'None'
	    	},
	    	{
	    		'MetricName': 'Tables',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': number_tables,
	    		'Unit': 'Count'
	    	},
	    	{
	    		'MetricName': 'QueriesScanNoSort',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': queries_scan_no_sort,
	    		'Unit': 'Count'
	    	},
	    	{
	    		'MetricName': 'MaxSkewSortRatio',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': max_skew_sort_ratio,
	    		'Unit': 'None'
	    	},
	    	{
	    		'MetricName': 'AvgSkewSortRatio',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': avg_skew_sort_ratio,
	    		'Unit': 'None'
	    	},
	    	{
	    		'MetricName': 'TablesStatsOff',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': number_tables_statsoff,
	    		'Unit': 'Count'
	    	},
	    	{
	    		'MetricName': 'MaxVarcharSize',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': max_varchar_size,
	    		'Unit': 'None'
	    	},
	    	{
	    		'MetricName': 'TotalWLMQueueTime',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': total_wlm_queue_time,
	    		'Unit': 'Seconds'
	    	},
	    	{
	    		'MetricName': 'DiskBasedQueries',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': total_disk_based_queries,
	    		'Unit': 'Count'
	    	},
	    	{
	    		'MetricName': 'AvgCommitQueueTime',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': avg_commit_queue,
	    		'Unit': 'Milliseconds'
	    	},
	    	{
	    		'MetricName': 'TotalAlerts',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': total_alerts,
	    		'Unit': 'Count'
	    	},
	    	{
	    		'MetricName': 'MaxUnsorted',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': max_unsorted_pct,
	    		'Unit': 'Percent'
	    	},
	    	{
	    		'MetricName': 'Rows',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': total_rows,
	    		'Unit': 'Count'
	    	},
	    	{
	    		'MetricName': 'AverageQueryTime',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': avg_query_time,
	    		'Unit': 'Milliseconds'
	    	},
	    	{
	    		'MetricName': 'Packets',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': total_packets,
	    		'Unit': 'Count'
	    	},
	    	{
	    		'MetricName': 'QueriesWithHighTraffic',
	    		'Dimensions': [
	    			{ 'Name': 'ClusterIdentifier', 'Value': cluster}
	    		],
	    		'Timestamp': datetime.datetime.now(),
	    		'Value': queries_traffic,
	    		'Unit': 'Count'
	    	}
    	]
    )

    cursor.close()
    conn.close()
    return 'Finished'

if __name__ == "__main__":
    event_handler(sys.argv[0], None)
