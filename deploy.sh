#!/usr/bin/env bash

ver=1.4

for r in `aws ec2 describe-regions --query Regions[*].RegionName --output text`; do aws s3 cp dist/redshift-advanced-monitoring-$ver.zip s3://awslabs-code-$r/RedshiftAdvancedMonitoring/redshift-advanced-monitoring-$ver.zip --acl public-read --region $r; done