# Redshift Advance Monitoring

## Goals
Amazon Redshift is a fast, fully managed, petabyte-scale data warehouse solution that uses columnar storage to minimise IO, provides high data compression rates, and offers fast performance. This GitHub project provides an advance monitoring system for Amazon Redshift that is completely serverless, based on AWS Lambda and Amazon CloudWatch. A serverless Lambda function runs on a schedule, connects to the configured Redshift cluster, and generates CloudWatch custom alarms for common possible issues.

Most of the graphs are based on the information provided in AWS Big Data Blog articles and Redshift Documentation:

* [Top 10 Performance Tuning Techniques for Amazon Redshift](https://blogs.aws.amazon.com/bigdata/post/Tx31034QG0G3ED1/Top-10-Performance-Tuning-Techniques-for-Amazon-Redshift)
* [Advanced table design playbook](https://aws.amazon.com/blogs/big-data/amazon-redshift-engineerings-advanced-table-design-playbook-preamble-prerequisites-and-prioritization)

## Installation

This function can be automatically deployed using a Serverless Application Model (SAM) in CloudFormation. Use the links below based on the specified region to walk through the CloudFormation deployment model.

You must supply parameters for your cluster name, endpoint address and port, master username and the encrypted password, and the aggregation interval to be used by the monitoring scripts (default 1 hour).

The SAM stack will create:

* An IAM Role called LambdaRedshiftMonitoringRole
* This IAM Role will have a single linked IAM Policy called LambdaRedshiftMonitoringPolicy that can:
  *  Decrypt the KMS Key used to encrypt the cluster password (kms::Decrypt)
  *  Emit CloudWatch metrics (cloudwatch::PutMetricData)

|Region | VPC Template | Non-VPC Template |
|---- |---- | ----|
|ap-northeast-1 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ap-northeast-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ap-northeast-1.amazonaws.com/awslabs-code-ap-northeast-1/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ap-northeast-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ap-northeast-1.amazonaws.com/awslabs-code-ap-northeast-1/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||ap-northeast-2 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ap-northeast-2#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ap-northeast-2.amazonaws.com/awslabs-code-ap-northeast-2/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ap-northeast-2#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ap-northeast-2.amazonaws.com/awslabs-code-ap-northeast-2/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||ap-south-1 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ap-south-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ap-south-1.amazonaws.com/awslabs-code-ap-south-1/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ap-south-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ap-south-1.amazonaws.com/awslabs-code-ap-south-1/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||ap-southeast-1 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ap-southeast-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ap-southeast-1.amazonaws.com/awslabs-code-ap-southeast-1/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ap-southeast-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ap-southeast-1.amazonaws.com/awslabs-code-ap-southeast-1/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||ap-southeast-2 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ap-southeast-2#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ap-southeast-2.amazonaws.com/awslabs-code-ap-southeast-2/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ap-southeast-2#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ap-southeast-2.amazonaws.com/awslabs-code-ap-southeast-2/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||ca-central-1 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ca-central-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ca-central-1.amazonaws.com/awslabs-code-ca-central-1/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=ca-central-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-ca-central-1.amazonaws.com/awslabs-code-ca-central-1/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||eu-central-1 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=eu-central-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-eu-central-1.amazonaws.com/awslabs-code-eu-central-1/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=eu-central-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-eu-central-1.amazonaws.com/awslabs-code-eu-central-1/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||eu-west-1 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=eu-west-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-eu-west-1.amazonaws.com/awslabs-code-eu-west-1/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=eu-west-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-eu-west-1.amazonaws.com/awslabs-code-eu-west-1/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||eu-west-2 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=eu-west-2#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-eu-west-2.amazonaws.com/awslabs-code-eu-west-2/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=eu-west-2#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-eu-west-2.amazonaws.com/awslabs-code-eu-west-2/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||sa-east-1 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=sa-east-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-sa-east-1.amazonaws.com/awslabs-code-sa-east-1/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=sa-east-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-sa-east-1.amazonaws.com/awslabs-code-sa-east-1/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||us-east-1 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-us-east-1.amazonaws.com/awslabs-code-us-east-1/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-us-east-1.amazonaws.com/awslabs-code-us-east-1/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||us-east-2 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=us-east-2#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-us-east-2.amazonaws.com/awslabs-code-us-east-2/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=us-east-2#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-us-east-2.amazonaws.com/awslabs-code-us-east-2/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||us-west-1 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=us-west-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-us-west-1.amazonaws.com/awslabs-code-us-west-1/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=us-west-1#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-us-west-1.amazonaws.com/awslabs-code-us-west-1/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) ||us-west-2 | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-us-west-2.amazonaws.com/awslabs-code-us-west-2/RedshiftAdvancedMonitoring/deploy-vpc.yaml) | [<img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png">](https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/new?stackName=RedshiftAdvancedMonitoring&templateURL=https://s3-us-west-2.amazonaws.com/awslabs-code-us-west-2/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml) |

If you wish to deploy manually, you can use the prebuilt zip in the [dist](dist) folder, or you can build it yourself. We've included a [build script](build.sh) for bash shell that will create a zip file which you can upload into AWS Lambda.

The password for the Redshift user *must* be encrypted with KMS, and plaintext passwords are NOT supported. Furthermore, Lambda Environment Variables can also be [encrypted within the Lambda service using KMS](http://docs.aws.amazon.com/lambda/latest/dg/env_variables.html#env_encrypt).

# Setting up KMS Keys for encryption

If you use the above SAM deployment templates, then all permissions are configured for you. If not, then these are the steps you should follow to configure the function:

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

## Configuration 

### Static Configuration (Bad - deprecated after v1.2)

You can edit the variables at the top of the script, and rebuild. Please note that anyone who has access to the Lambda function code will also have access to these configuration values. This includes:

* user: The user in the database.
* enc_password: The password encrypted with the KMS key.
* host: The endpoing dns name of the Redshift cluster.
* port: The port used by the Redshift cluster.
* database: Database name of the Redshift cluster.
* ssl: If you want to use SSL to connect to the cluster.
* cluster: A cluster name, your graphs in CloudWatch are going to use it to reference the Redshift Cluster.
* interval: The interval you're going to use to run your lambda function, 1 hour is a recommended interval.

### Environment Variables (Better)

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

### Configuring with Events (Best)

This option allows you to send the configuration as part of the Scheduled Event, which then means you can support multiple clusters from a single Lambda function. This option will override any Environment variables that you've configured. An example event looks like:

```
{
  "DbUser": "master",
  "EncryptedPassword": "AQECAHh+YtzV/K7+L/VDT7h2rYDCWFSUugXGqMxzWGXynPCHpQAAAGkwZwYJKoZIhvcNAQcGoFowWAIBADBTBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDM8DWMFELclZ2s7cmwIBEIAmyVGjoB7F4HbwU5Y1lq7GVQ3UU3MaE10LWieCKMHOtVhJioi+IHw=",
  "ClusterName": "energy-demo",
  "HostName": "energy-demo.c7bpmf3ajaft.eu-west-1.redshift.amazonaws.com",
  "HostPort": "5439",
  "DatabaseName": "master",
  "AggregationInterval": "1 hour"
}
```

The old environment variable names are provided for backward compatibility, but you can use environment variables with the above names, and it will use those instead. 

## Manual Deployment Instructions

* If you are rebuilding the function, download and install dependencies
>pip install -r requirements.txt -t .

* Assemble and compress the Lambda function package:
>./build.sh

If you are including any user defined query extensions, then build with:

>./build.sh --include-user-queries

Please note the labelled version in Github does not include any user queries

* Create a lambda function, some of the parameters of the function are:
  * Runtime: Python 2.7
  * Upload the zip file generated
  * Handler: `lambda_function.lambda_handler`
  * Role: Use the role created
  * Memory: 256MB
  * Timeout: 5 minutes
  * VPC: Use the same VPC as the Redshift cluster. You're going to need at least two private subnets with access to the Redshift cluster in its Security Group. You should have a NAT Gateway to give access to Internet to those subnets routing tables. You cannot use public subnets. You can read more information here [AWS blog](https://aws.amazon.com/blogs/aws/new-access-resources-in-a-vpc-from-your-lambda-functions/)

* Add an Event Source to the Lambda function with a Scheduled Event, running with the same frequency you configured in the Lambda function.

## Confirming Successful Execution

* After a period of time, you can check your CloudWatch metrics, and create alarms. You can also create a Dashboard with all the graphs and have a view of your database as this one:

![Dashboard1](https://s3-eu-west-1.amazonaws.com/amzsup/dashboard1.png)
![Dashboard2](https://s3-eu-west-1.amazonaws.com/amzsup/dashboard2.png)

# Extensions

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