# 🔐 AWS StackSet Deployment Framework for Multi-Account Automation

This solution provides a flexible, automated approach for deploying CloudFormation StackSets across multiple AWS accounts using account-specific parameters.

The framework can be adapted for any multi-account use case that requires reliable infrastructure deployment and configuration propagation.

---

## 📌 Overview

This solution helps you:
- Deploy a CloudFormation StackSet to multiple AWS accounts and regions
- Apply **custom parameter overrides** per account
- Perform **template updates**, **parameter refreshes**, and **targeted deployments**
- Monitor progress and handle conflicts with built-in logic

---

## 📁 Included Files

- `Sample.yaml` – CloudFormation template (customize for your use case)
- `deploy-auto-loop.py` – Deployment script with update and retry logic
- `account-parameters.json` – Configuration file for account-specific parameters

---

## 🚀 Usage

### Initial Deployment

```bash
python deploy-auto-loop.py
```

- Creates the StackSet if not present
- Deploys to all accounts sequentially
- Applies custom parameters from configuration file

### Updating the Template

```bash
python deploy-auto-loop.py --update
```

- Updates the template for the StackSet
- Automatically applies to all existing stack instances

### Updating Parameters

**Single account:**
```bash
python deploy-auto-loop.py --update --account 123456789012
```

**All accounts:**
```bash
python deploy-auto-loop.py --update --update-params
```

### Custom Execution

```bash
python deploy-auto-loop.py \
  --profile my-profile \
  --stackset-name MyStackSet \
  --template my-template.yaml \
  --config my-config.json
```

---

## ⚙️ CLI Parameters

| Argument             | Default                   | Description                                 |
|----------------------|---------------------------|---------------------------------------------|
| `--profile`          | deployment-tools-admin    | AWS CLI profile name                        |
| `--stackset-name`    | IAM-Key-Status-Report     | Name of the StackSet                        |
| `--template`         | IAM-Key-Status-Report.yaml| Path to the CloudFormation template         |
| `--config`           | account-parameters.json   | Path to JSON config file                    |
| `--update`           | -                         | Enables update mode                         |
| `--account`          | -                         | Deploy/update a specific account            |
| `--update-params`    | -                         | Refreshes parameters for all instances      |

---

## 🧾 Configuration File Format

```json
{
  "accounts": [
    {
      "accountId": "123456789012",
      "regions": ["ap-southeast-2"],
      "parameters": [
        {"ParameterKey": "AccountName", "ParameterValue": "Production"},
        {"ParameterKey": "RecipientEmailAddresses", "ParameterValue": "admin@example.com"},
        {"ParameterKey": "ExpirationThresholdDays", "ParameterValue": "30"}
      ]
    }
  ]
}
```

---

## ✨ Key Features

- **Account-Specific Deployments**: Override parameters per account using JSON
- **Safe Sequential Rollout**: One account at a time to minimize risk
- **Built-In Retries**: Handles in-progress conflicts with retries
- **Flexible Updates**: Update template or parameters independently
- **Custom Profiles & Templates**: Works with any template and AWS CLI profile

---

## 🔍 Monitoring

- CloudFormation operation status printed in real-time
- Timeout handling included (20-minute default)
- Logs available in each target account’s CloudWatch

---

## ⚠️ Limitations

### Technical
- Only one StackSet operation can run at a time (AWS constraint)
- Deployments are sequential (no parallelization)
- StackSets must be supported in the selected regions
- Parameter updates require individual operations per account

### Operational
- IAM roles and trust relationships must be pre-configured
- Script requires pre-set AWS CLI profile with admin access
- Failed operations must be manually investigated
- Cross-account services (e.g., SES) require setup in advance

---

## ✅ Best Practices

1. Test with a single account using `--account`
2. Roll out in stages (Dev → QA → Prod)
3. Backup `account-parameters.json` in version control
4. Monitor progress during deployments and updates
5. Use CloudFormation drift detection periodically

---

## 🛠 Troubleshooting

**Common Issues & Fixes**

| Problem                         | Solution                                              |
|----------------------------------|--------------------------------------------------------|
| Operation already in progress   | Wait and retry; script handles this automatically      |
| Template update fails           | Check CloudFormation events in the AWS Console         |
| Parameter validation errors     | Validate JSON structure and parameter constraints      |
| IAM permission errors           | Verify StackSet roles and trust relationships          |
| Timeout or stuck deployments    | Check current operations and increase timeout if needed|

---

## 🧪 Example Use Cases

- IAM Access Key Auditing
- Organization-wide security guardrails
- Periodic reporting (e.g., cost, compliance, tag policies)
- Multi-account baseline provisioning

---
