# Redshift Advance Monitoring
## Goals
Amazon Redshift is a fast, fully managed, petabyte-scale data warehouse solution that uses columnar storage to minimise IO, provide high data compression rates, and offer fast performance. This GitHub provides an advance monitoring system for Amazon Redshift.

The monitoring system is based in Lambda and CloudWatch. A Lambda function is running regularly, connecting to the Redshift cluster and generating cloudwatch custom alarms for the Redshift cluster.

Most of the graphs are based on the information provided in this blog article, so I recommend you to read it carefully: [Top 10 Performance Tuning Techniques for Amazon Redshift](https://blogs.aws.amazon.com/bigdata/post/Tx31034QG0G3ED1/Top-10-Performance-Tuning-Techniques-for-Amazon-Redshift).

## Installation
To install the script, you should create a Lambda function in the same VPC as the Redshift cluster.

The password for the Redshift user is going to be encrypted with KMS, so you don't need to write it in the Lambda script in clear.

These are the steps you should follow:

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
>aws kms encrypt --key-id <kms_key_id> --plaintext <password>

* Download the source code of this project, and edit the file "lambda_function.py", you should modify the configuration with these options:
  * user: The user in the database.
  * enc_password: The password encrypted with the KMS key.
  * host: The endpoing dns name of the Redshift cluster.
  * port: The port used by the Redshift cluster.
  * database: Database name of the Redshift cluster.
  * ssl: If you want to use SSL to connect to the cluster.
  * cluster: A cluster name, your graphs in CloudWatch are going to use it to reference the Redshift Cluster.
  * inverval: The interval you're going to use to run your lambda function, 1 hour is a recommended interval.

* Download dependencies
>pip install -r requirements.txt -t .

* Compress the Lambda function package:
>zip -r ../redshiftMonitoring.zip *

* Create a lambda function, some of the parameters of the function are:
  * Runtime: Python 2.7
  * Upload the zip file generated
  * Handler: lambda_function.lambda_handler
  * Role: Use the role created
  * Memory: 256MB
  * Timeout: 5 minutes
  * VPC: Use the same VPC as the Redshift cluster. You're going to need at least two private subnets with access to the Redshift cluster in its Security Group. You should have a NAT Gateway to give access to Internet to those subnets routing tables. You cannot use public subnets. You can read more information here [AWS blog](https://aws.amazon.com/blogs/aws/new-access-resources-in-a-vpc-from-your-lambda-functions/)

* Add an Event Source to the Lambda function with a Scheduled Event, running with the same frecuency you configured in the Lambda function.

* After a few hours you can check your CloudWatch metrics, and create alarms. You can also create a Dashboard with all the graphs and have a view of your database as this one:

![Dashboard1](https://s3-eu-west-1.amazonaws.com/amzsup/dashboard1.png)
![Dashboard2](https://s3-eu-west-1.amazonaws.com/amzsup/dashboard2.png)

