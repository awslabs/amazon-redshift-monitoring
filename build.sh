#!/bin/bash

ver=`python3 -c 'import redshift_monitoring as rm; print(rm.__version__);'`

if [ ! -d dist ]; then
	mkdir dist
fi

ARCHIVE=redshift-advanced-monitoring-$ver.zip

# add required dependencies
pip install pg8000 -t lib
pip install pgpasslib -t lib

if [ ! -e lib/pgpasslib.py ]; then
       pip install pgpasslib -t lib
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
