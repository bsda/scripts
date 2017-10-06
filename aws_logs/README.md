## AWS custom logs

Some ugly scripts used to generate some useful custom logs from aws to be ingest by splunk (or any other siem/logging aggregator)


## splunk_aws_credentials_report.py
Downloads the usual Credential Reports and adds the access keys for each user and which groups the user is a mamber of


## splunk_aws_public_ip_summary.py
Script to generate a list of all public IPs assigned to instances or ELBs in a format that resembles firewall rules
It will create a line for each security group rule found per IP addreess
