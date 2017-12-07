#!/usr/bin/env python

# Copyright 2016-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
# http://aws.amazon.com/apache2.0/
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

import os

import redshift_monitoring

def lambda_handler(event, context):
    # resolve the configuration from the sources required
    config_sources = [event, os.environ]
    redshift_monitoring.monitor_cluster(config_sources)
    return 'Finished'

if __name__ == "__main__":
    lambda_handler(sys.argv[0], None)
