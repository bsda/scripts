#!/usr/bin/env python

import boto3
import botocore
import datetime
import socket
import getopt
import logging
import os
import sys

logging.basicConfig(filename='/tmp/ec2_public_ips.log',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s: [ec2_public_ips:%(lineno)d] %(message)s')

logfile = '/var/log/aws/aws_public_ips-' + str(datetime.datetime.now().date()) + '.log'


def init_session(service, account, region):
    logging.info('Initiating new session. aws_account= ' + account + ', region= ' + region)
    session = boto3.session.Session(profile_name=account, region_name=region)
    return session.client(service)


def get_groups(account, region):
    try:
        client = init_session('ec2', account, region)
    except botocore.exceptions.ClientError as e:
        raise e
    logging.info('Getting security groups. aws_account= ' + account + ', region= ' + region)
    groups = client.describe_security_groups()['SecurityGroups']
    # new_rule = ''
    all_groups = list()
    group = dict()
    for g in groups:
        group[g['GroupId']] = dict()
        group[g['GroupId']]['group_name'] = g['GroupName']
        group[g['GroupId']]['rules'] = list()
        for rule in g['IpPermissions']:
            ips = list()
            if 'FromPort' in rule:
                if rule['FromPort'] == rule['ToPort']:
                    ports = rule['ToPort']
                else:
                    ports = str(rule['FromPort']) + ":" + str(rule['ToPort'])
            else:
                ports = "0:65535"
            if rule['IpProtocol'] == '-1':
                protocol = 'all'
            else:
                protocol = rule['IpProtocol']
                # ips = list()
            if 'IpRanges' in rule:
                for ip in rule['IpRanges']:
                    ips.append(ip['CidrIp'])
            # group_pairs = list()
            if 'UserIdGroupPairs' in rule:
                for gp in rule['UserIdGroupPairs']:
                    src_group_name = groups[index(groups, 'GroupId', 'sg-839a34e7')]['GroupName']
                    new_rule = {'protocol': protocol, 'ports': ports, 'src': gp['GroupId'] + " (" + src_group_name + ")"}
                    group[g['GroupId']]['rules'].append(new_rule)
            for ip in ips:
                new_rule = {'protocol': protocol, 'ports': ports, 'src': ip}
                group[g['GroupId']]['rules'].append(new_rule)
#        all_groups.append(group)
    return group


def get_instances_with_public_ips(account, region):
    client = init_session('ec2', account, region)
    logging.info('Getting ec2 instances. aws_account= ' + account + ', region= ' + region)
    instances = client.describe_instances()['Reservations']
    all_instances = list()
    for i in instances:
        for p in i['Instances']:
                if p['State']['Name'] == 'running':
                    if 'PublicIpAddress' in p:
                        all_instances.append(p)
    return all_instances


def get_elb_with_public_ips(account, region):
    client = init_session('elb', account, region)
    logging.info('Getting Elastic Load Balancers. aws_account= ' + account + ', region= ' + region)
    elbs = client.describe_load_balancers()['LoadBalancerDescriptions']
    public_elb = list()
    for elb in elbs:
        if elb['Scheme'] == 'internet-facing':
            elb['PublicIpAddress'] = socket.gethostbyname_ex(elb['DNSName'])[2]
            public_elb.append(elb)
    return public_elb


# Find position of security group in groups list
def index(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1


def usage():
    print 'Usage:'
    print os.path.basename(__file__) + ' -a <aws_account> (from ~/.aws/credentials)'
    sys.exit(0)


def main():
    """
    Script to get all public IPs from an aws account and correlate them with
    security groups in order to have a clear view of open ports.
    The script writes to a log file specified in the command line
    For splunk consumption.
    :return:
    """
    now = datetime.datetime.now()
    # account = ''
    # logfile = ''
    regions = ('us-east-1', 'us-west-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-northeast-1',
               'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'sa-east-1')

    try:
        opts, args = getopt.getopt(sys.argv[1:], "ha:", ['account='])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
        elif opt in ('-a', '--account'):
            account = arg
        else:
            assert False, "unhandled option"
    if 'account' in locals():
        for region in regions:
            log_buffer = list()
            try:
                groups = get_groups(account, region)
            except botocore.exceptions.ClientError as e:
                logging.critical('Failed to describe groups. aws_account=' + account + ', region=' + region)
                logging.critical(e)
                raise e
            try:
                instances = get_instances_with_public_ips(account, region)
            except botocore.exceptions.ClientError as e:
                logging.critical('Failed to describe instances. aws_account=' + account + ', region=' + region)
                logging.critical(e)
                raise e
            try:
                elbs = get_elb_with_public_ips(account, region)
            except botocore.exceptions.ClientError as e:
                logging.critical('Failed to describe elbs. aws_account=' + account + ', region=' + region)
                logging.critical(e)
                raise e
            for i in instances:
                tags = list()
                instance_name = 'null'
                if 'KeyName' in i:
                    key_name = i['KeyName']
                else:
                    key_name = 'null'
                if 'Tags' in i.keys():
                    for t in i['Tags']:
                        tags.append(t['Key'] + "=" + t['Value'])
                        if t['Key'] == 'Name':
                                instance_name = t['Value']
                for sg in i['SecurityGroups']:
                    sgid = sg['GroupId']
                    for rule in groups[sgid]['rules']:
                        log_line = (
                                '{time}, aws_public_ip="{aws_ip}", src="{src}", port_range="{ports}", '
                                'protocol="{proto}", instance_name="{instance_name}", instance_id="{instance_id}", '
                                'security_group_id="{sgid}", security_group_name="{sgname}", region="{region}", '
                                'account="{account}", tags="{tags}", type="ec2", '
                                'aws_public_dns="{public_dns}", key_name="{key_name}"'
                        ).format(aws_ip=i['PublicIpAddress'], src=rule['src'], ports=rule['ports'],
                                 proto=rule['protocol'], instance_name=instance_name,
                                 instance_id=i['InstanceId'], sgid=sgid, time=str(now),
                                 region=region, account=account, tags=", ".join(sorted(tags)),
                                 public_dns=i['PublicDnsName'], sgname=groups[sgid]['group_name'],
                                 key_name=key_name)
                        log_buffer.append(log_line)
            for lb in elbs:
                for sg in lb['SecurityGroups']:
                    sgid = sg
                    for rule in groups[sgid]['rules']:
                        public_ip = ", ".join(sorted(lb['PublicIpAddress']))
                        log_line = (
                            '{time}, aws_public_ip="{aws_ip}", src="{src}", port_range="{ports}", '
                            'protocol="{proto}", instance_name="{instance_name}", instance_id="null", '
                            'security_group_id="{sgid}", security_group_name="{sgname}", region="{region}", '
                            'account="{account}", tags="null", type="elb", aws_public_dns="{public_dns}", '
                            'key_name="null"'
                        ).format(aws_ip=public_ip, src=rule['src'], ports=rule['ports'],
                                 proto=rule['protocol'], instance_name=lb['LoadBalancerName'],
                                 sgid=sgid, time=str(now), region=region, account=account,
                                 public_dns=lb['DNSName'], sgname=groups[sgid]['group_name']
                                 )
                        log_buffer.append(log_line)
            with open(logfile, 'a') as public_ip_log:
                for item in log_buffer:
                    public_ip_log.write("%s\n" % item)
    else:
        usage()


if __name__ == "__main__":
    main()




