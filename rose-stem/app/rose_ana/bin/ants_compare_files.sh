#!/bin/bash -l
#
# Wrapper script for convenience of standardised testing in a rose_ana style
# app configuration using rose bunch for calls to nccmp and mule-cumf within
# an ants-based rose-stem.
set -eu


comparethese(){
    export source=$1
    export target=$2

    # Based on the filename extension, determine whether to call the nccmp or the cumf check script
    echo $source
    echo $target
    if [[ $source == *.nc ]]; then
        # Compare netcdf files, treating nans as equal and ignoring the history, _NCProperties, and Conventions global attributes.
        nccmp --var-diff-count 5 --global --data --force --metadata --nans-are-equal --buffer-entire-var --statistics --globalex=history,_NCProperties,Conventions $source $target
    else
        # Compare F03 Ancil files, ignoring the fixed length header entry from model version
        result=$( mule-cumf $source $target --ignore fixed_length_header=12 )
        echo "$result"
        compare_check=$( echo "$result" | grep "Files compare" | wc -l )
        if [[ $compare_check -ne 1 ]]; then
            exit 1
        fi
    fi
}

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <source> <target>"
    exit 1
fi

source=$1
target=$2

comparethese $source $target
