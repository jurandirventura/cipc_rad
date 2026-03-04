#!/bin/bash

PROJECT_NAME=$1

mkdir -p $PROJECT_NAME/src/{download,processing,viewer}
mkdir -p $PROJECT_NAME/config

mkdir -p ../${PROJECT_NAME}_data/L2
mkdir -p ../${PROJECT_NAME}_output/{figures,gif,mp4}
mkdir -p ../${PROJECT_NAME}_logs

touch $PROJECT_NAME/.env
# It is not necessary if you have the environment.yml file. touch $PROJECT_NAME/requirements.txt
touch $PROJECT_NAME/README.md

echo "$PROJECT_NAME project created with success!"
