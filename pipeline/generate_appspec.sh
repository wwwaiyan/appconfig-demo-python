#!/bin/bash
if [ -z "$ECS_TASK_DEFINITION_ARN" ] || [ -z "$CONTAINER_NAME" ] || [ -z "$CONTAINER_PORT" ]; then
  exit 1
fi
sed -e "s|__TASK_DEFINITION__|$ECS_TASK_DEFINITION_ARN|g" \
    -e "s|__CONTAINER_NAME__|$CONTAINER_NAME|g" \
    -e "s|__CONTAINER_PORT__|$CONTAINER_PORT|g" \
    pipeline/appspec.yml.template > pipeline/appspec.yml