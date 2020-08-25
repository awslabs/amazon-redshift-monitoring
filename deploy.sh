#!/usr/bin/env bash

ver=`python3 -c 'import redshift_monitoring as rm; print(rm.__version__);'`

if [ "$1" = "" -o "$1" = "bin" ] ; then
  for r in `aws ec2 describe-regions --query Regions[*].RegionName --output text`; do aws s3 cp dist/redshift-advanced-monitoring-$ver.zip s3://awslabs-code-$r/RedshiftAdvancedMonitoring/redshift-advanced-monitoring-$ver.zip --acl public-read --region $r; done
fi

if [ "$1" = "" -o "$1" = "yaml" ] ; then
  for r in `aws ec2 describe-regions --query Regions[*].RegionName --output text`; do aws s3 cp deploy-vpc.yaml s3://awslabs-code-$r/RedshiftAdvancedMonitoring/deploy-vpc.yaml --acl public-read --region $r; done

  for r in `aws ec2 describe-regions --query Regions[*].RegionName --output text`; do aws s3 cp deploy-non-vpc.yaml s3://awslabs-code-$r/RedshiftAdvancedMonitoring/deploy-non-vpc.yaml --acl public-read --region $r; done
fi
