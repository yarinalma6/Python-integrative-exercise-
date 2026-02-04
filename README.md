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
