#!/bin/bash

ver=1.4


if [ ! -d dist ]; then
	mkdir dist
fi

ARCHIVE=redshift-advanced-monitoring-$ver.zip

# add required dependencies
if [ ! -d lib/pg8000 ]; then
	pip install pg8000 -t lib
fi

# bin the old zipfile
if [ -f dist/$ARCHIVE ]; then
	echo "Removed existing Archive ../dist/$ARCHIVE"
	rm -Rf dist/$ARCHIVE
fi

cmd="zip -r dist/$ARCHIVE lambda_function.py redshift_monitoring.py monitoring-queries.json lib/"

if [ "$1" == "--include-user-queries" ]; then
	cmd="$cmd user-queries.json" 
fi

if [ $# -eq 1 ]; then
	cmd=`echo $cmd`
fi

echo $cmd

eval $cmd

echo "Generated new Lambda Archive dist/$ARCHIVE"
