import boto3
import click
import os
import datetime

# --- CONFIGURATION ---
try:
    current_user = os.getlogin()
except Exception:
    current_user = "Unknown_User"

# הגדרת תגיות גלובליות
GLOBAL_TAGS = {
    "CreatedBy": "yarin-platform-cli",
    "Owner": current_user,
    "Project": "CloudAutomation",
    "Environment": "Dev",
}

# שימוש בקבוע כדי למנוע Hardcoding בבדיקות
CLI_ID_TAG = {'Name': f'tag:CreatedBy', 'Values': [GLOBAL_TAGS['CreatedBy']]}

EC2_CONFIG = {
    "PROJECT_NAME": "yarinCLI",
    "REGION": "us-east-1",
    "ALLOWED_TYPES": ["t3.micro", "t2.small"],
    "MAX_INSTANCES": 2,
    "AMI_MAP": {
        "amazon": "ami-0532be01f26a3de55",
        "ubuntu": "ami-0b6c6ebed2801a5cb"
    }
}

S3_CONFIG = {
    "Location": "us-east-1",
    "Encryption": {
        'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]
    }
}

ROUTE53_CONFIG = {
    "DEFAULT_TTL": 300,
    "RecordType": "A"
}


# --- Helper Functions ---

def get_aws_tags(extra_tags=None):
    """Generates the tag list for AWS calls, merging global and specific tags."""
    if extra_tags is None:
        final_dict = GLOBAL_TAGS.copy()
    else:
        final_dict = {**GLOBAL_TAGS, **extra_tags}
    return [{'Key': k, 'Value': v} for k, v in final_dict.items()]


def is_route53_ours(client, zone_id):
    """
    בודקת האם Zone מסוים שייך לכלי שלנו.
    מונע שכפול קוד בין list ל-manage_records.
    """
    try:
        tags_data = client.list_tags_for_resource(
            ResourceType='hostedzone',
            ResourceId=zone_id
        )
        for tag in tags_data['ResourceTagSet']['Tags']:
            # משתמשים במשתנה הגלובלי במקום במחרוזת קשיחה
            if tag['Key'] == 'CreatedBy' and tag['Value'] == GLOBAL_TAGS['CreatedBy']:
                return True
        return False
    except Exception:
        return False


def count_my_instances(ec2_client):
    """Returns the number of instances created by this CLI."""
    # משתמשים בפילטר הקבוע שהגדרנו למעלה
    response = ec2_client.describe_instances(Filters=[CLI_ID_TAG])
    count = 0
    for i in response['Reservations']:
        count += len(i['Instances'])
    return count


# --- CLI Implementation ---

@click.group()
def cli():
    """My Tool"""
    pass


@cli.group()
def ec2():
    """EC2 Commands"""
    pass


@ec2.command(name='list')
def list_instances():
    """List instances created by this CLI"""
    ec2_client = boto3.client('ec2')
    # שימוש בפילטר הקבוע
    response = ec2_client.describe_instances(Filters=[CLI_ID_TAG])

    for i in response['Reservations']:
        for instance in i['Instances']:
            print(f"{instance['InstanceId']} ({instance.get('State', {}).get('Name')})")


@ec2.command()
@click.option('--name', required=True, help='Name of the instance')
@click.option('--os_type', default='amazon', help='OS type: amazon or ubuntu')
def create(name, os_type):
    """Create a new EC2 instance"""
    ec2_client = boto3.client('ec2')

    # בדיקת מכסה
    if count_my_instances(ec2_client) >= EC2_CONFIG['MAX_INSTANCES']:
        print("Error: Limit reached! You cannot create more than 2 instances.")
        return

    tag_specifications = get_aws_tags({'Name': name})
    ami_id = EC2_CONFIG['AMI_MAP'][os_type]

    ec2_client.run_instances(
        ImageId=ami_id,
        InstanceType='t3.micro',
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': tag_specifications}]
    )
    print("Instance created successfully!")


@ec2.command()
@click.option('--instance_id', required=True, help='ID of the instance to stop')
def stop(instance_id):
    """Stop an EC2 instance (only if created by this CLI)"""
    ec2_client = boto3.client('ec2')
    print(f"Checking permission for {instance_id}...")

    try:
        # שימוש בפילטר הקבוע - הכי יעיל ומדויק
        response = ec2_client.describe_instances(
            InstanceIds=[instance_id],
            Filters=[CLI_ID_TAG]
        )
    except Exception:
        print("Error: Instance ID not found.")
        return

    if len(response['Reservations']) == 0:
        print("Access Denied: This instance was not created by platform-cli.")
        return

    ec2_client.stop_instances(InstanceIds=[instance_id])
    print(f"Stopping instance {instance_id}... Done.")


# --- S3 Section ---
@cli.group()
def s3():
    """S3 Commands"""
    pass


@s3.command()
@click.option('--access', type=click.Choice(['public', 'private'], case_sensitive=False), help='Specify access type.')
@click.option('--name', required=True, help='Name of the bucket')
def create(name, access):
    """Creates a bucket"""
    if access == 'public':
        if not click.confirm(f'WARNING: Bucket {name} will be PUBLIC. Are you sure?', default=False):
            print('Aborted!')
            return

    print(f'Creating {access} bucket: {name}...')
    s3_client = boto3.client('s3')

    try:
        s3_client.create_bucket(Bucket=name)
        s3_client.put_bucket_encryption(
            Bucket=name,
            ServerSideEncryptionConfiguration=S3_CONFIG['Encryption']
        )
        s3_client.put_bucket_tagging(
            Bucket=name,
            Tagging={'TagSet': get_aws_tags()}
        )
        print("Bucket created successfully!")
    except Exception as e:
        print(f"Error: {e}")


@s3.command()
@click.option('--bucket', required=True, help='Target bucket name')
@click.option('--file', required=True, type=click.Path(exists=True), help='Path to file')
@click.option('--key', help='Rename the file in S3 (Optional)')
def upload(bucket, file, key):
    """Upload a file to S3"""
    s3_client = boto3.client('s3')
    target_name = key if key else file

    try:
        s3_client.upload_file(file, bucket, target_name)
        print(f"Uploaded '{file}' to '{bucket}' as '{target_name}'")
    except Exception as e:
        print(f"Error: {e}")


@s3.command()
@click.option('--bucket', required=True, help='Source bucket name')
@click.option('--key', required=True, help='The file name in S3 to download')
@click.option('--file', help='Local path to save the file (Optional)')
def download(bucket, key, file):
    """Download a file from S3"""
    s3_client = boto3.client('s3')
    local_filename = file if file else key

    try:
        s3_client.download_file(bucket, key, local_filename)
        print(f"Downloaded '{key}' from '{bucket}' to '{local_filename}'")
    except Exception as e:
        print(f"Error: {e}")


# --- Route53 Section ---
@cli.group()
def route53():
    """ROUTE53 Commands"""
    pass


@route53.command()
@click.option('--domain', required=True, help='Creates a Route53 Hosted Zone')
def create(domain):
    ref = str(datetime.datetime.now())
    client = boto3.client('route53')

    zone_tags = get_aws_tags({'Timestamp': ref})

    response = client.create_hosted_zone(Name=domain, CallerReference=ref)
    zone_id = response['HostedZone']['Id']

    client.change_tags_for_resource(
        ResourceType='hostedzone',
        ResourceId=zone_id,
        AddTags=zone_tags
    )
    print(f"Zone created! ID: {zone_id}")


@route53.command(name='list')
def list_routes():
    client = boto3.client('route53')
    all_zones = client.list_hosted_zones()

    for zone in all_zones['HostedZones']:
        # כאן השינוי הגדול: שימוש בפונקציית העזר במקום לשכפל את הלולאה
        if is_route53_ours(client, zone['Id']):
            print(f"{zone['Name']} ({zone['Id']})")


@route53.command()
@click.option('--zoneid', required=True, help='The zone id')
@click.option('--name', required=True, help='The name of zone ')
@click.option('--value', required=True, help='The ip of the zone')
@click.option('--action', type=click.Choice(['CREATE', 'DELETE', 'UPSERT']), help='The action')
def manage_records(zoneid, name, value, action):
    client = boto3.client('route53')

    # שימוש בפונקציית העזר לבדיקת הרשאות
    if not is_route53_ours(client, zoneid):
        print("Error: You cannot touch this zone! It belongs to someone else.")
        return

    try:
        client.change_resource_record_sets(
            HostedZoneId=zoneid,
            ChangeBatch={
                'Changes': [{
                    'Action': action,
                    'ResourceRecordSet': {
                        'Name': name,
                        'Type': ROUTE53_CONFIG['RecordType'],
                        'TTL': ROUTE53_CONFIG['DEFAULT_TTL'],
                        'ResourceRecords': [{'Value': value}]
                    }
                }]
            }
        )
        print(f"Successfully applied {action} on {name}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    cli()