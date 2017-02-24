# Redshift Advance Monitoring

## Goals
Amazon Redshift is a fast, fully managed, petabyte-scale data warehouse solution that uses columnar storage to minimise IO, provide high data compression rates, and offer fast performance. This GitHub provides an advance monitoring system for Amazon Redshift.

The monitoring system is based in Lambda and CloudWatch. A Lambda function is running regularly, connecting to the Redshift cluster and generating cloudwatch custom alarms for the Redshift cluster.

Most of the graphs are based on the information provided in this blog article, so I recommend you to read it carefully: [Top 10 Performance Tuning Techniques for Amazon Redshift](https://blogs.aws.amazon.com/bigdata/post/Tx31034QG0G3ED1/Top-10-Performance-Tuning-Techniques-for-Amazon-Redshift).

## Installation
To install this utility, you can either use the prebuilt zip in the [dist](dist) folder, or you can build it yourself. We've included a [build script](build.sh) for bash shell that will create a zip file which you can upload into AWS Lambda.

This function is able to monitor a single cluster (today), so you must configure it to connect. To do this, you can either edit the variables at the top of the file:

* user: The user in the database.
* enc_password: The password encrypted with the KMS key.
* host: The endpoing dns name of the Redshift cluster.
* port: The port used by the Redshift cluster.
* database: Database name of the Redshift cluster.
* ssl: If you want to use SSL to connect to the cluster.
* cluster: A cluster name, your graphs in CloudWatch are going to use it to reference the Redshift Cluster.
* interval: The interval you're going to use to run your lambda function, 1 hour is a recommended interval.

Alternatively, you can now use [Lambda Environment Variables](http://docs.aws.amazon.com/lambda/latest/dg/env_variables.html) for configuration, including:

```
"Environment": {
        "Variables": {
            "encrypted_password": "KMS encrypted password",
            "db_port": "database part number",
            "cluster_name": "display name for cloudwatch metrics",
            "db_name": "database name",
            "db_user": "database user name",
            "cluster_endpoint": "cluster DNS name"
        }
    }
```
 
The password for the Redshift user *must* be encrypted with KMS, and plaintext passwords are NOT supported. Furthermore, Lambda Environment Variables can also be [encrypted within the Lambda service using KMS](http://docs.aws.amazon.com/lambda/latest/dg/env_variables.html#env_encrypt).

These are the steps you should follow to configure the function:

* Create a KMS key in the same region as the Redshift Cluster. Take note of the key ARN [Documentation](http://docs.aws.amazon.com/kms/latest/developerguide/create-keys.html)
* Create a Role for the lambda function, at least this role should have the policy "AWSLambdaVPCAccessExecutionRole" to be able to run in a VPC, and the custom policy (to access the KMS key):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Stmt1458213823000",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt"
            ],
            "Resource": [
                "<kms key arn>"
            ]
        },
        {
            "Sid": "Stmt1458218675000",
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
```

* Create a user in Redshift to use it with the script, this user should have at least access to the tables in the "pg_catalog" schema: 
>grant select on all tables in schema pg_catalog to tamreporting

* Encrypt the password of the user with the KMS key, you can use this command line to do it: 
>aws kms encrypt --key-id `<kms_key_id>` --plaintext `<password>`

* If you are rebuilding the function, download and install dependencies
>pip install -r requirements.txt -t .

* Compress the Lambda function package:
>./build.sh

* Create a lambda function, some of the parameters of the function are:
  * Runtime: Python 2.7
  * Upload the zip file generated
  * Handler: `lambda_function.lambda_handler`
  * Role: Use the role created
  * Memory: 256MB
  * Timeout: 5 minutes
  * VPC: Use the same VPC as the Redshift cluster. You're going to need at least two private subnets with access to the Redshift cluster in its Security Group. You should have a NAT Gateway to give access to Internet to those subnets routing tables. You cannot use public subnets. You can read more information here [AWS blog](https://aws.amazon.com/blogs/aws/new-access-resources-in-a-vpc-from-your-lambda-functions/)

* Add an Event Source to the Lambda function with a Scheduled Event, running with the same frequency you configured in the Lambda function.

* After a period of time, you can check your CloudWatch metrics, and create alarms. You can also create a Dashboard with all the graphs and have a view of your database as this one:

![Dashboard1](https://s3-eu-west-1.amazonaws.com/amzsup/dashboard1.png)
![Dashboard2](https://s3-eu-west-1.amazonaws.com/amzsup/dashboard2.png)

## Extensions

The published CloudWatch metrics are all configured in a JSON file called `monitoring-queries.json`. These are queries that have been built by the AWS Redshift database engineering and support teams and which provide detailed metrics about the operation of your cluster.

If you would like to create your own queries to be instrumented via AWS CloudWatch, such as user 'canary' queries which help you to see the performance of your cluster over time, these can be added into the [user-queries.json](user-queries.json) file. The file is a JSON array, with each query having the following structure:

```
{
	"query": "my select query that returns a numeric value",
	"name":"MyCanaryQuery",
	"unit":"Count | Seconds | Milliseconds | Whatever",
	"type":"(value | interval)"
}
```

The last attribute `type` is probably the most important. If you use `value`, then the value from your query will be exported to CloudWatch with the indicated unit and Metric Name. However, if you use `interval`, then the runtime of your query will be instrumented as elapsed milliseconds, giving you the ability to create the desired 'canary' query.

----

Copyright 2016-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.