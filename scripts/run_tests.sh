#!/bin/bash
this_dir="$(dirname $0)"

test_dir="$(readlink -f $this_dir/..)"
if [ ! -z "$1" ]; then
    test_dir="$(readlink -f $this_dir/../$1)"
    
    if [ ! -e "$test_dir" ]; then
        echo "No such file or directory: $test_dir"
        exit 1
    fi

    echo "Running only tests in $test_dir"
else
    echo "Running all tests in $test_dir"
fi

pytest "$test_dir" -v