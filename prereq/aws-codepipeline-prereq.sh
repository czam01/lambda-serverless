#!/bin/bash
# aws cloudformation deploy \
# --region us-east-1 \ 
# --stack-name labpreq \ 
# --template-file ./aws-codepipeline-prereq2.yml \
# --capabilities CAPABILITY_IAM \
# --capabilities CAPABILITY_NAMED_IAM
aws cloudformation deploy --region us-east-1 --stack-name labpreq --template-file ./aws-codepipeline-prereq.yml --capabilities CAPABILITY_IAM --capabilities CAPABILITY_NAMED_IAM