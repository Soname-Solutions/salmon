#!/usr/bin/env bash
if [[ $# -ge 2 ]]; then
    export AWS_PROFILE=$1
    export STAGE_NAME=$2
    shift; shift
    npx cdk deploy --all --profile $AWS_PROFILE "$@"
    exit $?
else
    echo 1>&2 "Provide aws profile and stage as first two args."
    echo 1>&2 "Additional args are passed through to cdk deploy."
    exit 1
fi
