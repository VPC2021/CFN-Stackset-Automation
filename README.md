
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

## 🚀 Deployment Steps

### 1. Validate CloudFormation Template
```bash
aws cloudformation validate-template   --template-body file://template.yaml   --profile deployment-admin
```

### 3. Deploy to Target Accounts

#### Option A: Fully Automated (Recommended)
```bash
python deploy-auto-loop.py
```

- Auto-deploys to all listed accounts
- Waits for each operation to complete
- Handles conflicts and retries
- Shows progress summary

#### Option B: Manual (One Account at a Time)
```bash
python deploy-manual-approach.py
```

---

## 🔍 Verifying Deployment

### StackSet & Instance Info
```bash
aws cloudformation describe-stack-set   --stack-set-name <STACKSET_NAME>   --profile deployment-admin

aws cloudformation list-stack-instances   --stack-set-name <STACKSET_NAME>   --profile deployment-admin
```

### Check Parameter Overrides
```bash
aws cloudformation describe-stack-instance   --stack-set-name <STACKSET_NAME>   --stack-instance-account <ACCOUNT_ID>   --stack-instance-region <REGION>   --profile deployment-admin   --query 'StackInstance.ParameterOverrides'
```

---

## 🧠 Best Practices

- Use **naming conventions** with environment prefixes
- Keep your **templates modular and reusable**
- Version control your **parameter files and scripts**
- Test deployments in **sandbox environments first**
- Enable **CloudTrail** and **CloudWatch** for audit and monitoring

---

## 🛠️ Maintenance Tips

- Update parameters via the config file and redeploy
- Add accounts by extending the JSON and rerunning the script
- Remove accounts by deleting instances before config update
- Use drift detection to monitor configuration changes

---

## 📊 Monitoring Tools

```bash
aws cloudformation list-stack-set-operations   --stack-set-name <STACKSET_NAME>   --profile deployment-admin

aws cloudformation describe-stack-set-operation   --stack-set-name <STACKSET_NAME>   --operation-id <OPERATION_ID>   --profile deployment-admin
```

---

## ❗ Troubleshooting

| Problem | Solution |
|---------|----------|
| StackSet fails to create | Check IAM permissions & template syntax |
| Instances fail to deploy | Validate execution role and trust setup |
| Parameter overrides not applied | Confirm parameter names match template |
| CLI profile not working | Check AWS credentials and region settings |
| Conflicts during deployment | Use `deploy-auto-loop.py` with retry logic |

---

## 📈 Benefits of This Approach

- ✅ **Consistency** across environments
- ✅ **Single source of truth** for infrastructure
- ✅ **Scalability** to dozens of accounts
- ✅ **Auditability** with centralized operations

---

## 🛡️ Security Considerations

- Restrict StackSet admin roles to privileged users
- Use `AssumeRole` policies for cross-account access
- Enable rollback in templates for safe deployment
- Regularly audit IAM permissions

---

## 👥 Contributors

Maintained by the Cloud Platform Team.  
For questions or improvements, please raise an issue or contact us at [cloud-platform@example.com](mailto:cloud-platform@example.com)

---

**License**: MIT  
**Last Updated**: 2024
