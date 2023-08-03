import boto3
import pathlib
import os
from botocore.config import Config
from fpdf import FPDF
import sys
import json

def create_s3_bucket():#At some point make this a loop with exception handling
    boolean = False
    while boolean == False:
        value = input("Please insert the name of your S3 bucket. It must be one that already exists, or a new one with a unique name.\n")
        #print(value)
        try:
            s3 = boto3.client('s3')
            s3.create_bucket(Bucket = value)
            boolean = True
        except:
            print("Try again!")
    return value

def upload_image_or_pdf_to_s3_bucket(bucketname):
    filename = input("Please input the name of the file you are trying push to an s3 bucket.")
    file_and_path = "./" + filename
    client = boto3.client('s3', region_name = 'us-east-1')
    client.upload_file(file_and_path, bucketname, filename)
    return filename

def use_textract_and_return_array(bucketname, filename):
    my_config = Config(
        region_name = "us-east-1"
    )
    #Textract client
    textract = boto3.client('textract', config=my_config)
    #call aws textract
    response = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': bucketname,
                'Name': filename
            }
        }

    )

    #install this python3 -m pip install reportlab
    #run pip install fpdf
    array = []
    i = 0
    for item in response["Blocks"]:
        if item["BlockType"] == "LINE":
            i = i + 1
    array = [0 for i in range(i)]
    q = 0
    for item in response["Blocks"]:
        if item["BlockType"] == "LINE":
            array[q] = (item["Text"] + "\n")
            q = q + 1
    return array

def make_PDF(array):
    pdf = FPDF()
    pdf.add_page()
    #set style and font size wanted in pdf
    pdf.set_font("Arial", size = 15)
    for x in array:
        pdf.cell(200, 10, txt = x, ln = 1, align = 'C')
    #save the pdf with file_name.pdf
    pdf_name = input("Please type in the name that you want for this pdf:\n")
    pdf.output(pdf_name)
    return pdf_name


def verify_email():
    email = input("Please provide an email address:")
    ses_client = boto3.client("ses", region_name = "us-east-1")
    response1 = ses_client.verify_domain_identity(
        Domain = "testinguser1"
    )

    response2 = ses_client.verify_email_identity(
        EmailAddress = str(email)
    )
    return email

def use_ses(email):#email must be verified first
    prompt = input("Please verify your email before continuing. \n Press enter when ready")
    ses_client = boto3.client("ses", region_name = "us-east-1")

    try:
        response = ses_client.create_template(
            Template = {
                'TemplateName': 'Test',
                'SubjectPart': 'Test email',
                'TextPart': 'Pdf is complete',
                'HtmlPart': 'Pdf is complete'
            }
        )
    except:
        print("Please ignore this message")


    #template for method that should use ses to send an email 
    worker = '{"email_address":' + ' "' + email + '"' + '}'
    response = ses_client.send_templated_email(
        Source = email,
        Destination = {
            'ToAddresses': [email],
            'CcAddresses': [email],
        },
        ReplyToAddresses = [email],
        Template = 'Test',
        TemplateData = worker
    )

def create_sqs_queue():
    sqs_client = boto3.client("sqs", region_name = 'us-east-1')
    response = sqs_client.create_queue(
        QueueName = "my-new-queue",
        Attributes = {
            "DelaySeconds": "0",
            "VisibilityTimeout": "60",#60 Seconds
        }

    )
def return_url_of_new_queue():
    sqs_client = boto3.client("sqs", region_name="us-east-1")
    response = sqs_client.get_queue_url(
        QueueName="my-new-queue",
    )
    return response["QueueUrl"]

def send_sqs_message(url):
    sqs_client = boto3.client("sqs", region_name="us-east-1")

    message = {"Message": "There is a new file in your s3 bucket! This is to sqs."}
    response = sqs_client.send_message(
        QueueUrl = url,
        MessageBody = json.dumps(message)
    )
    print("There is now a message in sqs!")

def create_dynamodb_table():
    dynamodb = boto3.client('dynamodb', region_name = "us-east-1")
    try:
        table = dynamodb.create_table(
            TableName = 'FilesUploaded',
            KeySchema = [
                {
                    'AttributeName': 'FileName',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions = [
                {
                    'AttributeName': 'FileName',
                    'AttributeType': 'S'
                }

            ],
            ProvisionedThroughput = {
                'ReadCapacityUnits':10,
                'WriteCapacityUnits':10
            }
        )
    except:
        print("If your getting this message than that means a dynamodb table was already created in a previous go.")
    return "FilesUploaded"

def upload_to_dynamodb(table_name, filename):
    db = boto3.resource('dynamodb', region_name = "us-east-1")
    table = db.Table(table_name)

    table.put_item(
        Item = {
            'FileName': filename
        }
    )
  

if __name__ == '__main__':
    print("Hi and welcome to the text scraper!\n This code assumes that you will be using us-east-1 for your region.")
    bucketname = create_s3_bucket()
    filename = upload_image_or_pdf_to_s3_bucket(bucketname)#specify .png image here
    array = use_textract_and_return_array(bucketname, filename)
    pdf_file = make_PDF(array)
    upload_image_or_pdf_to_s3_bucket(bucketname)#specify newly created pdf here
    email = verify_email()
    use_ses(email)
    create_sqs_queue()
    url = return_url_of_new_queue()
    send_sqs_message(url)
    table_name = create_dynamodb_table()
    upload_to_dynamodb(table_name, filename)#also pass file name here