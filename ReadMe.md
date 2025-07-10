
# 🧰 AWS CloudFormation StackSet Deployment Guide (Multi-Account Strategy)

This repository provides a standardized, scalable approach to deploying AWS CloudFormation templates across multiple accounts and regions using **StackSets** with **parameter overrides** per account.

---

## 📦 Project Structure

```
project-root/
├── template.yaml                  # CloudFormation template
├── account-parameters.json        # Per-account parameter values
├── deploy-auto-loop.py            # Automated multi-account deployer
├── deploy-manual-approach.py      # Manual deployment (one account at a time)
└── README.md                      # This documentation
```

---

## 🧭 Overview

This solution enables:
- Centralized infrastructure management from a **management account**
- Custom per-account settings using **ParameterOverrides**
- Safe, repeatable, and automated rollouts across multiple AWS accounts

---

## ✅ Prerequisites

1. **Management Account Access**: With permissions to manage StackSets.
2. **Target Accounts Configured**: Must have `AWSCloudFormationStackSetExecutionRole`.
3. **Cross-Account Trust**: Execution role must trust the admin role in the management account.
4. **AWS CLI & Python**: Ensure [`boto3`](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) and AWS CLI are installed.
5. **CLI Profile Setup**: Set up your AWS CLI profile (e.g., `deployment-admin`) to run commands.

---

## 🔐 Authentication Example

In Python scripts:
```python
import boto3
session = boto3.Session(profile_name='deployment-admin')
```

---

## ⚙️ Parameter Strategy

| Parameter Type | Description |
|----------------|-------------|
| StackSet Parameters | Shared across all accounts |
| ParameterOverrides | Unique per account (from config) |
| Template Defaults | Fallback if not overridden |

Parameter precedence:
1. ParameterOverrides
2. StackSet Parameters
3. Template Defaults

---

## 🧾 Configuration File Format (`account-parameters.json`)

```json
{
  "accounts": [
    {
      "accountId": "123456789012",
      "regions": ["us-east-1", "ap-southeast-2"],
      "parameters": [
        {"ParameterKey": "EnvironmentName", "ParameterValue": "Dev"},
        {"ParameterKey": "NotificationEmail", "ParameterValue": "team-dev@example.com"},
        {"ParameterKey": "ResourcePrefix", "ParameterValue": "dev"}
      ]
    }
  ]
}
```

---

## 🚀 Deployment & Operations Guide

### 1. Validate CloudFormation Template
```bash
aws cloudformation validate-template --template-body file://template.yaml --profile deployment-admin
```

### 2. Create StackSet (First Time Only)
```bash
aws cloudformation create-stack-set \
  --stack-set-name "S3LifecycleCleanupStackSet" \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_IAM \
  --profile deployment-admin
```

### 3. Deploy to Target Accounts

#### Option A: Fully Automated (Recommended)
```bash
# Deploy new instances to all accounts
python deploy-auto-loop.py

# Update all existing instances
python deploy-auto-loop.py --update

# Update specific account only
python deploy-auto-loop.py --update --account 123456789012
```

**Features:**
- Auto-deploys to all listed accounts
- Waits for each operation to complete
- Handles conflicts and retries
- Shows progress summary
- Supports bulk updates

#### Option B: Manual (One Account at a Time)
```bash
# Deploy next pending account
python deploy-manual-approach.py

# Update first existing instance
python deploy-manual-approach.py --update

# Update specific account only
python deploy-manual-approach.py --update --account 123456789012
```

**Features:**
- Step-by-step deployment control
- One account per execution
- Manual verification between deployments
- Ideal for testing or cautious rollouts

### 4. Update Operations

#### When to Use Updates
- Template changes (new resources, modified configurations)
- Parameter value changes in `account-parameters.json`
- Adding new parameters to existing stacks
- Fixing drift or configuration issues

#### Update Process
1. **Modify template or parameters**
2. **Update StackSet template** (if template changed):
   ```bash
   aws cloudformation update-stack-set \
     --stack-set-name "S3LifecycleCleanupStackSet" \
     --template-body file://template.yaml \
     --profile deployment-admin
   ```
3. **Run update command** using scripts above

---

## 🔍 Verification & Management

### StackSet & Instance Info
```bash
# View StackSet details
aws cloudformation describe-stack-set \
  --stack-set-name "S3LifecycleCleanupStackSet" \
  --profile deployment-admin

# List all instances
aws cloudformation list-stack-instances \
  --stack-set-name "S3LifecycleCleanupStackSet" \
  --profile deployment-admin
```

### Check Parameter Overrides
```bash
aws cloudformation describe-stack-instance \
  --stack-set-name "S3LifecycleCleanupStackSet" \
  --stack-instance-account 123456789012 \
  --stack-instance-region us-east-1 \
  --profile deployment-admin \
  --query 'StackInstance.ParameterOverrides'
```

### Instance Management

#### Remove Specific Instance
```bash
aws cloudformation delete-stack-instances \
  --stack-set-name "S3LifecycleCleanupStackSet" \
  --accounts 123456789012 \
  --regions us-east-1 \
  --profile deployment-admin
```

---

## 🧠 Best Practices

### Development Workflow
- Use **naming conventions** with environment prefixes
- Keep your **templates modular and reusable**
- Version control your **parameter files and scripts**
- Test deployments in **sandbox environments first**
- Use **feature branches** for template changes

### Operational Excellence
- Enable **CloudTrail** and **CloudWatch** for audit and monitoring
- Set up **SNS notifications** for operation status
- Use **manual approach** for production deployments
- Implement **rollback procedures** for failed deployments
- Document **parameter changes** in commit messages

---

## 🛠️ Maintenance & Lifecycle Management

### Regular Maintenance
- **Update parameters** via config file and run update commands
- **Add accounts** by extending JSON and rerunning deployment script
- **Remove accounts** by deleting instances before config update
- **Monitor drift** using AWS Config or CloudFormation drift detection

### Lifecycle Operations

#### Adding New Accounts
1. Add account configuration to `account-parameters.json`
2. Run deployment script: `python deploy-auto-loop.py`
3. Verify deployment in AWS Console

#### Template Updates
1. Modify `template.yaml`
2. Update StackSet: `aws cloudformation update-stack-set`
3. Update instances: `python deploy-auto-loop.py --update`

---

## 📊 Monitoring & Observability

### Operation Monitoring
```bash
# List recent operations
aws cloudformation list-stack-set-operations \
  --stack-set-name "S3LifecycleCleanupStackSet" \
  --profile deployment-admin

# Get detailed operation info
aws cloudformation describe-stack-set-operation \
  --stack-set-name "S3LifecycleCleanupStackSet" \
  --operation-id <OPERATION_ID> \
  --profile deployment-admin
```

---

## ❗ Troubleshooting Guide

### Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| StackSet fails to create | Check IAM permissions & template syntax |
| Instances fail to deploy | Validate execution role and trust setup |
| Parameter overrides not applied | Confirm parameter names match template |
| CLI profile not working | Check AWS credentials and region settings |
| Operation conflicts | Use `deploy-auto-loop.py` with retry logic |
| Timeout errors | Check target account connectivity |

### Debugging Steps

#### Check Failed Operations
```bash
aws cloudformation list-stack-set-operation-results \
  --stack-set-name "S3LifecycleCleanupStackSet" \
  --operation-id <OPERATION_ID> \
  --profile deployment-admin \
  --query 'Summaries[?Status==`FAILED`]'
```

#### Verify IAM Roles
```bash
aws iam get-role \
  --role-name AWSCloudFormationStackSetExecutionRole \
  --profile target-account-profile
```

---

## 📈 Benefits & Use Cases

### Key Benefits
- ✅ **Consistency** across environments and accounts
- ✅ **Single source of truth** for infrastructure
- ✅ **Scalability** to hundreds of accounts
- ✅ **Auditability** with centralized operations
- ✅ **Parameter flexibility** per account/environment
- ✅ **Automated rollouts** with error handling

### Common Use Cases
- **Multi-environment deployments** (Dev/Staging/Prod)
- **Security baselines** across organizations
- **Compliance requirements** and governance
- **Cost management** and resource optimization

---

## 🛡️ Security & Compliance

### Access Control
- **Restrict StackSet admin roles** to privileged users only
- **Use AssumeRole policies** for secure cross-account access
- **Implement MFA requirements** for admin operations
- **Regular IAM permission audits** and cleanup

### Deployment Security
- **Enable rollback** in templates for safe deployment
- **Use CloudTrail** for comprehensive audit logging
- **Validate templates** before deployment
- **Encrypt sensitive parameters** using AWS Systems Manager

### Compliance & Governance
- **Document all changes** with proper commit messages
- **Regular security reviews** of deployed resources
- **Compliance scanning** with AWS Config rules
- **Backup and disaster recovery** procedures

---
