#!/bin/bash
aws cloudformation deploy \
--region us-west-2 \
--stack-name codepipeline-lambda-prereq \
--template-file ./aws-codepipeline-prereq.yml \
--capabilities CAPABILITY_IAM \
--capabilities CAPABILITY_NAMED_IAM
