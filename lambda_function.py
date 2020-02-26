#!/usr/bin/python

import sys
import logging
import pymysql
import time
# import boto3
import simplejson as json

# rds settings
rds_host  = "erj-uat.cxz4ohwzcbuk.ap-northeast-1.rds.amazonaws.com"
name = "elsevierreview"
password = "El$*%SeV1er"
db_name = "elsevierreview_prod"

# rds_host  = "loalhost"
# name = "newuser"
# password = "password"
# db_name = "elsevierreviewuat"
port = 3306

# logging
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# connect db
try:
    conn = pymysql.connect(rds_host, user=name,
                           passwd=password, db=db_name, connect_timeout=5)
except:
    logger.error("ERROR: Unexpected error: Could not connect to MySql instance.")
    sys.exit()

logger.info("SUCCESS: Connection to RDS mysql instance succeeded")

headers = {"Content-Type": "application/json"}

# executes upon API event
def lambda_handler(event, context):
    """
    This function inserts content into mysql RDS instance
    """
    # s3 = boto3.client('s3')
    item_count = 0
    with conn.cursor() as cur:
        uniqueid = event.unique_id
        # uniqueid = '117715'
        cur.execute("SELECT quiz FROM `mdl_quiz_attempts` where uniqueid = '" + uniqueid + "'")
        fields = map(lambda x:x[0], cur.description)
        quiz = [dict(zip(fields,rowh))   for rowh in cur.fetchall()]

        cur.execute("select m.id , questionid, qtype from mdl_question_attempts m JOIN mdl_question q ON m.questionid=q.id WHERE questionusageid ='" + uniqueid + "'")
        records = {}
        
        try:
            for row in cur.fetchall():
                # check question types
                if row[2] == 'freetext':
                    state_str = "todo"
                elif row[2] == "testinputfc":
                    state_str = "invalid"
                else:
                    state_str = "complete"

                cur.execute("select * from mdl_question_attempt_steps WHERE questionattemptid ='%s' AND state ='%s' ORDER BY sequencenumber DESC LIMIT 0,1" % (row[0],state_str))
                fields = map(lambda x:x[0], cur.description)
                result = [dict(zip(fields,rowh))   for rowh in cur.fetchall()]

                
                if result:
                    records[row[1]] = {'mdl_question_attempt_steps':result}

                    if (row[2] == 'multichoice'):

                        cur.execute("SELECT * FROM `mdl_question_attempt_step_data` WHERE attemptstepid='%s' AND name = 'answer'" % (result[0]['id']))
                        fields = map(lambda x:x[0], cur.description)
                        user_input = [dict(zip(fields,rowh))   for rowh in cur.fetchall()]
                        # print(user_input)

                        records[row[1]].update({'mdl_question_attempt_step_data':user_input})           
                            
                        cur.execute("SELECT * FROM `mdl_quiz_question_answers` where question = '%s' AND quiz = '%s' ORDER BY id ASC LIMIT %s ,1" % (row[1],quiz[0]['quiz'],user_input[0]['value']))
                        fields = map(lambda x:x[0], cur.description)
                        answer = [dict(zip(fields,rowh))   for rowh in cur.fetchall()]
                        # print(answer)

                        records[row[1]].update({'mdl_quiz_question_answers':answer})

                        cur.execute("SELECT * FROM `mdl_question_answers` where id = '%s'" % (answer[0]['answer']))
                        fields = map(lambda x:x[0], cur.description)
                        response = [dict(zip(fields,rowh))   for rowh in cur.fetchall()]
                        # print(response)

                        records[row[1]].update({'mdl_question_answers':response})

                        cur.execute("UPDATE `mdl_question_attempts` SET responsesummary = '%s' , timemodified = '%s' WHERE questionid='%s'" % (response[0]['answer'],time.time(),row[1]))
                        conn.commit()

                    elif row[2] != 'oumultiresponse':

                        cur.execute("SELECT * FROM `mdl_question_attempt_step_data` WHERE attemptstepid='%s' AND name = 'answer'" % (result[0]['id']))
                        fields = map(lambda x:x[0], cur.description)
                        user_input = [dict(zip(fields,rowh))   for rowh in cur.fetchall()]
                        records[row[1]].update({'mdl_question_attempt_step_data':user_input})
                        print(answers)

                        cur.execute("UPDATE TABLE `mdl_question_attempts` SET responsesummary = '%s' , timemodified = '%s' WHERE questionid='%s'" % (user_input[0]['value'],time.time(),row[1]))
                        conn.commit()     
                    else:
                        print(result[0]['id'])
                        # user_choices = []
                        cur.execute("SELECT * FROM `mdl_question_attempt_step_data` WHERE value = 1 AND attemptstepid='%s' AND name LIKE '%s'" % (result[0]['id'], '%choice%')) 
                        user_choices = [dict(zip([column[0] for column in cur.description], row)) for row in cur.fetchall()]
                        print(user_choices)

                        records[row[1]].update({'mdl_question_attempt_step_data':user_choices})
                        summary_answers = []
                        data_record = []
                        for choices in user_choices:
                            user_input_choice = choices['name'].replace('choice','')

                            cur.execute("SELECT * FROM `mdl_quiz_question_answers` where question = '%s' AND quiz = '%s' ORDER BY id ASC LIMIT %s ,1" % (row[1],quiz[0]['quiz'],user_input_choice))
                            fields = map(lambda x:x[0], cur.description)
                            answer = [dict(zip(fields,rowh))   for rowh in cur.fetchall()]
                            print(answer)

                            records[row[1]].update({'mdl_quiz_question_answers':answer})

                            cur.execute("SELECT * FROM `mdl_question_answers` where id = '%s'" % (answer[0]['answer']))
                            fields = map(lambda x:x[0], cur.description)
                            response = [dict(zip(fields,rowh))   for rowh in cur.fetchall()]
                            print(response)

                            data_record.append(response)
                            summary_answers.append(response[0]['answer']) 

                        records[row[1]].update({'mdl_question_answers':data_record})
                        response_summary = ';'.join(summary_answers)
                        cur.execute("UPDATE `mdl_question_attempts` SET responsesummary = '%s' , timemodified = '%s' WHERE questionid='%s'" % (response_summary,time.time(),row[1]))
                        conn.commit()  
                else:
                    return json.dumps('No record'), 200, headers

            serializedMyData = json.dumps(records)
            print(serializedMyData)
            # Entries save in s3
            # s3.put_object(Body=serializedMyData,Bucket='info-facialapp',Key='uniqueId-'+ uniqueid)
            
        except:
            headers = {"Content-Type": "application/json"}
            return json.dumps('Unexpected error: '+str(sys.exc_info())), 200, headers

            # Entries save in s3
            # s3.put_object(Body=serializedMyData,Bucket='info-facialapp',Key='uniqueId-'+ uniqueid)
                # with open('/tmp/output2.csv', 'w') as data:
                #     data.write(record)
                # records.append(record)
                # logger.info(row)