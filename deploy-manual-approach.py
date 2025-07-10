#!/usr/bin/env python3
import boto3
import json
import time
import argparse

def update_stack_instance(cf, stackset_name, config, target_account=None):
    """Update existing stack instance (manual approach - one at a time)"""
    try:
        existing_instances = cf.list_stack_instances(StackSetName=stackset_name)
        existing_accounts = {instance['Account'] for instance in existing_instances['Summaries']}
    except Exception as e:
        print(f"❌ Error listing stack instances: {e}")
        return
    
    if target_account:
        if target_account not in existing_accounts:
            print(f"❌ Account {target_account} not found in existing stack instances")
            return
        accounts_to_update = [acc for acc in config['accounts'] if acc['accountId'] == target_account]
    else:
        accounts_to_update = [acc for acc in config['accounts'] if acc['accountId'] in existing_accounts]
        if not accounts_to_update:
            print("❌ No existing stack instances found to update")
            return
        # For manual approach, update only the first account
        accounts_to_update = [accounts_to_update[0]]
    
    account = accounts_to_update[0]
    account_name = next(p['ParameterValue'] for p in account['parameters'] if p['ParameterKey'] == 'AccountName')
    
    print(f"🔄 Updating stack instance for account {account['accountId']} ({account_name})")
    print(f"Region: {account['regions']}")
    print(f"Parameter overrides: {account['parameters']}")
    
    try:
        response = cf.update_stack_instances(
            StackSetName=stackset_name,
            Accounts=[account['accountId']],
            Regions=account['regions'],
            ParameterOverrides=account['parameters']
        )
        
        operation_id = response['OperationId']
        print(f"✓ Stack instance update initiated - Operation ID: {operation_id}")
        
        print("Waiting for operation to complete...")
        
        for attempt in range(40):
            try:
                operation = cf.describe_stack_set_operation(
                    StackSetName=stackset_name,
                    OperationId=operation_id
                )
                status = operation['StackSetOperation']['Status']
                print(f"Operation status: {status}")
                
                if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
                    if status == 'SUCCEEDED':
                        print(f"✓ Stack instance updated successfully for {account['accountId']}")
                    else:
                        print(f"✗ Operation {status} for {account['accountId']}")
                    break
                
                time.sleep(15)
            except Exception as e:
                print(f"Error checking operation status: {e}")
                break
        
    except Exception as e:
        print(f"✗ Error updating {account['accountId']}: {str(e)}")

def deploy_manual_approach():
    session = boto3.Session(profile_name='REPLACE_ME')
    cf = session.client('cloudformation')
    stackset_name = "REPLACE_STACKSET"
    
    # Load configuration
    with open('account-parameters.json', 'r') as f:
        config = json.load(f)
    
    # Check existing instances
    try:
        existing_instances = cf.list_stack_instances(StackSetName=stackset_name)
        existing_accounts = {instance['Account'] for instance in existing_instances['Summaries']}
    except Exception as e:
        existing_accounts = set()
    
    # Find accounts that need deployment
    accounts_to_deploy = [account for account in config['accounts'] if account['accountId'] not in existing_accounts]
    
    print(f"StackSet Deployment Status:")
    print(f"✓ Deployed: {len(existing_accounts)} accounts")
    print(f"⏳ Remaining: {len(accounts_to_deploy)} accounts")
    
    if not accounts_to_deploy:
        print("\n🎉 All accounts have been deployed successfully!")
        return
    
    # Show next account to deploy
    next_account = accounts_to_deploy[0]
    account_name = next(p['ParameterValue'] for p in next_account['parameters'] if p['ParameterKey'] == 'AccountName')
    print(f"\n🚀 Next deployment: {next_account['accountId']} ({account_name})")
    
    # Deploy only the first pending account
    account = next_account
    
    account_name = next(p['ParameterValue'] for p in account['parameters'] if p['ParameterKey'] == 'AccountName')
    print(f"\nAdding stack instance for account {account['accountId']} ({account_name})")
    print(f"Region: {account['regions']}")
    print(f"Parameter overrides: {account['parameters']}")
    
    try:
        # This mimics the manual "Add stack instances" action
        response = cf.create_stack_instances(
            StackSetName=stackset_name,
            Accounts=[account['accountId']],
            Regions=account['regions'],
            ParameterOverrides=account['parameters']
        )
        
        operation_id = response['OperationId']
        print(f"✓ Stack instance creation initiated - Operation ID: {operation_id}")
        
        # Wait for this specific operation to complete (like the console does)
        print("Waiting for operation to complete...")
        
        # Poll operation status instead of using waiter
        for attempt in range(40):
            try:
                operation = cf.describe_stack_set_operation(
                    StackSetName=stackset_name,
                    OperationId=operation_id
                )
                status = operation['StackSetOperation']['Status']
                print(f"Operation status: {status}")
                
                if status in ['SUCCEEDED', 'FAILED', 'STOPPED']:
                    if status == 'SUCCEEDED':
                        print(f"✓ Stack instance deployed successfully to {account['accountId']}")
                    else:
                        print(f"✗ Operation {status} for {account['accountId']}")
                    break
                
                time.sleep(15)
            except Exception as e:
                print(f"Error checking operation status: {e}")
                break
        
    except Exception as e:
        print(f"✗ Error deploying to {account['accountId']}: {str(e)}")
    
    # Show remaining accounts after this deployment
    remaining_after = len(accounts_to_deploy) - 1
    if remaining_after > 0:
        print(f"\n📋 Run script again to deploy remaining {remaining_after} accounts")
    else:
        print(f"\n🎉 All accounts deployed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Deploy or update CloudFormation StackSet instances (manual approach)')
    parser.add_argument('--update', action='store_true', help='Update existing stack instance instead of deploying new one')
    parser.add_argument('--account', type=str, help='Target specific account ID for update operation')
    
    args = parser.parse_args()
    
    if args.update:
        session = boto3.Session(profile_name='REPLACE_ME')
        cf = session.client('cloudformation')
        stackset_name = "REPLACE_STACKSET"
        
        with open('account-parameters.json', 'r') as f:
            config = json.load(f)
        
        update_stack_instance(cf, stackset_name, config, args.account)
    else:
        deploy_manual_approach()