#!/usr/bin/env python3
import boto3
import json
import time
import argparse

def update_stack_instances(cf, stackset_name, config, target_account=None):
    """Update existing stack instances"""
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
            print(f"❌ Error updating {account['accountId']}: {e}")
            continue

def deploy_auto_loop():
    session = boto3.Session(profile_name='REPLACE_ME')
    cf = session.client('cloudformation')
    stackset_name = "REPLACE_STACKSET_NAME"
    
    # Load configuration
    with open('account-parameters.json', 'r') as f:
        config = json.load(f)
    
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
    
    args = parser.parse_args()
    
    if args.update:
        session = boto3.Session(profile_name='REPLACE_ME')
        cf = session.client('cloudformation')
        stackset_name = "REPLACE_STACKSET_NAME"
        
        with open('account-parameters.json', 'r') as f:
            config = json.load(f)
        
        update_stack_instances(cf, stackset_name, config, args.account)
    else:
        deploy_auto_loop()