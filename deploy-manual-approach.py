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

def deploy_manual_approach(profile_name, stackset_name, template_file, config_file):
    session = boto3.Session(profile_name=profile_name)
    cf = session.client('cloudformation')
    
    # Load CloudFormation template
    with open(template_file, 'r') as f:
        template_body = f.read()
    
    # Create or update StackSet
    create_or_update_stackset(cf, stackset_name, template_body)
    
    # Load configuration
    with open(config_file, 'r') as f:
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
    parser.add_argument('--update-params', action='store_true', help='Update parameters for specific account (use with --update)')
    parser.add_argument('--profile', type=str, default='Profile-admin', help='AWS profile name (default: Profile-admin)')
    parser.add_argument('--stackset-name', type=str, default='Template', help='StackSet name (default: Template)')
    parser.add_argument('--template', type=str, default='Template.yaml', help='CloudFormation template file (default: Template.yaml)')
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
        
        # Only update instances if specific account requested and update-params flag used
        if args.account and args.update_params:
            with open(args.config, 'r') as f:
                config = json.load(f)
            print(f"🔄 Updating parameters for account: {args.account}")
            update_stack_instance(cf, args.stackset_name, config, args.account)
        elif args.account:
            print(f"ℹ️ Template updated for StackSet. Use --update-params to also update parameters for account {args.account}")
        else:
            print("✅ Template updated - changes will propagate to all instances automatically")
            print("ℹ️ Use --account and --update-params to update specific account parameters")
    else:
        deploy_manual_approach(args.profile, args.stackset_name, args.template, args.config)