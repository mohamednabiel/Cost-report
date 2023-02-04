""" 
auther: Mohammed Nabil
date: 04/02/2023
description: This script will calculate the cost of the AWS resources EC2:,RDS in the account
             then it will send the cost to the SNS topic.
"""
import json
import boto3
import re
from pkg_resources import resource_filename



resources_region = "us-east-1"
aws_pricing_region= "us-east-1"

"""
explaination for extending the script to other AWS accounts:
1- Add a direct profile to the ~/.aws/credentials file and use it here 
   session = boto3.Session(profile_name="stylight-dev") then use the session to create the clients and resources
2- Assume a role in the other account and use it here
    sts_client = boto3.client('sts')
    assumed_role_object=sts_client.assume_role(
        RoleArn="arn:aws:iam::123456789012:role/role-name",
        RoleSessionName="AssumeRoleSession1"
    )
    credentials=assumed_role_object['Credentials']
    ec2_resource = boto3.resource(
        'ec2',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_key_id=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        region_name=resources_region
    )

"""
ec2_resource = boto3.resource("ec2", resources_region)
ec2_client = boto3.client("ec2", resources_region)
rds_client = boto3.client("rds", resources_region)
sns_client = boto3.client('sns',resources_region)
price_client = boto3.client("pricing", aws_pricing_region)

set_of_current_rds_instances_ids = []
set_of_currenct_rds_instances_prices = []

set_of_current_ec2_instances_ids = []
set_of_currenct_ec2_instances_prices = []


ebs_default_price = 0.05
number_of_days = 24
number_of_hours = 30

"""_summary_
        This function will get the price of the instance from the AWS pricing API response based oon json processing
    _input_
        response - the response from the AWS pricing API
        purchase_option_in - the purchase option of the instance (OnDemand, Reserved, etc.)
    _output_
        price_value - the price of the instance
    """
def get_price_from_pricelist(response,purchase_option_in="OnDemand"):
    for result in response['PriceList']:
        json_result = json.loads(result)
        for json_result_level_1 in json_result['terms'][purchase_option_in].values():
            for json_result_level_2 in json_result_level_1['priceDimensions'].values():
                for price_value in json_result_level_2['pricePerUnit'].values():
                    continue
    return float(price_value)

"""_summary_
    This function will extract the purchase option of the instance from the response based on text processing
    _input_
    response - the response from the AWS pricing API
    _output_
    value_purchase[0].strip() - the purchase option of the instance (OnDemand, Reserved, etc.)
    """
def extract_instatnce_purchase_type(response):
    output= response['PriceList']
    object = json.loads(output[0])
    terms_key_value=str(object['terms'])
    value_purchase=re.findall(r"'([^']*)'", terms_key_value)
    return value_purchase[0].strip()
    
"""_summary_
    This function will get the region name from the region code
    and will return the default region name if the region code is not found
    _input_
    region_code - the region code
    _output_
    region_name - the region name that works with the AWS pricing API
    """
def get_region_name(region_code):
    default_region = "EU (Ireland)"
    endpoint_file = resource_filename("botocore", "data/endpoints.json")
    try:
        with open(endpoint_file, "r") as f:
            data = json.load(f)
        return data["partitions"][0]["regions"][region_code]["description"]
    except IOError:
        return default_region

"""_summary_
    This function will get the price of the EC2 instance from the AWS pricing API
    _input_
    instance_type - the instance type
    region - the region of the instance with the default value of aws_pricing_region
    _output_
    price_value - the price of the instance from calling get_price_from_pricelist function
"""
def get_ec2_price(instance_type, region=aws_pricing_region):
    resolved_region = get_region_name(region)
    filter = [
        {'Field': 'instanceType',    'Value': instance_type,         'Type': 'TERM_MATCH'},
        {'Field': 'location',        'Value': resolved_region,       'Type': 'TERM_MATCH'},
        {'Field': 'capacitystatus',  'Value': 'Used',                'Type': 'TERM_MATCH'}
    ]
    try:
        response_ec2_price = price_client.get_products(ServiceCode="AmazonEC2", Filters=filter)
    except:
        print("can't find EC2 price")
    purchase_option=extract_instatnce_purchase_type(response_ec2_price)
    return get_price_from_pricelist(response_ec2_price,purchase_option)

"""_summary_
    This function will get the price of the EBS volume from the AWS pricing API
    _input_
    ebs_code - the EBS volume type
    region - the region of the EBS volume with the default value of aws_pricing_region
    _output_
    price_value - the price of the EBS volume from calling get_price_from_pricelist function    
    """     
def get_ebs_price(ebs_code, region=aws_pricing_region):
    if ebs_code == 'standard':
        return ebs_default_price # Just hard code this, it doesn't fit the search and is rarely used

    resolved_region = get_region_name(region)
    filter = [
        {'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': f"EBS:VolumeUsage.{ebs_code}"}, 
        {'Type': 'TERM_MATCH', 'Field': 'location',  'Value': resolved_region}
    ]
    try:
        response_ebs_price = price_client.get_products(ServiceCode='AmazonEC2', Filters=filter)
    except:
        print("can't find EBs price")
    purchase_option=extract_instatnce_purchase_type(response_ebs_price)

    return get_price_from_pricelist(response_ebs_price,purchase_option)

"""_summary_
    This function will get the price of the RDS instance from the AWS pricing API
    _input_ 
    instance_type - the instance type
    region - the region of the instance with the default value of aws_pricing_region
    _output_
    price_value - the price of the instance from calling get_price_from_pricelist function
"""
def get_rds_price(instance_type, region=aws_pricing_region):
    resolved_region = get_region_name(region)
    filter = [
        {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type}, 
        {'Type': 'TERM_MATCH', 'Field': 'location',  'Value': resolved_region}
    ]
    response = price_client.get_products(ServiceCode='AmazonRDS', Filters=filter)
    return get_price_from_pricelist(response)

"""_summary_
    This function will get the price of the RD instance type from the AWS pricing API
    _input_
    instance_id - the instance id
    _output_
    instance_type - the instance type
    """
def get_rds_instance_price_monthly(instance_id):
    try:
        response_rds_isntance_type = rds_client.describe_db_instances(DBInstanceIdentifier=instance_id)
    except:
        print("Instance not found")
        return 0
    instance_type=response_rds_isntance_type['DBInstances'][0]['DBInstanceClass']
    rds_monthly_price=get_rds_price(instance_type) * number_of_days * number_of_hours
    set_of_current_rds_instances_ids.append(instance_id)
    set_of_currenct_rds_instances_prices.append(rds_monthly_price)
    return rds_monthly_price

"""_summary_
    This function will get the price of the EC2 instance type from the AWS pricing API
     _input_
    instance_id - the instance id
    _output_
    total_monthly - the total price of the instance and the volumes attached to it    
        """
def get_ec2_instance_price_monthly(innstance_id):
    try:
        instance = ec2_resource.Instance(innstance_id)
    except:
        print("Instance not found")
        return 0
    try:
        volumes = instance.volumes.all()
    except:
        print("No volumes found")
        volumes = []
    vols = [(x.volume_type, int(x.size)) for x in volumes]
    instance_type = instance.instance_type
    ec2_monthly = get_ec2_price(instance_type) * number_of_days * number_of_hours
    total_monthly = 0 + ec2_monthly
    for vol in vols:
        vols_monthly = get_ebs_price(vol[0]) * vol[1]
    total_monthly += vols_monthly


    set_of_currenct_ec2_instances_prices.append(total_monthly)
    set_of_current_ec2_instances_ids.append(innstance_id)
    return total_monthly

"""_summary_
    This function for the lambda function to call
    _input_
    event - the event that triggered the lambda function
    context - the context of the lambda function
    _output_
    None
"""
def lambda_handler(event, context):
   main()

def main():
    print("Getting running instances")
    try:       
        request_ec2 = ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])
        for reservation in request_ec2["Reservations"]:
            for instance in reservation["Instances"]:
                id = instance["InstanceId"]
                print(f"Processing EC2 instances Id: {id}")
                get_ec2_instance_price_monthly(id)

    except Exception as error_ec2:
        print(error_ec2)
        raise error_ec2
    try:
        request_rds = rds_client.describe_db_instances()
        for instance in request_rds["DBInstances"]:
            id = instance["DBInstanceIdentifier"]
            print(f"Processing RDS Id: {id}")
            get_rds_instance_price_monthly(id)
    except Exception as error_rds:
        print(error_rds)
        raise error_rds

    print("The most expensive EC2 instance costs monthly: $",max(set_of_currenct_ec2_instances_prices),"and it's id is:",set_of_current_ec2_instances_ids[set_of_currenct_ec2_instances_prices.index(max(set_of_currenct_ec2_instances_prices))])
    print("The most expensive RDS instance costs monthly: $",max(set_of_currenct_rds_instances_prices),"and it's id is:",set_of_current_rds_instances_ids[set_of_currenct_rds_instances_prices.index(max(set_of_currenct_rds_instances_prices))])
    message = {set_of_current_ec2_instances_ids[set_of_currenct_ec2_instances_prices.index(max(set_of_currenct_ec2_instances_prices))]: max(set_of_currenct_ec2_instances_prices),
               set_of_current_rds_instances_ids[set_of_currenct_rds_instances_prices.index(max(set_of_currenct_rds_instances_prices))]: max(set_of_currenct_rds_instances_prices)}
    try:
        response_sns_publish = sns_client.publish(
        TargetArn='arn:aws:sns:us-east-1:755352676598:test-topic',
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json'
    )
    except Exception as error_sns:
        print(error_sns)
        raise error_sns

    print("Published to SNS topic with status code: ",response_sns_publish['ResponseMetadata']['HTTPStatusCode'])
    print("Done")
    
    
if __name__ == "__main__":
    main()
