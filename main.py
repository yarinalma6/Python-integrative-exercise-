import boto3
import click
import os
import datetime

# --- CONFIGURATION ---
# מנסה למצוא את שם המשתמש הנוכחי במערכת ההפעלה (לצורך תיעוד בטאגים)
try:
    current_user = os.getlogin()
# אם הפקודה נכשלה (למשל בסביבה וירטואלית מסוימת), תשתמש בשם ברירת מחדל
except:
    current_user = "Unknown_User"

# הגדרת מילון תגיות קבועות שיוצמדו לכל משאב שייווצר (כדי שנדע לזהות ולנהל אותו)
GLOBAL_TAGS = {
    "CreatedBy": "yarin-platform-cli",
    "Owner": current_user,
    "Project": "CloudAutomation",
    "Environment": "Dev",
}
CLI_ID_TAG = {'Name': f'tag:CreatedBy', 'Values': [GLOBAL_TAGS['CreatedBy']]}
# הגדרות קבועות מראש (כמו סוגי שרתים ו-AMI) כדי למנוע שימוש בערכים "קשיחים" בתוך הפונקציות
EC2_CONFIG = {
    "PROJECT_NAME": "yarinCLI",
    "REGION": "us-east-1",
    "ALLOWED_TYPES": ["t3.micro", "t2.small"],
    "MAX_INSTANCES": 2,
    "AMI_MAP": {
        "amazon": "ami-0532be01f26a3de55",  # שים לב: AMI משתנה בין Regions
        "ubuntu": "ami-0b6c6ebed2801a5cb"
    }
}
S3_CONFIG = {
    "Location": "us-east-1", # או Region אחר
    "Encryption": {
        'Rules': [
            {
                'ApplyServerSideEncryptionByDefault': {
                    'SSEAlgorithm': 'AES256'
                }
            }
        ]
    }
}

ROUTE53_CONFIG = {
    "DEFAULT_TTL": 300,
    "RecordType": "A"
}

    # Helper Functions
def get_aws_tags(extra_tags=None):
    # אם לא קיבלנו תגיות נוספות, נשתמש רק בגלובליות
    if extra_tags is None:
        final_dict = GLOBAL_TAGS.copy()
    else:
        #  חיבור שני המילונים
        # (הערכים ב-extra_tags ידרסו את GLOBAL אם יש כפילות במפתחות, וזה מעולה)
        final_dict = {**GLOBAL_TAGS, **extra_tags}

    # המרה לפורמט של AWS
    return [{'Key': k, 'Value': v} for k, v in final_dict.items()]


# מגדיר את הפונקציה הבאה כקבוצת הפקודות הראשית של הכלי (ה"גזע" של העץ)
@click.group()
# פונקציית הבסיס של ה-CLI, היא לא עושה כלום בעצמה אלא רק מאגדת את הפקודות האחרות
def cli():
    """My Tool"""
    # פקודה שאומרת לפייתון "אל תעשה כלום", נדרשת כי פונקציה לא יכולה להיות ריקה
    pass


# מגדיר את הפונקציה הבאה כתת-קבוצה תחת cli, שתרכז את כל פקודות ה-EC2
@cli.group()
# פונקציית הקבוצה לניהול EC2
def ec2():
    """EC2 Commands"""
    # פקודה שאומרת לפייתון "אל תעשה כלום"
    pass


# מגדיר את הפונקציה הבאה כפקודה ביצועית (Command) תחת קבוצת EC2
@ec2.command(name='list')
# הפונקציה שמבצעת את פעולת ה-List (הצגת השרתים)
def list_instances():
    """List instances created by this CLI"""
    # יצירת חיבור (Client) שמאפשר לנו לדבר עם שירות ה-EC2
    ec2_client = boto3.client('ec2')

    # שליחת הבקשה לאמזון: "תביא לי את השרתים, אבל רק אלו שעוברים דרך המסננת שהגדרתי"
    response = ec2_client.describe_instances(Filters=[CLI_ID_TAG])
    # התשובה מאמזון מגיעה במבנה של "קבוצות" (Reservations), אז הלולאה הראשונה פותחת את הקבוצות
    for i in response['Reservations']:
        # בתוך כל קבוצה יש את השרתים עצמם (Instances), הלולאה השנייה עוברת עליהם אחד אחד
        for instance in i['Instances']:
            # הדפסת תעודת הזהות (ID) של השרת למסך
            print(instance['InstanceId'])
# פונקציית עזר פנימית שבודקת כמה שרתים כבר קיימים בחשבון שנוצרו ע"י הכלי הזה

def count_my_instances():
    """Returns the number of instances created by this CLI"""
    # יוצר חיבור (Client) לשירות EC2 של אמזון לצורך ביצוע הבדיקה
    ec2_client = boto3.client('ec2')

    # מגדיר את תנאי הסינון: חפש רק שרתים שיש להם תגית CreatedBy עם הערך platform-cli
    # (שים לב: תיקנתי כאן את הגרשיים המיותרים שהיו בתוך השם של התגית)
    # שולח בקשה לאמזון לקבל רק את השרתים שעומדים בתנאי הסינון שהגדרנו למעלה
    response = ec2_client.describe_instances(Filters=[CLI_ID_TAG])
    # מאתחל משתנה ספירה ב-0
    count = 0

    # מתחיל לולאה שעוברת על התשובה שחזרה מאמזון כדי לספור את התוצאות
    for i in response['Reservations']:
        # עובר על כל שרת שנמצא בתוך רשימת השרתים שחזרה
        for instance in i['Instances']:
            count = count + 1

    # מחזיר את המספר הסופי של השרתים שנמצאו לפונקציה שקראה לי
    return count


# מגדיר את הפונקציה הבאה כפקודה ביצועית נוספת תחת קבוצת EC2
@ec2.command()
# מגדיר פרמטר שחובה להקליד אותו כשמריצים את הפקודה (שם השרת)
@click.option('--name', required=True, help='Name of the instance')
# מגדיר פרמטר אופציונלי לבחירת סוג מערכת ההפעלה, עם ערך ברירת מחדל 'amazon'
@click.option('--os_type', default='amazon', help='OS type: amazon or ubuntu')
# הפונקציה שיוצרת את השרת, מקבלת את הפרמטרים שהוגדרו למעלה
def create(name, os_type):
    """Create a new EC2 instance"""

    # קורא לפונקציית העזר שלנו כדי לבדוק אם הגענו כבר למכסה המקסימלית של 2 שרתים
    if count_my_instances() >= 2:
        print("Error: Limit reached!")
        # עוצר את ריצת הפונקציה כאן ויוצא החוצה (כדי למנוע את יצירת השרת)
        return
    # משתמש בפונקציית העזר כדי להכין את התגיות (משלב גלובליות + שם השרת)
    tag_specifications = get_aws_tags({'Name': name})
    # שולף את ה-ID של התמונה (AMI) מתוך הקובץ הגדרות למעלה, לפי מה שהמשתמש בחר
    ami_id = EC2_CONFIG['AMI_MAP'][os_type]
    # יוצר חיבור (Client) לשירות EC2 של אמזון
    ec2_client = boto3.client('ec2')
    #
    ec2_client.run_instances(
        # הפרמטר שמגדיר איזו מערכת הפעלה להתקין (לפי ה-ID ששלפנו קודם)
        ImageId=ami_id,
        # הפרמטר שמגדיר את עוצמת השרת (מעבד וזיכרון) - כרגע קבוע בקוד
        InstanceType='t3.micro',
        # מגדיר את מינימום השרתים ליצירה (חובה שיהיה לפחות 1)
        MinCount=1,
        # מגדיר את מקסימום השרתים ליצירה (כדי להבטיח שנוצר בדיוק שרת אחד)
        MaxCount=1,
        # מעביר לאמזון את רשימת התגיות שיצרנו, כדי שיודבקו על השרת
        TagSpecifications=[
            {
                # מציין שהתגיות האלו שייכות לשרת עצמו (ולא לרכיב אחר כמו דיסק)
                'ResourceType': 'instance',
                # כאן אנחנו מכניסים את הרשימה שיצרנו
                'Tags': tag_specifications
            }
        ]
    )

    print("Instance created successfully!")


# מגדיר את הפונקציה הבאה כפקודה תחת קבוצת EC2
@ec2.command()
# המשתמש חייב לספק את ה-ID של השרת שהוא רוצה לעצור
@click.option('--instance_id', required=True, help='ID of the instance to stop')
# הפונקציה שמבצעת את עצירת השרת בפועל, מקבלת את ה-ID כפרמטר
def stop(instance_id):
    """Stop an EC2 instance (only if created by this CLI)"""
    # יצירת חיבור ל-EC2 כדי שנוכל לשלוח פקודות לאמזון
    ec2_client = boto3.client('ec2')

    print(f"Checking permission for {instance_id}...")

    # מתחילים בלוק "ניסיון" (try) כדי למנוע מהתוכנה לקרוס אם המשתמש הזין ID שלא קיים בכלל
    try:
        # אנחנו מנסים לשלוף את השרת הספציפי הזה, אבל *רק* אם יש לו את התגית הנכונה
        response = ec2_client.describe_instances(
            # מגדיר שאנחנו מחפשים מידע ספציפית על ה-ID שהמשתמש הקליד
            InstanceIds=[instance_id],
            # מוסיף תנאי קריטי: תביא את השרת הזה *רק* אם יש לו את התגית שלנו (CreatedBy)
            Filters=[CLI_ID_TAG]
        )
    # אם ה-boto3 נכשל (למשל כי ה-ID לא תקין או לא קיים), הקוד יגיע לכאן במקום לקרוס
    except:
        # אם ה-ID לא קיים בכלל באמזון, הקוד יקפוץ לכאן
        print("Error: Instance ID not found.")
        return

    # אם אמזון החזירה רשימה ריקה, זה אומר שהשרת קיים (כי ה-try עבר), אבל אין לו את התגית שלנו (הפילטר סינן אותו)
    if len(response['Reservations']) == 0:
        print("Access Denied: This instance was not created by platform-cli.")
        return

    # אם הגענו לכאן - השרת הוא שלנו ומותר לעצור אותו!
    print(f"Stopping instance {instance_id}...")

    # שולח את פקודת העצירה הסופית לאמזון עבור ה-ID שאימתנו
    ec2_client.stop_instances(InstanceIds=[instance_id])

    print("Stop command sent successfully.")


# מגדיר את הפונקציה הבאה כתת-קבוצה תחת cli, שתרכז את כל פקודות ה-S3
@cli.group()
# פונקציית הקבוצה לניהול S3
def s3():
    """S3 Commands"""
    # פקודה שאומרת לפייתון "אל תעשה כלום"
    pass


# מגדיר את הפונקציה הבאה כפקודה ביצועית (Command) תחת קבוצת S3
@s3.command()
# מגדיר את הפרמטר access (סוג הגישה) שיועבר לפונקציה
@click.option(
    # השם של הדגל שכותבים בשורת הפקודה
    '--access',
    # מגביל את המשתמש לבחור אך ורק בין האופציות 'public' או 'private' (ולא רגיש לאותיות גדולות/קטנות)
    type=click.Choice(['public', 'private'], case_sensitive=False),
    # טקסט עזרה שיופיע אם המשתמש יקליד --help
    help='Specify the access type (public, private).'
)
# מגדיר את הפרמטר name (שם הדלי) שהוא חובה
@click.option('--name', required=True, help='Name of the bucket')
# הפונקציה שמבצעת את יצירת הדלי בפועל, מקבלת את השם והגישה שהמשתמש בחר
def create(name, access):
    """Creates a bucket"""

    # בדיקה: אם המשתמש בחר 'public', רק אז נפעיל את מנגנון האישור (הוספתי את השורה הזו לתיקון הלוגיקה)
    if access == 'public':
        # שואל את המשתמש "האם אתה בטוח?" ועוצר את התוכנית (return) אם התשובה היא "לא"
        if not click.confirm(f'WARNING: Bucket {name} will be PUBLIC. Are you sure?', default=False):
            print('Aborted!')
            return

    print(f'Creating {access} bucket: {name}...')

    # יצירת חיבור (Client) שמאפשר לנו לדבר עם שירות ה-S3 של אמזון
    s3_client = boto3.client('s3')

    # בלוק המנסה להריץ את הקוד, ותופס שגיאות אם משהו נכשל (למשל אם השם כבר תפוס ע"י מישהו אחר בעולם)
    try:
        # שולח את הפקודה לאמזון ליצירת הדלי עם השם שהתקבל
        s3_client.create_bucket(Bucket=name)
        # מוסיף את הגדרות ההצפנה (AES256) לדלי שיצרנו - חובה לפי הדרישות
        s3_client.put_bucket_encryption(
            Bucket=name,
            # משתמש בקונפיגורציה המוכנה מראש להצפנה
            ServerSideEncryptionConfiguration = S3_CONFIG['Encryption']
        )
        # מוסיף את התגיות לדלי (כי הפקודה create_bucket לא תומכת בזה)
        s3_client.put_bucket_tagging(
            Bucket=name,
            # משתמש בפונקציית העזר כדי לקבל את מבנה התגיות הנכון
            Tagging={'TagSet': get_aws_tags()}
        )
        print("Bucket created successfully!")

    # אם קרתה תקלה (כמו שם תפוס), הקוד יגיע לכאן וידפיס את השגיאה במקום לקרוס
    except Exception as e:
        print(f"Error: {e}")


# מגדיר את הפונקציה הבאה כפקודה ביצועית (Command) תחת קבוצת S3
@s3.command()
# מגדיר פרמטר חובה: שם הדלי שאליו אנחנו רוצים להעלות את הקובץ
# (הוספתי את ה -- בהתחלה כי זה חובה ב-Click)
@click.option('--bucket', required=True, help='Target bucket name')
# מגדיר פרמטר לקובץ, ומשתמש ב-Click כדי לוודא אוטומטית שהקובץ באמת קיים במחשב
# (בגלל exists=True, אם הקובץ לא קיים - התוכנית תעצור לבד ותזרוק שגיאה ברורה)
@click.option('--file', required=True, type=click.Path(exists=True), help='Path to file')
# פרמטר אופציונלי (בלי required=True)
@click.option('--key', help='Rename the file in S3 (Optional)')
# הפונקציה המבצעת את ההעלאה. מחקתי את ה-if הידני כי Click כבר עשה את הבדיקה למעלה
def upload(bucket, file, key):
    """Upload a file to S3"""

    # יצירת החיבור לשירות S3
    s3_client = boto3.client('s3')

    # בודקים האם המשתמש הזין ערך בפרמטר האופציונלי key
    if key:
        # אם כן - המשתמש רוצה לשנות את השם, אז נשתמש במה שהוא הקליד
        target_name = key

    # אחרת (אם המשתמש לא כתב כלום ב-key)
    else:
        # ברירת המחדל: השם בענן יהיה זהה בדיוק לשם (או הנתיב) של הקובץ במחשב
        target_name = file

    # מתחילים את תהליך ההעלאה בתוך בלוק הגנה (try) למקרה של תקלות
    try:
        # הפקודה המרכזית: מעלים את הקובץ (file) לדלי (bucket) ושומרים אותו תחת השם שבחרנו (target_name)
        s3_client.upload_file(file, bucket, target_name)

        # אם השורה למעלה הצליחה, מודיעים למשתמש שהכל עבר בשלום
        print(f"Uploaded '{file}' to '{bucket}' as '{target_name}'")


    # תופס שגיאות (כמו הרשאות חסרות או דלי שלא קיים) ומדפיס אותן
    except Exception as e:
        print(f"Error: {e}")


# מגדיר את הפונקציה הבאה כפקודה ביצועית (Command) תחת קבוצת S3
@s3.command()
# שם הדלי שממנו אנחנו רוצים להוריד (חובה)
@click.option('--bucket', required=True, help='Source bucket name')
# המפתח (שם הקובץ בענן) שאותו אנחנו רוצים להוריד (חובה - אחרת לא נדע מה להביא)
@click.option('--key', required=True, help='The file name in S3 to download')
# לאן לשמור במחשב? (אופציונלי)
@click.option('--file', help='Local path to save the file (Optional)')
# הפונקציה המבצעת את ההורדה
def download(bucket, key, file):
    """Download a file from S3"""

    # יצירת החיבור לשירות S3
    s3_client = boto3.client('s3')

    # בדיקה: האם המשתמש ביקש לשמור בשם ספציפי במחשב?
    if file:
        # אם כן - נשתמש בשם שהוא נתן
        local_filename = file

    # אחרת (המשתמש לא נתן שם לקובץ המקומי)
    else:
        # נשמור את הקובץ במחשב באותו שם בדיוק כמו שהוא מופיע בענן
        local_filename = key

    try:
        # מורידים מהדלי (bucket), את הקובץ (key), ושומרים למחשב (local_filename)
        # שים לב שהסדר בתוך הסוגריים השתנה לעומת ה-upload!
        s3_client.download_file(bucket, key, local_filename)

        # הודעת הצלח
        print(f"Downloaded '{key}' from '{bucket}' to '{local_filename}'")

    # תופס שגיאות (כמו קובץ שלא קיים בענן או בעיות רשת)
    except Exception as e:
        print(f"Error: {e}")

#
@cli.group()
#
def route53():
    """ROUTE53 Commands"""
    #
    pass


# מגדיר את הפונקציה הבאה כתת-קבוצה (Group) תחת cli, שתרכז את כל פקודות ה-Route53
@cli.group()
# פונקציית הקבוצה לניהול DNS. היא משמשת כ"אבא" לפקודות create ו-list
def route53():
    """ROUTE53 Commands"""
    # פקודה שאומרת לפייתון "אל תעשה כלום" (חובה כי הפונקציה ריקה מתוכן)
    pass


# מגדיר את הפונקציה הבאה כפקודה ביצועית (Command) תחת קבוצת route53
@route53.command()
# מגדיר פרמטר חובה: שם הדומיין שאנחנו רוצים ליצור (למשל my-site.com)
@click.option('--domain', required=True, help='Creates a Route53 Hosted Zone')
# הפונקציה שמבצעת את יצירת ה-Zone בפועל
def create(domain):
    # יוצר מחרוזת ייחודית (Timestamp) שתשמש כ-CallerReference
    # זה מונע מצב שבו לחיצה כפולה בטעות תיצור שני Zones ותחייב אותנו כפול
    ref = str(datetime.datetime.now())

    # יוצר חיבור (Client) לשירות ה-DNS של אמזון (Route53)
    client = boto3.client('route53')
    # מכין את רשימת התגיות מראש, כולל החותמת זמן הייחודית ל-Zone הזה
    zone_tags = get_aws_tags({'Timestamp': ref})
    # שולח בקשה ליצירת Zone חדש. שים לב שאי אפשר לשלוח פה תגיות!
    response = client.create_hosted_zone(
        # השם של הדומיין
        Name=domain,
        # המזהה הייחודי שיצרנו למעלה (חובה ב-Route53)
        CallerReference=ref
    )

    # מחלץ את ה-ID של ה-Zone החדש מתוך התשובה של אמזון
    # אנחנו חייבים את ה-ID הזה כדי שנוכל להוסיף עליו תגיות בשלב הבא
    # אמזון מחזירה מזהה עם קידומת "/hostedzone/..." שגורמת לשגיאה בפקודות אחרות.
    # הפקודה split('/')[-1] לוקחת רק את החלק שאחרי הלוכסן האחרון (ה-ID הנקי).
    zone_id = response['HostedZone']['Id'].split('/')[-1]
    # פעולה נפרדת להוספת תגיות (כי אי אפשר לעשות את זה ביצירה עצמה)
    client.change_tags_for_resource(
        # אומרים לאמזון שאנחנו רוצים לתייג Hosted Zone
        ResourceType='hostedzone',
        # אומרים לאמזון *איזה* Zone לתייג (לפי ה-ID שחילצנו)
        ResourceId=zone_id,
        # רשימת התגיות שאנחנו רוצים להדביק
        AddTags=zone_tags
    )

    # הודעת הצלחה למשתמש
    print(f"Zone created! ID: {zone_id}")


# מגדיר את הפונקציה הבאה כפקודה ביצועית (Command) תחת קבוצת route53
@route53.command(name='list')
# הפונקציה שמדפיסה את רשימת הדומיינים שנוצרו על ידי הכלי
def list_routes():
    # יוצר חיבור ל-Route53
    client = boto3.client('route53')

    # 1. מביאים את *כל* האזורים (Zones) שיש בחשבון, ללא סינון מוקדם
    all_zones = client.list_hosted_zones()

    # 2. לולאה שעוברת על כל Zone ברשימה שחזרה מאמזון
    for zone in all_zones['HostedZones']:
        # שומר את ה-ID של ה-Zone הנוכחי במשתנה זמני
        current_id = zone['Id'].split('/')[-1]
        # שומר את השם של ה-Zone הנוכחי (כדי להדפיס אותו בסוף אם הוא מתאים)
        current_name = zone['Name']

        # 3. מבקשים את התגיות עבור ה-ID הספציפי הזה בלבד
        # (מבצעים קריאה נוספת ל-AWS עבור כל דומיין ברשימה)
        tags_data = client.list_tags_for_resource(
            # סוג המשאב
            ResourceType='hostedzone',
            # ה-ID הספציפי שאנחנו בודקים כרגע
            ResourceId=current_id
        )

        # מחלץ את רשימת התגיות מתוך המבנה המורכב של התשובה
        actual_tags_list = tags_data['ResourceTagSet']['Tags']

        # לולאה פנימית שעוברת על כל תגית שיש ל-Zone הזה
        for tag in actual_tags_list:
            # בדיקה: האם התגית הנוכחית היא המפתח והערך שאנחנו מחפשים?
            if tag['Value'] == GLOBAL_TAGS['CreatedBy'] and tag['Key'] == 'CreatedBy':                # אם כן - מצאנו Zone שלנו! מדפיסים את שמו.
                print(current_name)


# מגדיר את הפונקציה הבאה כפקודה ביצועית (Command) תחת קבוצת Route53
@route53.command()
# מגדיר פרמטר חובה: ה-ID של ה-Zone שאותו אנחנו רוצים לערוך
@click.option('--zoneid', required=True, help='The zone id')
# מגדיר פרמטר חובה: שם הרשומה (הדומיין) המלא, למשל www.example.com
@click.option('--name', required=True, help='The name of zone ')
# מגדיר פרמטר חובה: הערך שאליו נפנה (כתובת ה-IP)
@click.option('--value', required=True, help='The ip of the zone')
# מגדיר את סוג הפעולה. משתמשים ב-Choice כדי להגביל את המשתמש רק לפעולות חוקיות
@click.option(
    '--action',
    # מגדיר את האפשרויות המותרות: יצירה, מחיקה, או עדכון (UPSERT)
    type=click.Choice(['CREATE', 'DELETE', 'UPSERT']),
    help='The action you want to do (CREATE/DELETE/UPSERT)'
)
# הפונקציה המבצעת את ניהול הרשומות. מקבלת את כל הפרמטרים שהגדרנו למעלה
def manage_records(zoneid, name, value, action):
    # יוצר חיבור (Client) לשירות ה-DNS של אמזון (Route53)
    client = boto3.client('route53')

    # מאתחל "דגל בטיחות". ברירת המחדל היא False (אנחנו מניחים שה-Zone לא שלנו עד שיוכח אחרת)
    is_our_zone = False

    # מתחיל בלוק מוגן (try) למקרה שהמשתמש הזין ID שגוי או לא קיים
    try:
        # שלב ב: בודקים תגיות *רק* עבור ה-ID הספציפי שהמשתמש ביקש
        # (בלי להביא את כל ה-Zones בעולם - חוסך זמן ומשאבים)
        tags_data = client.list_tags_for_resource(
            # מגדיר את סוג המשאב (Hosted Zone)
            ResourceType='hostedzone',
            # מעביר את ה-ID הספציפי לבדיקה
            ResourceId=zoneid
        )
        # לולאה שעוברת על כל התגיות שחזרו עבור ה-Zone הספציפי הזה
        for tag in tags_data['ResourceTagSet']['Tags']:
            # בדיקה: האם מצאנו את "החתימה" שלנו (CreatedBy = platform-cli)?
            if tag['Value'] == GLOBAL_TAGS['CreatedBy'] and tag['Key'] == 'CreatedBy':                # אם כן - מרים את הדגל לאישור (True)
                is_our_zone = True
                # מצאנו מה שחיפשנו, אין טעם להמשיך לבדוק תגיות אחרות
                break

                # תופס שגיאות כלליות (למשל אם ה-ID לא קיים ב-AWS)
    except Exception:
        # אם ה-ID בכלל לא קיים באמזון, תהיה שגיאה ונגיד שזה לא שלנו
        print("Error: Zone ID not found.")
        return

    # שלב ג: רגע האמת (השומר בכניסה). אם הדגל נשאר למטה (False) - עוצרים הכל!
    if not is_our_zone:
        print("Error: You cannot touch this zone! It belongs to someone else.")
        return

    # אם הגענו לפה, הכל תקין. שולחים את בקשת השינוי לאמזון
    client.change_resource_record_sets(
        # מזהה ה-Zone שבו נבצע את השינוי
        HostedZoneId=zoneid,
        # אובייקט שמכיל את רשימת השינויים לביצוע
        ChangeBatch={
            # רשימת השינויים (אנחנו שולחים שינוי אחד, אבל המבנה מחייב רשימה)
            'Changes': [
                {
                    # הפעולה לביצוע (מה שהמשתמש בחר: CREATE, DELETE, UPSERT)
                    'Action': action,
                    # הגדרת הרשומה עצמה
                    'ResourceRecordSet': {
                        # שם הדומיין (המפתח)
                        'Name': name,
                        # סוג הרשומה (A Record = כתובת IP)
                        'Type': 'A',
                        # זמן חיים (בשניות) - כמה זמן שרתי DNS אחרים יזכרו את הכתובת הזו
                        'TTL': ROUTE53_CONFIG['DEFAULT_TTL'],
                        # רשימת הערכים (לאן הדומיין יפנה)
                        'ResourceRecords': [
                            # הערך הספציפי (ה-IP שהמשתמש הזין)
                            {'Value': value}
                        ]
                    }
                }
            ]
        }
    )

    # (אופציונלי) כדאי להוסיף הודעת הצלחה בסוף
    print(f"Successfully applied {action} on {name}")


if __name__ == '__main__':
    cli()