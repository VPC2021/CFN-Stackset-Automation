#!/usr/bin/env python3
import boto3
import json
import time
import argparse

def create_or_update_stackset(cf, stackset_name, template_body):
    """Create StackSet if it doesn't exist, or update if it does"""
    try:
        cf.describe_stack_set(StackSetName=stackset_name)
        print(f"🔄 Updating StackSet {stackset_name} template...")
        response = cf.update_stack_set(
            StackSetName=stackset_name,
            TemplateBody=template_body,
            Capabilities=['CAPABILITY_IAM']
        )
        
        # Wait for template update to complete
        operation_id = response['OperationId']
        print(f"⏳ Waiting for template update to complete...")
        
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            try:
                operation = cf.describe_stack_set_operation(
                    StackSetName=stackset_name,
                    OperationId=operation_id
                )
                status = operation['StackSetOperation']['Status']
                
                if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
                    if status == 'SUCCEEDED':
                        print(f"✅ StackSet {stackset_name} template updated")
                    else:
                        print(f"❌ Template update {status}")
                    break
                
                print(f"   Template update status: {status}")
                time.sleep(10)
                attempt += 1
                
            except Exception as e:
                print(f"Error checking template update status: {e}")
                break
        
        if attempt >= max_attempts:
            print(f"⚠️ Timeout waiting for template update")
            
    except cf.exceptions.StackSetNotFoundException:
        print(f"🔧 Creating StackSet {stackset_name}...")
        cf.create_stack_set(
            StackSetName=stackset_name,
            TemplateBody=template_body,
            Capabilities=['CAPABILITY_IAM'],
            Description='Default StackSet'
        )
        print(f"✅ StackSet {stackset_name} created")

def update_stack_instances(cf, stackset_name, config, target_account=None):
    """Update existing stack instances"""
    # Wait for any ongoing operations to complete
    print("⏳ Checking for ongoing operations...")
    max_wait_attempts = 30
    wait_attempt = 0
    
    while wait_attempt < max_wait_attempts:
        try:
            operations = cf.list_stack_set_operations(StackSetName=stackset_name, MaxResults=1)
            if operations['Summaries']:
                latest_op = operations['Summaries'][0]
                if latest_op['Status'] in ['RUNNING', 'STOPPING']:
                    print(f"⏳ Operation {latest_op['OperationId']} is {latest_op['Status']} - waiting...")
                    time.sleep(30)
                    wait_attempt += 1
                    continue
            break
        except Exception as e:
            print(f"Error checking operations: {e}")
            break
    
    try:
        existing_instances = cf.list_stack_instances(StackSetName=stackset_name)
        existing_accounts = {instance['Account'] for instance in existing_instances['Summaries']}
    except Exception as e:
        print(f"❌ Error listing stack instances: {e}")
        return
    
    # Filter accounts to update
    if target_account:
        if target_account not in existing_accounts:
            print(f"❌ Account {target_account} not found in existing stack instances")
            return
        accounts_to_update = [acc for acc in config['accounts'] if acc['accountId'] == target_account]
        print(f"🔄 Updating stack instance for account: {target_account}")
    else:
        accounts_to_update = [acc for acc in config['accounts'] if acc['accountId'] in existing_accounts]
        print(f"🔄 Updating {len(accounts_to_update)} stack instances...")
    
    for account in accounts_to_update:
        account_name = next(p['ParameterValue'] for p in account['parameters'] if p['ParameterKey'] == 'AccountName')
        print(f"🔄 Updating: {account['accountId']} ({account_name})")
        
        try:
            response = cf.update_stack_instances(
                StackSetName=stackset_name,
                Accounts=[account['accountId']],
                Regions=account['regions'],
                ParameterOverrides=account['parameters']
            )
            
            operation_id = response['OperationId']
            print(f"✓ Update operation initiated: {operation_id}")
            
            # Wait for operation to complete
            max_attempts = 60
            attempt = 0
            
            while attempt < max_attempts:
                try:
                    operation = cf.describe_stack_set_operation(
                        StackSetName=stackset_name,
                        OperationId=operation_id
                    )
                    status = operation['StackSetOperation']['Status']
                    
                    if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
                        if status == 'SUCCEEDED':
                            print(f"✅ Successfully updated {account['accountId']}")
                        else:
                            print(f"❌ Update {status} for {account['accountId']}")
                        break
                    
                    print(f"   Status: {status}")
                    time.sleep(20)
                    attempt += 1
                    
                except Exception as e:
                    print(f"Error checking status: {e}")
                    break
            
            if attempt >= max_attempts:
                print(f"⚠️ Timeout waiting for operation {operation_id}")
                
        except Exception as e:
            if "OperationInProgressException" in str(e):
                print(f"⏳ Another operation in progress for {account['accountId']} - will retry...")
                time.sleep(60)
                # Retry the same account
                continue
            else:
                print(f"❌ Error updating {account['accountId']}: {e}")
                continue

def deploy_auto_loop(profile_name, stackset_name, template_file, config_file):
    session = boto3.Session(profile_name=profile_name)
    cf = session.client('cloudformation')
    
    # Load CloudFormation template
    with open(template_file, 'r') as f:
        template_body = f.read()
    
    # Load configuration
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Create or update StackSet
    create_or_update_stackset(cf, stackset_name, template_body)
    
    print("🔄 Starting automated StackSet deployment loop...")
    
    while True:
        # Check existing instances
        try:
            existing_instances = cf.list_stack_instances(StackSetName=stackset_name)
            existing_accounts = {instance['Account'] for instance in existing_instances['Summaries']}
        except Exception as e:
            existing_accounts = set()
        
        # Find accounts that need deployment
        accounts_to_deploy = [account for account in config['accounts'] if account['accountId'] not in existing_accounts]
        
        print(f"\n📊 Status: ✓ {len(existing_accounts)} deployed | ⏳ {len(accounts_to_deploy)} remaining")
        
        if not accounts_to_deploy:
            print("🎉 All accounts deployed successfully!")
            break
        
        # Check if any operation is in progress
        try:
            operations = cf.list_stack_set_operations(StackSetName=stackset_name, MaxResults=1)
            if operations['Summaries']:
                latest_op = operations['Summaries'][0]
                if latest_op['Status'] in ['RUNNING', 'STOPPING']:
                    print(f"⏳ Operation {latest_op['OperationId']} is {latest_op['Status']} - waiting...")
                    time.sleep(30)
                    continue
        except Exception as e:
            print(f"Error checking operations: {e}")
        
        # Deploy next account
        next_account = accounts_to_deploy[0]
        account_name = next(p['ParameterValue'] for p in next_account['parameters'] if p['ParameterKey'] == 'AccountName')
        print(f"🚀 Deploying: {next_account['accountId']} ({account_name})")
        
        try:
            response = cf.create_stack_instances(
                StackSetName=stackset_name,
                Accounts=[next_account['accountId']],
                Regions=next_account['regions'],
                ParameterOverrides=next_account['parameters']
            )
            
            operation_id = response['OperationId']
            print(f"✓ Operation initiated: {operation_id}")
            
            # Wait for operation to complete (with timeout)
            print("⏳ Waiting for completion...")
            max_attempts = 60  # 20 minutes timeout
            attempt = 0
            
            while attempt < max_attempts:
                try:
                    operation = cf.describe_stack_set_operation(
                        StackSetName=stackset_name,
                        OperationId=operation_id
                    )
                    status = operation['StackSetOperation']['Status']
                    
                    if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
                        if status == 'SUCCEEDED':
                            print(f"✅ Successfully deployed to {next_account['accountId']}")
                        else:
                            print(f"❌ Operation {status} for {next_account['accountId']}")
                        break
                    
                    print(f"   Status: {status}")
                    time.sleep(20)
                    attempt += 1
                    
                except Exception as e:
                    print(f"Error checking status: {e}")
                    break
            
            if attempt >= max_attempts:
                print(f"⚠️ Timeout waiting for operation {operation_id}")
            
        except Exception as e:
            if "OperationInProgressException" in str(e):
                print("⏳ Another operation in progress - will retry...")
                time.sleep(60)
            elif "does not exist" in str(e).lower():
                print(f"❌ StackSet {stackset_name} not found - exiting")
                break
            else:
                print(f"❌ Error: {e}")
                time.sleep(30)
        
        # Brief pause before next iteration
        time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Deploy or update CloudFormation StackSet instances')
    parser.add_argument('--update', action='store_true', help='Update existing stack instances instead of deploying new ones')
    parser.add_argument('--account', type=str, help='Target specific account ID for update operation')
    parser.add_argument('--update-params', action='store_true', help='Update parameters for all accounts (use with --update)')
    parser.add_argument('--profile', type=str, default='Profile-admin', help='AWS profile name (default: Profile-admin)')
    parser.add_argument('--stackset-name', type=str, default='Default-Stackname', help='StackSet name (default: Default-Stackname)')
    parser.add_argument('--template', type=str, default='template.yaml', help='CloudFormation template file (default: template.yaml)')
    parser.add_argument('--config', type=str, default='account-parameters.json', help='Account parameters config file (default: account-parameters.json)')
    
    args = parser.parse_args()
    
    if args.update:
        session = boto3.Session(profile_name=args.profile)
        cf = session.client('cloudformation')
        
        # Load CloudFormation template
        with open(args.template, 'r') as f:
            template_body = f.read()
        
        # Create or update StackSet (template changes auto-propagate to instances)
        create_or_update_stackset(cf, args.stackset_name, template_body)
        
        # Update instances based on flags
        if args.account or args.update_params:
            with open(args.config, 'r') as f:
                config = json.load(f)
            
            if args.account:
                print(f"🔄 Updating parameters for account: {args.account}")
                update_stack_instances(cf, args.stackset_name, config, args.account)
            elif args.update_params:
                print("🔄 Updating parameters for all accounts...")
                update_stack_instances(cf, args.stackset_name, config)
        else:
            print("✅ Template updated - changes will propagate to all instances automatically")
    else:
        deploy_auto_loop(args.profile, args.stackset_name, args.template, args.config)