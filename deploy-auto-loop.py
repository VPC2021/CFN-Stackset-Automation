#!/usr/bin/env python3
import boto3
import json
import time

def deploy_auto_loop():
    session = boto3.Session(profile_name='REPLACE_ME')
    cf = session.client('cloudformation')
    stackset_name = "StackSet-Name"
    
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
            
            # Wait for operation to complete
            print("⏳ Waiting for completion...")
            while True:
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
                    
                except Exception as e:
                    print(f"Error checking status: {e}")
                    break
            
        except Exception as e:
            if "OperationInProgressException" in str(e):
                print("⏳ Another operation in progress - will retry...")
                time.sleep(60)
            else:
                print(f"❌ Error: {e}")
                time.sleep(30)
        
        # Brief pause before next iteration
        time.sleep(10)

if __name__ == "__main__":
    deploy_auto_loop()