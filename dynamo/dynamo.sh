#!/bin/bash
aws cloudformation deploy \
--region us-west-2 \
--parameter-overrides DynamoName="DynamoPlatzi" DynamoKey="cc" \
--stack-name dynamo-lambda-lab \
--template-file ./dynamo.yml
