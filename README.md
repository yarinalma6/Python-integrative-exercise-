# ️ Platform Engineering CLI Tool

A Python-based Command Line Interface (CLI) for automating AWS resource provisioning.
This tool allows developers to self-service **EC2 instances**, **S3 buckets**, and **Route53 DNS records** within safe, pre-defined boundaries.

##  Features
* **EC2:** Create (t3.micro/t2.small only), Stop, and List instances. Enforces a limit of 2 instances per user.
* **S3:** Create Private/Public buckets (with confirmation), Upload, and Download files. Enforces encryption (AES256) by default.
* **Route53:** Create Hosted Zones, Manage DNS records (A Records), and List zones.
* **Security:** Operates ONLY on resources tagged by this tool. Does not touch other resources in the account.

---

##  Prerequisites
Before running the tool, ensure you have:
1.  **Python 3.8+** installed.
2.  **AWS Account** with appropriate permissions.
3.  **AWS Credentials** configured locally (NEVER save secrets in this repo!).
    * Run `aws configure` in your terminal and enter your Access Key and Secret Key.

---

##  Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yarinalma6/Python-integrative-exercise-.git
    cd Python-integrative-exercise-
    ```

2.  **Install dependencies:**
    This will install `boto3`, `click`, and `awscli`.
    ```bash
    pip install -r requirements.txt
    ```

---

##  Tagging Strategy
This tool uses a strict tagging strategy to identify and manage resources.
Every resource created by the CLI is automatically tagged with:
* `CreatedBy`: **yarin-platform-cli** (This is the unique signature of the tool)
* `Owner`: Your system username
* `Project`: CloudAutomation
* `Environment`: Dev

**Note:** The CLI will ignore any resource that does not have the `CreatedBy` tag matching the tool's signature.

---

##  Usage Examples

### 1. EC2 Instances
```bash
Create a new instance (Amazon Linux or Ubuntu)
python main.py ec2 create --name web-server-1 --os_type amazon

# List all instances created by the tool
python main.py ec2 list

# Stop an instance
python main.py ec2 stop --instance_id i-0123456789abcdef0
```
### 2. S3 Bucket
```bash
# Create a PRIVATE bucket (Encrypted by default)
python main.py s3 create --name my-private-bucket-99 --access private

# Create a PUBLIC bucket (Requires confirmation)
python main.py s3 create --name my-public-site-99 --access public

# Upload a file
python main.py s3 upload --bucket my-private-bucket-99 --file test.txt

# Download a file
python main.py s3 download --bucket my-private-bucket-99 --key test.txt --file downloaded.txt
```
### 3. ROUTE53 (DNS)
```bash
# Create a new DNS Zone
python main.py route53 create --domain yarin-test.com

# List my zones
python main.py route53 list

# Add a DNS record (A Record)
python main.py route53 manage-records --zoneid Z0123456789 --name [www.yarin-test.com](https://www.yarin-test.com) --value 1.2.3.4 --action CREATE
```
# Python-integrative-exercise-
## Cleanup Instructions 🧹

To avoid unwanted charges, please follow these steps to remove resources created by the CLI:

1.  **EC2:**
    * Go to the AWS Console -> EC2 -> Instances.
    * Select instances created by the tool (tagged `CreatedBy: yarin-platform-cli`).
    * Select **Instance State** -> **Terminate**.

2.  **S3:**
    * Go to the AWS Console -> S3.
    * Find buckets created by the tool.
    * **Empty** the buckets first (delete all objects inside).
    * **Delete** the buckets.

3.  **Route53:**
    * Go to the AWS Console -> Route53 -> Hosted Zones.
    * Select the zone created by the tool.
    * Delete all record sets (except NS and SOA).
    * Click **Delete Zone**.

# Security Note
* This project adheres to security best practices:
* No hardcoded secrets: Credentials are loaded from the environment/AWS profile.
* Least Privilege: The tool filters resources by tags to prevent accidental modification of production resources.