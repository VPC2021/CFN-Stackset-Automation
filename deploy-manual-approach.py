#!/usr/bin/env python3
import boto3
import json

def deploy_manual_approach():
    session = boto3.Session(profile_name='REPLACE_WITH_YOUR_PR')
    cf = session.client('cloudformation')
    stackset_name = "StackSet-Name"
    
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
            continue
    
    # Show remaining accounts after this deployment
    remaining_after = len(accounts_to_deploy) - 1
    if remaining_after > 0:
        print(f"\n📋 Run script again to deploy remaining {remaining_after} accounts")
    else:
        print(f"\n🎉 All accounts deployed successfully!")

if __name__ == "__main__":
    deploy_manual_approach()