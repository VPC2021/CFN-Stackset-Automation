# Multi-Account CloudFormation StackSet Deployment Guide

## Overview
This document describes the standardized approach for deploying CloudFormation templates across multiple AWS accounts using StackSets with account-specific parameter customization. This methodology enables consistent infrastructure deployment while accommodating account-specific configurations.

## Architecture

### Core Components
- **CloudFormation StackSet**: Single template deployed across multiple accounts
- **Stack Instances**: Individual deployments in target accounts
- **Parameter Overrides**: Account-specific configuration values
- **Deployment Script**: Automated deployment orchestration

### Deployment Pattern
1. **Template Preparation**: Single CloudFormation template with parameterized values
2. **Configuration Setup**: Account-specific parameters defined in JSON configuration
3. **StackSet Creation**: Single StackSet created in management account
4. **Instance Deployment**: Multiple stack instances deployed with parameter overrides
5. **Validation**: Verify successful deployment across all target accounts

## Deployment Approach

### StackSet Strategy
- **1 StackSet** in management account
- **Multiple Stack Instances** (one per target account)
- **Account-specific parameters** via ParameterOverrides

### Files Structure
```
project-directory/
├── template.yaml                    # CloudFormation template
├── account-parameters.json          # Account configuration
├── deploy-with-config.py           # Deployment script
└── deployment-documentation.md      # This documentation
```

## Configuration

### Authentication
The deployment script uses AWS profile authentication:
```python
session = boto3.Session(profile_name='deployment-tools-admin')
```

**Important**: Use `deployment-tools-admin` profile (account: 394128373775) as the management account for StackSets, not `global-express-admin`.

### Template Parameters
| Parameter Type | Usage | Description |
|----------------|-------|-------------|
| **Common Parameters** | Same across all accounts | Shared configuration values (set in script) |
| **Account-Specific Parameters** | Varies per account | Customized values via ParameterOverrides (JSON file) |
| **Template Defaults** | Fallback values | Used when not specified in common or account-specific parameters |

### Parameter Hierarchy (precedence order)
1. **ParameterOverrides** (account-specific) - Highest priority
2. **StackSet Parameters** (common across all accounts)
3. **Template Default Values** - Lowest priority

### Important: Parameter Verification
**StackSet vs Stack Instance Parameters:**
- **StackSet Level**: Shows common parameters (what you see in StackSet console)
- **Stack Instance Level**: Uses account-specific parameter overrides (actual values used)

To verify parameter overrides are working:
```bash
# Check specific stack instance parameters
aws cloudformation describe-stack-instance --stack-set-name <STACKSET-NAME> --stack-instance-account <ACCOUNT-ID> --stack-instance-region <REGION> --profile deployment-tools-admin --query 'StackInstance.ParameterOverrides'
```

Example output showing working overrides:
```
RecipientEmailAddresses aws-notify-corporate-sandbox@teamglobalexp.com  False
AccountName     Corporate Sandbox       False
```

### Parameter Categories
- **Environment-specific**: Account names, email addresses, environment tags
- **Resource-specific**: Naming conventions, sizing, configuration values
- **Integration-specific**: Cross-account role ARNs, external service endpoints

### Account Configuration (account-parameters.json)
```json
{
  "accounts": [
    {
      "accountId": "123456789012",
      "regions": ["us-east-1", "ap-southeast-2"],
      "parameters": [
        {"ParameterKey": "EnvironmentName", "ParameterValue": "Production"},
        {"ParameterKey": "NotificationEmail", "ParameterValue": "team-prod@company.com"},
        {"ParameterKey": "ResourcePrefix", "ParameterValue": "prod"}
      ]
    },
    {
      "accountId": "234567890123",
      "regions": ["us-east-1"],
      "parameters": [
        {"ParameterKey": "EnvironmentName", "ParameterValue": "Development"},
        {"ParameterKey": "NotificationEmail", "ParameterValue": "team-dev@company.com"},
        {"ParameterKey": "ResourcePrefix", "ParameterValue": "dev"}
      ]
    }
  ]
}
```

## Deployment Steps

### Prerequisites
1. **Management Account Access**: CloudFormation StackSets permissions
2. **Target Account Setup**: StackSet execution roles configured (AWSCloudFormationStackSetExecutionRole)
3. **Cross-Account Roles**: Any required cross-account access roles configured
4. **Python Environment**: boto3 library installed
5. **AWS CLI Profile**: Configured with management account credentials (profile: `global-express-admin`)
6. **File Structure**: All files must be in the same directory

### Deployment Process

#### Step 1: Initial StackSet Creation
```bash
# Validate CloudFormation template
aws cloudformation validate-template --template-body file://template.yaml --profile deployment-tools-admin

# Create StackSet (one-time setup)
python deploy-with-config.py  # Creates StackSet with common parameters
```

#### Step 2: Configure Target Accounts
Update `account-parameters.json` with all target accounts:
```json
{
  "accounts": [
    {
      "accountId": "905418144846",
      "regions": ["ap-southeast-2"],
      "parameters": [
        {"ParameterKey": "RecipientEmailAddresses", "ParameterValue": "aws-notify-corporate-sandbox@teamglobalexp.com"},
        {"ParameterKey": "AccountName", "ParameterValue": "Corporate Sandbox"}
      ]
    }
  ]
}
```

#### Step 3: Deploy Stack Instances

**Option A: Automated Loop (Recommended)**
```bash
# Fully automated deployment - runs until all accounts are deployed
python deploy-auto-loop.py
```

**This script will:**
- Automatically deploy to all remaining accounts
- Check operation status before each deployment
- Wait for completion before proceeding to next account
- Handle operation conflicts by waiting and retrying
- Show real-time progress updates
- Stop automatically when all accounts are deployed

**Option B: Manual Step-by-Step**
```bash
# Deploy one account at a time (requires multiple runs)
python deploy-manual-approach.py
```

**This script will:**
- Deploy only the next pending account
- Show clear progress (deployed vs remaining)
- Require multiple script runs to complete all accounts

#### Step 4: Verify Deployment
```bash
# Check StackSet status
aws cloudformation describe-stack-set --stack-set-name S3LifecycleCleanupStackSet --profile deployment-tools-admin

# List all stack instances
aws cloudformation list-stack-instances --stack-set-name S3LifecycleCleanupStackSet --profile deployment-tools-admin

# Verify parameter overrides for specific account
aws cloudformation describe-stack-instance --stack-set-name S3LifecycleCleanupStackSet --stack-instance-account 905418144846 --stack-instance-region ap-southeast-2 --profile deployment-tools-admin --query 'StackInstance.ParameterOverrides'
```

#### Step 5: Monitor Operations
```bash
# Check recent operations
aws cloudformation list-stack-set-operations --stack-set-name S3LifecycleCleanupStackSet --profile deployment-tools-admin --max-items 5

# Check specific operation status
aws cloudformation describe-stack-set-operation --stack-set-name S3LifecycleCleanupStackSet --operation-id <OPERATION-ID> --profile deployment-tools-admin
```

## Best Practices

### Template Design
- **Parameterization**: Use parameters for account-specific values
- **Conditional Logic**: Implement conditions for environment-specific resources
- **Resource Naming**: Use consistent naming conventions with parameter-based prefixes
- **Output Values**: Define outputs for cross-stack references

### Configuration Management
- **Version Control**: Store configuration files in source control
- **Environment Separation**: Separate configuration files per environment group
- **Parameter Validation**: Use parameter constraints and allowed values
- **Documentation**: Document all parameters and their purposes

## Deployment Script Structure
```python
def deploy_stackset_from_config():
    # Load configuration and template
    # Create/Update StackSet with common parameters
    # Deploy instances with account-specific parameter overrides
    # Handle errors and provide status updates
```

### Key Functions
- **Configuration Loading**: Parse account-parameters.json
- **StackSet Management**: Create or update StackSet
- **Instance Deployment**: Deploy to multiple accounts with parameter overrides
- **Error Handling**: Graceful handling of deployment failures

## Monitoring and Maintenance

### CloudWatch Logs
- Lambda execution logs (5-day retention)
- Step Functions execution logs
- Error tracking and debugging

### Deployment Management
- **Incremental Updates**: Update existing StackSet and instances
- **Rollback Capability**: Built-in CloudFormation rollback mechanisms
- **Drift Detection**: Monitor for configuration drift across accounts

### Updates and Changes
1. **Template Updates**: Use `update_stack_set()` operation
2. **Parameter Changes**: Update account-parameters.json and redeploy
3. **Account Addition**: Add new accounts to configuration and run deployment script (incremental)
4. **Account Removal**: Remove stack instances before removing from configuration
5. **File Dependencies**: Script locates files using relative paths from current directory

### Deployment Behavior

#### Automated Loop Script (`deploy-auto-loop.py`)
**Recommended Method** - Fully automated deployment:
- **Continuous Loop**: Runs until all accounts are deployed
- **Operation Monitoring**: Checks for in-progress operations before deploying
- **Conflict Handling**: Automatically waits and retries on operation conflicts
- **Real-time Progress**: Shows deployment status and remaining accounts
- **Unattended Operation**: No manual intervention required

**Example Output:**
```
🔄 Starting automated StackSet deployment loop...

📊 Status: ✓ 15 deployed | ⏳ 2 remaining
🚀 Deploying: 749919732152 (Staging Parcels)
✓ Operation initiated: abc123...
⏳ Waiting for completion...
   Status: RUNNING
   Status: RUNNING
✅ Successfully deployed to 749919732152

📊 Status: ✓ 16 deployed | ⏳ 1 remaining
🚀 Deploying: 764897823219 (Staging TDA)
✓ Operation initiated: def456...
⏳ Waiting for completion...
✅ Successfully deployed to 764897823219

📊 Status: ✓ 17 deployed | ⏳ 0 remaining
🎉 All accounts deployed successfully!
```

#### Alternative Methods
- **Manual Step-by-Step**: `deploy-manual-approach.py` for controlled single deployments
- **CLI Batch Script**: `deploy-cli.bat` for Windows command-line deployment
- **Instances Only**: `deploy-instances-only.py` for adding instances without StackSet updates

## Troubleshooting

### Common Issues
| Issue | Solution |
|-------|----------|
| StackSet creation fails | Verify management account permissions and profile |
| Stack instance deployment fails | Check execution roles in target accounts |
| Parameter override not applied | Verify parameter key names match template |
| Cross-account access denied | Validate cross-account role ARNs and permissions |
| File not found error | Ensure all files are in same directory as script |
| Profile authentication fails | Verify `deployment-tools-admin` profile is configured |
| Only one account deploys per run | Use `deploy-auto-loop.py` for automated deployment or `deploy-manual-approach.py` for step-by-step |
| Parameter overrides not applied | Verify using: `aws cloudformation describe-stack-instance --query 'StackInstance.ParameterOverrides'` |
| Operation timeout or stuck | Check operation status and wait for completion before retrying |

### Validation Commands
```bash
# Check StackSet status
aws cloudformation describe-stack-set --stack-set-name <STACKSET-NAME> --profile deployment-tools-admin

# List stack instances
aws cloudformation list-stack-instances --stack-set-name <STACKSET-NAME> --profile deployment-tools-admin

# Check specific account deployment
aws cloudformation describe-stack-instance --stack-set-name <STACKSET-NAME> --stack-instance-account <ACCOUNT-ID> --stack-instance-region <REGION> --profile deployment-tools-admin

# Verify parameter overrides for specific account
aws cloudformation describe-stack-instance --stack-set-name <STACKSET-NAME> --stack-instance-account <ACCOUNT-ID> --stack-instance-region <REGION> --profile deployment-tools-admin --query 'StackInstance.ParameterOverrides'

# List StackSet operations
aws cloudformation list-stack-set-operations --stack-set-name <STACKSET-NAME> --profile deployment-tools-admin
```

## Advantages of This Approach

### Operational Benefits
- **Consistency**: Identical infrastructure across all accounts
- **Efficiency**: Single deployment operation for multiple accounts
- **Maintainability**: Centralized template management
- **Scalability**: Easy addition of new accounts

### Management Benefits
- **Governance**: Standardized deployment patterns
- **Compliance**: Consistent security and compliance configurations
- **Cost Control**: Centralized resource management
- **Audit Trail**: Complete deployment history and tracking

## Security Considerations

### IAM Permissions
- **Management Account**: StackSet administration permissions
- **Target Accounts**: StackSet execution roles with appropriate permissions
- **Cross-Account Access**: Properly configured trust relationships
- **Audit Trail**: All actions logged in CloudTrail

### Deployment Safety
- **Parameter Validation**: Template-level parameter constraints
- **Rollback Capability**: Automatic rollback on deployment failures
- **Testing**: Validate templates and configurations before production deployment
- **Monitoring**: Track deployment status and resource health

---