import redshift_monitoring as rm
import os
import json
from argparse import ArgumentParser

config = {"DbUser": None,
          "EncryptedPassword": None,
          "HostName": None,
          "HostPort": None,
          "DatabaseName": None,
          "ClusterName": None,
          "DEBUG": False,
          "AWS_REGION": None
          }

parser = ArgumentParser()

for c in config.keys():
    parser.add_argument(f"--{c}", dest=c, required=False if c in ["AWS_REGION", "DEBUG", "HostPort"] else True)

args = parser.parse_args()

for arg in vars(args):
    config[arg] = getattr(args, arg)

if config.get("AWS_REGION") is None:
    if "AWS_REGION" not in os.environ or os.environ.get("AWS_REGION") is None:
        raise Exception("AWS_REGION must be exported in the environment or part of arguments")
    else:
        config["AWS_REGION"] = os.environ["AWS_REGION"]

if config.get("HostPort") is None:
    config["HostPort"] = 5439

print("Using the following event definition - can be used for testing in AWS Lambda")
print(json.dumps([config]))
response = rm.monitor_cluster([config])
