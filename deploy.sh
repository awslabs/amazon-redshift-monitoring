#!/usr/bin/env bash

ver=1.6

for r in `aws ec2 describe-regions --query Regions[*].RegionName --output text`; do aws s3 cp dist/redshift-advanced-monitoring-$ver.zip s3://awslabs-code-$r/RedshiftAdvancedMonitoring/redshift-advanced-monitoring-$ver.zip --acl public-read --region $r; done

for r in `aws ec2 describe-regions --query Regions[*].RegionName --output text`; do aws s3 cp deploy-vpc.yaml s3://awslabs-code-$r/RedshiftAdvancedMonitoring/deploy-vpc.yaml --acl public-read --region $r; done

for r in `aws ec2 describe-regions --query Regions[*].RegionName --output text`; do aws s3 cp deploy-non-vpc.yaml s3://awslabs-code-$r/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml --acl public-read --region $r; done