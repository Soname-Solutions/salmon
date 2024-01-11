#!/bin/bash

# copy grafana configurations to S3 bucket
aws s3 cp s3://{settings_bucket_name}/settings/grafana/conf/datasources.yaml /opt/bitnami/grafana/conf/provisioning/datasources
aws s3 cp s3://{settings_bucket_name}/settings/grafana/conf/dashboards.yaml /opt/bitnami/grafana/conf/provisioning/dashboards
aws s3 cp s3://{settings_bucket_name}/settings/grafana/dashboards/ /opt/bitnami/grafana/data --recursive

# get Grafana admin password from Secret Manager and apply it
grafana_admin_password=$(aws secretsmanager get-secret-value --region {region} --secret-id {grafana_admin_secret_name} --query 'SecretString' --output text | jq -r '.password' )
sudo /opt/bitnami/grafana/bin/grafana cli --homepath=/opt/bitnami/grafana admin reset-admin-password ${grafana_admin_password} 

# install grafana-timestream-datasource plugin and restart Grafana 
sudo /opt/bitnami/grafana/bin/grafana cli --pluginsDir /opt/bitnami/grafana/data/plugins plugins install grafana-timestream-datasource
sudo /opt/bitnami/ctlscript.sh restart