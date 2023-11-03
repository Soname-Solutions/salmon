#!/usr/bin/env bash
if [[ $# -ge 2 ]]; then
    export AWS_PROFILE=$1
    export STAGE=$2
    shift; shift
    npx cdk deploy --profile $AWS_PROFILE "$@"
    exit $?
else
    echo 1>&2 "Provide account and region as first two args."
    echo 1>&2 "Additional args are passed through to cdk deploy."
    exit 1
fi
