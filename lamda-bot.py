from xmlrpc.client import Transport as XMLTransport
from xmlrpc.client import SafeTransport as XMLSafeTransport
from xmlrpc.client import ServerProxy as XMLServerProxy
from xmlrpc.client import _Method as XML_Method
import xml.parsers.expat
from xmlrpc.client import Error
import json
import boto3
import difflib
import logging
import time
import os
import re
from botocore.exceptions import ClientError
url = 'https://cert1-www.apac.elsevierhealth.com/'
apiuser = 'akanksha'
apipass = '11111111'
client = None
session = None
gevent = None


def confirmintent(content):
    global gevent
    return {"sessionAttributes": gevent['sessionAttributes'], "dialogAction": {"type": "ConfirmIntent", "intentName": gevent['currentIntent']['name'],
                                                                               "slots": gevent["currentIntent"]['slots'], "message": {"contentType": "PlainText", "content": content}}}
########################################################################################################################################################################

def ElicitSlot(content, slot):
    global gevent
    print(gevent)
    out = {"sessionAttributes": gevent['sessionAttributes'], "dialogAction": {"type": "ElicitSlot", "message": {"contentType": "PlainText", "content": content},
                                                                              "intentName": gevent['currentIntent']['name'], "slots": gevent['currentIntent']['slots'], "slotToElicit": slot}}
    out['sessionAttributes']['lastslottoelicit'] = slot
    out['sessionAttributes']['ShowingDisplay'] = "false"
    return out
################################################################################################################################################################


def delegateintent(t, content, event=None):
    global gevent
    return {"sessionAttributes": gevent['sessionAttributes'], "dialogAction": {"type": t, "intentName": gevent['currentIntent']['name'],
                                                                               "slots": gevent["currentIntent"]['slots'], "message": {"contentType": "PlainText", "content": content}}}
########################################################################################################################################################


def denied(resp):
    global gevent
    return {"sessionAttributes": {},
            "dialogAction": {"type": "Close", "fulfillmentState": "Failed", "message": {"contentType": "PlainText", "content": resp}}}
###############################################################################################################################################


def confirmed(resp):
    global gevent
    return {"sessionAttributes": gevent['sessionAttributes'],
            "dialogAction": {"type": "Close", "fulfillmentState": "Fulfilled", "message": {"contentType": "PlainText", "content": resp}}}
############################################################################Ok###########################################################


def searchbyname(name):
    return client.call(session, 'catalog_product.list', [{"type": "simple", "status": 1, "name": {"like": ("%"+name+"%")}}])
############################################################################################################


def searchatsolr(name):
    out = client.call(session, 'apisolrsearch_search.list', [22, str(name)])

    return out
############################################################################################################


def searchbyany(inp):
    # return client.call(session,'catalog_product.info',[(inp+" ")])
    print("here to call/search both ways")
    return client.multiCall(session, [['catalog_product.info', [(inp+" "), "22"]], ['catalog_product.list', [{"type": "simple", "status": 1, "name": {"like": ("%"+str(inp)+"%")}}, '22']]])
############################################################################################################


def buildtheconnection(event):
    global client, session
    print("cREATING SESSION")
    try:
        client = XMLServerProxy(
            "https://cert1-www.apac.elsevierhealth.com/index.php/api/xmlrpc?type=xmlrpc")
        session = client.login(apiuser, apipass)
    except Error as e:
        return denied("Sorry. I couldn't connect to Server.Please try after sometime.")
############################################################################################################


def findthebook(isbn):
    flag = False
    try:
        if (int(isbn))and len(isbn) == 13:
            return findthebookname(isbn)
    except ValueError as e:
        res = searchbyname(isbn)
        if len(res) == 0:
            out = ElicitSlot("No relevent Products were found.", "shopagain")
            out['dialogAction']['responseCard'] = retshopagain()
            out['sessionAttributes']['findit'] = False
            return out
        out = ElicitSlot("We have found some matches.", "shopagain")
        out['sessionAttributes']['findit'] = True
        rang = min(len(res), 5)
        print("This is out before response cards\n", out)
        list_of_books = list()
        for book in range(0, rang):
            list_of_books.append(
                [str(res[book]['name'].encode('utf-8').rstrip()[:30]), (book+1)])
        out['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": [{"title": "Book-title",
                                                                                                                                              "subTitle": "Book-sub-title", "buttons": createbutton(list_of_books)}]}
        print("This is out after cards\n", out)
        return out
############################################################################################################


def isitno(inp):
    no = ['no', 'noo', 'don\'t know', 'no!!', "nopes", 'nope!!',
          'naa', 'naah', 'naah!!', 'nahi', 'skip', "cancel"]
    inp = inp.lower()
    # if difflib.get_close_matches(inp,no) != []:
    # return 1
    for each in no:
        if inp in each or each in inp:
            return 1
    return 0
############################################################################################################


def findthebookname(isbn):
    global gevent
    print(isbn)
    res = searchatsolr(isbn)
    print(res)
    if not len(res):
        output = ElicitSlot(
            "Sorry, I didn't find any titles based on your input, wanna try again", "shopagain")
        output['dialogAction']['responseCard'] = retshopagain()
        print("was nothing")
        output['sessionAttributes']['cart'] = "no"
        if output['sessionAttributes'].get('Booksbought', None) == None:
            output['sessionAttributes']['Booksbought'] = " "
        output['sessionAttributes']['Buyornot'] = 'None'
        output['sessionAttributes']['BookList'] = "None"
        output['sessionAttributes']['Lastsearchmethod'] = ""
        output['sessionAttributes']['qty'] = 'None'
        if output['sessionAttributes'].get('lastslot', None) == None:
            output['sessionAttributes']['lastslot'] = 'None'
        output['sessionAttributes']['repeat'] = "None"
        output['sessionAttributes']['findit'] = False
        if output['sessionAttributes'].get('CartId', None) == None:
            output['sessionAttributes']['CartId'] = "None"
        return output
    else:
        out = ElicitSlot("Here are the findings", "Buyornot")
        res = res[:min(len(res), 10)]
        print("This is out before response cards\n", out)

        list_of_books = []
        for each in res:
            img = 'https://cert1-www.apac.elsevierhealth.com/media/catalog/product/9/7/9780323525886.jpg'
            #out2 = client.call(session,'catalog_product_attribute_media.list',[each['products_id']])
            # if len(out2) > 0 and out2[0]['url'] != None:# and len(out2[0]['url']) < 80:
            #img = out2[0]['url']
            discounted_price = ""
            if str(each['discounted_price']).lower() != "false" and len(str(each['discounted_price'])) != 0:
                discounted_price = "####@ $" + \
                    str(round(float(each['discounted_price']), 2))
            author = " "
            if str(each['author']).lower() != "none" and each['author'] != None:
                author = str(each['author']).split(",")[0][:30]
            list_of_books.append({"title": str(each['name'][:70]), "imageUrl": each['thumbnail_src'],
                                  "subTitle": author + "####! $"+str(round(float(each['original_price']), 2)) + discounted_price, "buttons": [{'text': "Add to cart", "value": str(each['name'])[:70]+";;;;"+str(each['sku'])}]})

        out['sessionAttributes']['findit'] = True
        out['sessionAttributes']['Lastsearchmethod'] = "name"
        out['sessionAttributes']['Lastsearchvalue'] = isbn
        out['sessionAttributes']['ShowingDisplay'] = "true"
        out['dialogAction']['responseCard'] = {
            "version": 2, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": list_of_books}

        print("This is out after cards\n", out)
        return out
############################################################################################################


def findthebooknamerecent(isbn):
    global gevent
    # buildtheconnection(gevent)
    out = searchbyany(isbn)
    if len(out[0]) > 3:
        out = out[0]
        prin("searching by isbn")
        print(out)
        if out['price'] == None:
            out['price'] = "Not available"
        if gevent['currentIntent']['slots']['start'] == None or "buy" in gevent['currentIntent']['slots']['start'].lower():
            output = ElicitSlot("This needs to be removed", "Buyornot")
        else:
            output = ElicitSlot("This needs to be removed", "Buyornot")
        if output['sessionAttributes'].get('Booksbought', None) == None:
            output['sessionAttributes']['Booksbought'] = " "
        output['sessionAttributes']['Lastsearchmethod'] = "isbn"
        output['sessionAttributes']['BookList'] = out['name']
        output['sessionAttributes']['cart'] = "no"
        output['sessionAttributes']['Buyornot'] = 'None'
        output['sessionAttributes']['qty'] = 'None'
        output['sessionAttributes']['lastslot'] = 'None'
        output['sessionAttributes']['repeat'] = "None"
        output['sessionAttributes']['findit'] = True
        if output['sessionAttributes'].get('CartId', None) == None:
            output['sessionAttributes']['CartId'] = "None"
        out2 = client.call(session, 'catalog_product_attribute_media.list', [
                           out["product_id"]])
        print(out2)
        price = out['pp_authorblistbyline'].split(
            ',')[0] + " ####!" + out['price']
        print(type(out['discounted_price']))
        if out['discounted_price']:
            price += "####@ $" + out['discounted_price']
        output['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic",
                                                  "genericAttachments": [{"title": out['name'][:79], "subTitle":price,
                                                                          "buttons":[{'text': "Add to cart", "value": "yes"}]}]}

        # and len(out2[0]['url']) < 80:
        if len(out2) > 0 and out2[0]['url'] != None:
            output['dialogAction']['responseCard']['genericAttachments'][0]['imageUrl'] = out2[0]['url']
        print(output)
        return output
    elif not len(out[1]):
        output = ElicitSlot(
            "Sorry, I didn't find any titles based on your input, wanna try again", "shopagain")
        output['dialogAction']['responseCard'] = retshopagain()
        print("was nothing")
        output['sessionAttributes']['cart'] = "no"
        if output['sessionAttributes'].get('Booksbought', None) == None:
            output['sessionAttributes']['Booksbought'] = " "
        output['sessionAttributes']['Buyornot'] = 'None'
        output['sessionAttributes']['BookList'] = "None"
        output['sessionAttributes']['Lastsearchmethod'] = ""
        output['sessionAttributes']['qty'] = 'None'
        if output['sessionAttributes'].get('lastslot', None) == None:
            output['sessionAttributes']['lastslot'] = 'None'
        output['sessionAttributes']['repeat'] = "None"
        output['sessionAttributes']['findit'] = False
        if output['sessionAttributes'].get('CartId', None) == None:
            output['sessionAttributes']['CartId'] = "None"
        return output
    else:
        res = out[1]
        out = ElicitSlot("Choose one of the below to buy.", "Buyornot")
        out['sessionAttributes']['findit'] = True
        res = res[:min(len(res), 10)]
        print("This is out before response cards\n", out)

        list_of_books = []
        for each in res:
            img = 'https://cert1-www.apac.elsevierhealth.com/media/catalog/product/9/7/9780323525886.jpg'
            #out2 = client.call(session,'catalog_product_attribute_media.list',[each['product_id']])
            # if len(out2) > 0 and out2[0]['url'] != None:# and len(out2[0]['url']) < 80:
            #img = out2[0]['url']
            list_of_books.append({"title": str(each['name'][:70]), "imageUrl": each['thumbnail_src'],
                                  "subTitle": "Book", "buttons": [{'text': "Add to cart", "value": str(each['name'])[:70]+";;;;"+str(each['sku'])}]})

        out['sessionAttributes']['findit'] = True
        out['sessionAttributes']['Lastsearchmethod'] = "name"
        out['sessionAttributes']['ShowingDisplay'] = "true"
        out['dialogAction']['responseCard'] = {
            "version": 2, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": list_of_books}

        print("This is out after cards\n", out)
        return out
############################################################################################################


def findthebooknameold(isbn):
    global gevent
    # buildtheconnection(gevent)
    try:
        out = searchbyany(isbn)
        print("searching by isbn")
        print(out)
        if out['price'] == None:
            out['price'] = "Not available"
        if "buy" in gevent['currentIntent']['slots']['start'].lower():
            output = ElicitSlot("This needs to be removed", "Buyornot")
        else:
            output = ElicitSlot("This needs to be removed", "Buyornot")
        if output['sessionAttributes'].get('Booksbought', None) == None:
            output['sessionAttributes']['Booksbought'] = " "

        output['sessionAttributes']['BookList'] = out['name']
        output['sessionAttributes']['cart'] = "no"
        output['sessionAttributes']['Buyornot'] = 'None'
        output['sessionAttributes']['qty'] = 'None'
        output['sessionAttributes']['lastslot'] = 'None'
        output['sessionAttributes']['repeat'] = "None"
        output['sessionAttributes']['findit'] = True
        if output['sessionAttributes'].get('CartId', None) == None:
            output['sessionAttributes']['CartId'] = "None"
        out2 = client.call(session, 'catalog_product_attribute_media.list', [
                           out["product_id"]])
        print(out2)
        output['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic",
                                                  "genericAttachments": [{"title": out['name'][:80], "subTitle":out['pp_authorblistbyline'].split(',')[0] + " Price $ " + out['price'],
                                                                          "buttons":[{'text': "Add to cart", "value": "yes"}]}]}

        if len(out2) > 0 and out2[0]['url'] != None:
            output['dialogAction']['responseCard']['genericAttachments'][0]['imageUrl'] = out2[0]['url']
        print(output)
        return output
    except Error as e:
        output = ElicitSlot(
            "Sorry, I didn't find any titles based on your input, wanna try again", "shopagain")
        output['sessionAttributes']['cart'] = "no"
        if output['sessionAttributes'].get('Booksbought', None) == None:
            output['sessionAttributes']['Booksbought'] = " "
        output['sessionAttributes']['Buyornot'] = 'None'
        output['sessionAttributes']['BookList'] = "None"
        output['sessionAttributes']['qty'] = 'None'
        if output['sessionAttributes'].get('lastslot', None) == None:
            output['sessionAttributes']['lastslot'] = 'None'
        output['sessionAttributes']['repeat'] = "None"
        output['sessionAttributes']['findit'] = False
        if output['sessionAttributes'].get('CartId', None) == None:
            output['sessionAttributes']['CartId'] = "None"
        return output
###############################################################################################################################


def gettheaddress(event):
    return ElicitSlot("At what location?", "Address")
#####################################################################################################################


def isit(value, check):
    return (len(difflib.get_close_matches(value.lower(), [check.lower()])) > 0)
###########################################################################################################


def closetheconnection():
    client.endSession(session)
#################################################################################################


def sendemail(email, msg, out):
    cclient = boto3.client('ses')
    global gevent
    content = "The order id is  " + str(out) + "\n\n"
    books = client.call(session, 'cart.info', [
                        gevent['sessionAttributes']['CartId']])['items']
    print(books)
    for each in books:
        content += str(each['name']) + ":" + str(each['qty'])+"\n"
    print(msg, content)
    det = ""
    print("cart for total", gevent['sessionAttributes']['CartId'], client.call(
        session, 'cart.totals', [gevent['sessionAttributes']['CartId']])[0]['amount'])
    det += "The total cart price is: " + str(client.call(session, 'cart.totals', [
                                             gevent['sessionAttributes']['CartId']])[0]['amount']) + " USD\n"

    det += "Shipping details:\n"
    det += "Name: " + str(get("firstname")) + " " + str(get("lastname")) + "\n"
    det += "Postal Address: " + \
        str(get("postaladdress")) + " " + str(get("postalcode")) + "\n"
    resp = cclient.send_email(Source="nitin.khaneja@compunnel.in", Destination={'BccAddresses': [], 'CcAddresses': [], 'ToAddresses': [email]},
                              Message={'Subject': {'Data': 'Order', 'Charset': 'utf-8'}, 'Body': {'Text': {'Data': msg + "\n" + content + "\n" + det, 'Charset': 'utf-8'}}})
######################################################################################


def create_cart():
    global gevent, session
    cartid = client.call(session, 'cart.create', ['22'])
    print("The cart created is ", cartid)
    return cartid
#########################################################################


def gettheskuof(bookname):
    skulist = client.call(session, 'catalog_product.list', [
                          {"type": "simple", "status": 1, "name": {"like": ("%"+bookname+"%")}}])
    i = 0
    while len(skulist) == 0:
        if i == 4:
            break
        else:
            skulist = client.call(session, 'catalog_product.list', [
                                  {"type": "simple", "status": 1, "name": {"like": ("%"+bookname+"%")}}])
            print(i, skulist)
            i += 1
    print("tried ", i, " times")
    print(skulist)
    if len(skulist) == 0:
        return denied("Sorry Couldn't connect to Server(Tried 4 times)")
    return (skulist[0]['sku']+" ")
#############################################################


def get(val):
    global gevent, session
    return gevent['currentIntent']['slots'][val]
################################################


def gets(val):
    global gevent
    return gevent['sessionAttributes'][val]
###########################################################################################################


def addtocart(cartid):
    global gevent
    print("adding to cart", cartid)
    book = gevent['currentIntent']['slots']['Book']
    if ";;;;" in get("Buyornot"):
        book = get("Buyornot").split(";;;;")[1]
    if not book:
        book = gevent['currentIntent']['slots']['choice']
    # buildtheconnection(gevent)

    if book:
        print("adding ", gevent['currentIntent']['slots']['Book'],
              gevent['currentIntent']['slots']['quantity'], " in ", cartid)
        out = client.call(session, 'cart_product.add', [
                          [cartid], [{'sku': book, "qty": 1}]])
        print(out)
    print(client.call(session, 'cart.info', [cartid]))
############################################################################################################


def validateinput(event):
    if event['sessionAttributes']['lastslottoelicit'] == "checkcart":
        slot = str(event['currentIntent']['slots']['checkcart']).lower()
        print(slot, ' <--')
        if len(slot.split(";;;;")) == 3 or slot == "checkout":
            return 1
        else:
            return show_cart(event['sessionAttributes']['CartId'], "I'm good with this!!")

    elif event['sessionAttributes']['lastslottoelicit'] == "shopagain" and event['sessionAttributes']['withoutsugg'] != "yes":
        slot = event['currentIntent']['slots']['shopagain']
        if event['sessionAttributes']['lastslot'] =="Index":
            buildtheconnection(event)
            out = findthebookname(event['currentIntent']['slots']['shopagain'])
            if out['sessionAttributes']['findit'] == True:
                return out
                
        elif str(slot).lower() not in ['shopagain', 'shop again', 'view cart', "checkout", "no", "yes", 'yo', 'yess', 'yes!!', "yup", 'yup!!', 'yaa', 'yaah', 'yaah!!', 'haan', 'ok', 'sure', 'noo', 'don\'t know', 'no!!', "nopes", 'nope!!', 'naa', 'naah', 'naah!!', 'nahi', 'skip']:
            out = ElicitSlot(
                "Sorry, didn't understand that.Do you want to shop more?", "shopagain")
            out['dialogAction']['responseCard'] = retshopagain()
            return out

    elif event['sessionAttributes']['lastslottoelicit'] == "choice":
        if isityes(event['currentIntent']['slots']['choice']) or isitno(event['currentIntent']['slots']['choice']):
            return 1
        buildtheconnection(event)
        out = findthebookname(event['currentIntent']['slots']['choice'])
        if out['sessionAttributes']['findit'] == True:
            return out

    elif gets("lastslottoelicit") == "email":
        if not get('email') or not isthismailfine(get("email")):
            return ElicitSlot("Your email id doesn't look fine. Please Enter again", "email")
    elif gets("lastslottoelicit") == "finalconfirmation":
        print("validating the finalconfirmation")
        if get('finalconfirmation') != None and (isityes(get('finalconfirmation')) or isitno(get('finalconfirmation'))):
            pass
        else:
            out = ElicitSlot(
                "That wasn't valid input. Shall I place the order?", "finalconfirmation")
            out['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": [{"title": "Book-title", "subTitle": "Book-sub-title", "buttons":
                                                                                                                                                  [{'text': "Yes", "value": "yes"}, {"text": "Cancel", "value": "cancel"}]}]}
            return out

    return 1
############################################################################################################


def finalize2(event):
    cartid = event['sessionAttributes']['CartId']
    print("hi", cartid, " is the current cartid")
    if cartid == "None" or cartid == None:
        if event['sessionAttributes']['BookList'] != " ":
            cartid = create_cart()
            event['sessionAttributes']['CartId'] = cartid
        else:
            return denied("Thanks for your time")
    if event['sessionAttributes']['BookList'] != " " and event['sessionAttributes']['BookList'] != "None":
        addtocart(cartid)
    if client.call(session, 'cart.info', [event['sessionAttributes']['CartId']])['items'] == []:
        return denied("Nothing in the cart. Thanks")
    print("Hiiting the cart to check the lsit of products")
    print(event['sessionAttributes']['repeat'])

    if event['sessionAttributes']['repeat'] == "None":
        output = show_cart(event['sessionAttributes']
                           ['CartId'], "I'm good with this")
        output['sessionAttributes']['repeat'] = 1
        return output

    if (event['currentIntent']['slots']['checkcart']) != str("checkout"):
        print("here checkcart not continue",
              (event['sessionAttributes']['repeat'] == 1), " fgfd")
        if event['sessionAttributes']['repeat'] == str(1):
            print("show options")
            removeproduct(event['currentIntent']['slots']['checkcart'], event)
            output = show_cart(event['sessionAttributes']
                               ['CartId'], "I'm good with this!!")
            return output

    else:
        output = ElicitSlot('Choose one', 'shopagain')
        output['dialogAction']['responseCard'] = retshopagain()
        output['sessionAttributes']['repeat'] = "None"
        output['sessionAttributes']['Lastsearchmethod'] = ""
        return output
############################################################################################################


def booklist(event):
    listofbooks = []
    ls = gevent['sessionAttributes']['Booksbought'].split(";;;;")[:-1]
    print(ls)
    for each in ls:
        listofbooks.append(
            [each.split("=>")[0], each.split("=>")[1], each.split("=>")[2]])
    return listofbooks
############################################################################################################


def show_cart(cartid, text="Back"):
    global gevent
    # buildtheconnection(gevent)
    print(client, session)
    if not session:
        buildtheconnection(gevent)
    output = ElicitSlot("This needs to be removed", "checkcart")
    print(cartid, " is being used here")
    cart = client.call(session, "cart.info", [cartid])
    listofbooks = []
    if len(cart['items']) == 0:
        out = ElicitSlot(
            "Cart is empty. Would you like to shop more?", "shopagain")
        out['dialogAction']['responseCard'] = retshopagain()
        out['sessionAttributes']['repeat'] = "None"
        return out
    i = 0
    for each in cart['items']:
        i += 1
        if i == 5:
            break
        listofbooks.append({"text": str(each['name'][:70])+"~"+str(each['qty']) + "::"+str(round(float(
            each['price']), 2)*int(each['qty'])), "value": str(each['sku']+";;;;"+each['name']+";;;;" + str(each['qty']))})
    listofbooks.append({"text": text, "value": "checkout"})
    output['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic",
                                              "genericAttachments": [{"title": "Books in cart", "subTitle": "Select the book to Edit", "buttons": listofbooks}]}

    return output
############################################################################################################

def showAddresses(event, customer_id, text="Back"):
    print("denied...........")
    print(session, client)
    msg = " "
    msg2 = "Hi Customer,\n Your order has been placed."
    cartid = event['sessionAttributes']['CartId']
    if cartid == "None" or cartid == None:
        buildtheconnection(event)
        cartid = create_cart()
    if event['sessionAttributes']['BookList'] != " " and event['sessionAttributes']['BookList'] != "None":
        buildtheconnection(event)
        addtocart(cartid)
    if event['sessionAttributes']['CartId'] == "None":
        return denied("Thanks for your time")
    print(session, client)
    if not session:
        buildtheconnection(event)
    if client.call(session, 'cart.info', [event['sessionAttributes']['CartId']])['items'] == []:
        return denied("Thanks for the time")
    # global gevent
    # # buildtheconnection(gevent)
    # print(client, session)
    # if not session:
    #     buildtheconnection(gevent)
    # cartid = gevent['sessionAttributes']['CartId']
    # print(cartid, " is being used here")
    # cart = client.call(session, "cart.info", [cartid])
    # listofbooks = []
    # if len(cart['items']) == 0:
    #     out = ElicitSlot(
    #         "Cart is empty. Would you like to shop more?", "shopagain")
    #     out['dialogAction']['responseCard'] = retshopagain()
    #     out['sessionAttributes']['repeat'] = "None"
    #     return out
    # else :
    i = 0
    addresses = client.call(session, 'customer_address.list', [{"id": customer_id}])
    list_of_books = []
    for each in addresses:
        i += 1
        if i == 5:
            break            
        # list_of_books.append({"title": str(each['firstname'][:70])+ str(each['lastname'][:70]), "imageUrl": '',"subTitle": str(each['street']) + "####!"+str(each['city'])+"####!"+str(each['region'])+"####!"+str(each['postcode'])+"####!"+str(each['telephone']), "buttons": [{'text': "Select", "value": str(each['customer_address_id'])}]})
        list_of_books.append({"title":"@@@@@" + str(each['firstname'][:70])+ " " + str(each['lastname'][:70]),"subTitle": str(each['street']) + " "+str(each['city'])+ " " +str(each['region'])+" "+" " +str(each['country_id'])+" "+str(each['postcode']), "buttons": [{"text": "Select Address", "value": str(each['customer_address_id'])+'address'}]})
    out = ElicitSlot("Select Your address", "Buyornot")                            
    out['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic","genericAttachments": list_of_books}
    out['sessionAttributes']['ShowingDisplay'] = "true"
    out['sessionAttributes']['repeat'] = "None"
    out['sessionAttributes']['Lastsearchmethod'] = ""

    return out



def createbutton(lst):
    button = list()
    for each in lst:
        button.append({"text": each[0], "value": each[1]})
    print(button)
    return button
############################################################################################################


def updateproduct(cart, event):
    client.call(session, 'cart_product.update', [
                [event['sessionAttributes']['CartId']], [{"sku": cart.split(";;;;")[0], "qty":1}]])
############################################################################################################

def getCustomerAddress(customer_id, event):
    return client.call(session, 'customer_address.list', [[event['sessionAttributes']['CartId']], [{"id": customer_id}]])
############################################################################################################


def removeproduct(cart, event):
    qty = int(cart.split(";;;;")[2])
    if qty == 1:
        return client.call(session, 'cart_product.remove', [[event['sessionAttributes']['CartId']], [{"sku": cart.split(";;;;")[0], "qty":1}]])
    else:
        return client.call(session, 'cart_product.update', [[event['sessionAttributes']['CartId']], [{"sku": cart.split(";;;;")[0], "qty":qty-1}]])
############################################################################################################


def seecart(event):
    cartid = event['sessionAttributes']['CartId']
    print("hi", cartid, " is the current cartid")
    if cartid == "None" or cartid == None:
        cartid = create_cart()
    if event['sessionAttributes']['BookList'] != " " and event['sessionAttributes']['BookList'] != "None":
        addtocart(cartid)
    print("Hiiting the cart to check the lsit of products")
    print(event['sessionAttributes']['repeat'])
    if str(event['sessionAttributes']['repeat']) == str("update the product"):
        updateproduct(event['currentIntent']['slots']['checkcart'], event)
        event['sessionAttributes']['repeat'] = "None"

    if event['sessionAttributes']['repeat'] == "None":
        output = show_cart(event['sessionAttributes']['CartId'])
        if output['dialogAction']['slotToElicit'] == "shopagain":
            output['sessionAttributes']['repeat'] = "None"
        output['sessionAttributes']['repeat'] = 1
        return output

    if (event['currentIntent']['slots']['checkcart']) != str("checkout"):
        print("here checkcart not continue",
              (event['sessionAttributes']['repeat'] == 1), " fgfd")
        if event['sessionAttributes']['repeat'] == str(1):
            print("show options")
            output = ElicitSlot("You have requested to change " + str(
                event['currentIntent']['slots']['checkcart'].split(";;;;")[1]), 'redefine')
            output['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic",
                                                      "genericAttachments": [{"title": "Book-title", "subTitle": "Book-sub-title",
                                                                              "buttons": createbutton([['Remove this from cart', '1'], ['Continue', 3]])}]}
            output['sessionAttributes']['repeat'] = 2
            return output

        if event['currentIntent']['slots']['redefine'] == str(1):
            removeproduct(event['currentIntent']['slots']['checkcart'], event)
        output = show_cart(event['sessionAttributes']['CartId'])
        output['sessionAttributes']['repeat'] = "None"
        return output
    else:
        print("here that was fine")

    if event['currentIntent']['slots']['firstname'] == None:
        return ElicitSlot("Please enter you First Name", "firstname")
    elif event['currentIntent']['slots']['lastname'] == None:
        return ElicitSlot("Please provide your Last Name", "lastname")
    elif event['currentIntent']['slots']['postaladdress'] == None:
        return ElicitSlot("Please provide your Postal Address", "postaladdress")
    elif event['currentIntent']['slots']['postalcode'] == None:
        return ElicitSlot("Please provide your Postal Code", "postalcode")

    if event['currentIntent']['slots']['email'] == None and gets("email") == " ":
        return ElicitSlot("Enter your email", "email")
    print(event['sessionAttributes']['CartId'], (event['sessionAttributes']
                                                 ['CartId'] == "None"), (event['sessionAttributes']['CartId'] == None))
    print("cartid  is ", gevent['sessionAttributes']['CartId'])
    return list()
############################################################################################################


def isthismailfine(email):
    return (re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email) != None)
############################################################################################################


def erroneous(err):
    if "email address" in str(err.faultString):
        return ElicitSlot("The entered e-mail couln't be added. Please enter the correct one", "email")
    return denied("Please try after some time")
############################################################################################################


def finalize(event, customerId):
    print("denied...........")
    print(session, client)
    msg = " "
    msg2 = "Hi Customer,\n Your order has been placed."
    cartid = event['sessionAttributes']['CartId']
    if cartid == "None" or cartid == None:
        buildtheconnection(event)
        cartid = create_cart()
    if event['sessionAttributes']['BookList'] != " " and event['sessionAttributes']['BookList'] != "None":
        buildtheconnection(event)
        addtocart(cartid)
    if event['sessionAttributes']['CartId'] == "None":
        return denied("Thanks for your time")
    print(session, client)
    if not session:
        buildtheconnection(event)
    if client.call(session, 'cart.info', [event['sessionAttributes']['CartId']])['items'] == []:
        return denied("Thanks for the time")
    #out = seecart(event)
    # if out != []:
        # return out
        
    if event['currentIntent']['slots']['firstname'] == None:
        return ElicitSlot("Please enter you First Name?", "firstname")
    elif event['currentIntent']['slots']['lastname'] == None:
        return ElicitSlot("Please provide your Last Name", "lastname")
    elif event['currentIntent']['slots']['postaladdress'] == None:
        return ElicitSlot("Please provide your Postal Address", "postaladdress")
    elif event['currentIntent']['slots']['postalcode'] == None:
        return ElicitSlot("Please provide your Postal Code", "postalcode")

    if event['currentIntent']['slots']['email'] == None or not isthismailfine(get("email")):
        return ElicitSlot("Please provide your email address", "email")
    print(event['sessionAttributes']['CartId'], (event['sessionAttributes']
                                                 ['CartId'] == "None"), (event['sessionAttributes']['CartId'] == None))
    print("cartid  is ", gevent['sessionAttributes']['CartId'])

    if not event['currentIntent']['slots']['finalconfirmation']:
        try:

            out = client.multiCall(session, [['cart_customer.set', [[gevent['sessionAttributes']['CartId']], {"firstname": get("firstname"), "lastname": get("lastname"), "group_id": "1", "store_id": "22",
                                                                                                              "email": get("email"), "mode": "guest"}]], ['cart_customer.addresses', [[gevent['sessionAttributes']['CartId']],
                                                                                                                                                                                      [{"mode": "shipping", "firstname": get("firstname"), "lastname": get("lastname"), "street": get("postaladdress"), "postcode": get("postalcode"),
                                                                                                                                                                                        "country_id": "IN", "is_default_shipping": "0", "city": "Noida", "is_default_billing": "0", "telephone": "0123456789", "fax": "0123456789", "region_id": "950"},
                                                                                                                                                                                       {"mode": "billing", "firstname": get("firstname"), "lastname": get("lastname"), "street": get("postaladdress"), "postcode": get("postalcode"),
                                                                                                                                                                                        "country_id": "IN", "is_default_shipping": "0", "city": "Noida", "is_default_billing": "0", "telephone": "123456789", "fax": "0123456789", "region_id": "950"}]]],
                                             ['cart_payment.method', [[gevent['sessionAttributes']['CartId']], {"method": "cashondelivery"}]], ['cart_shipping.method', [[gevent['sessionAttributes']['CartId']], 'freeshipping_freeshipping']]])
        except Error as e:
            print(e)
            print(dir(e))
            print(e.faultCode, " :::", e.faultString, ";;; ", e.message)
            # return denied("Sorry, couldn't add your details" )
            return erroneous(e)
        print("cart for total", gevent['sessionAttributes']['CartId'], client.call(
            session, 'cart.totals', [gevent['sessionAttributes']['CartId']])[0]['amount'])
        ms = "OK. The total amount of your Cart is $" + str(client.call(session, 'cart.totals', [
                                                            gevent['sessionAttributes']['CartId']])[0]['amount']) + ". Shall I place the order."
        out = ElicitSlot(ms, "finalconfirmation")
        out['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": [{"title": "Book-title", "subTitle": "Book-sub-title", "buttons":
                                                                                                                                              [{'text': "Yes", "value": "yes"}, {"text": "Cancel", "value": "cancel"}]}]}
        return out
    if isityes(event['currentIntent']['slots']['finalconfirmation']) and not isitno(event['currentIntent']['slots']['finalconfirmation']):
        out = " "
        flag = False
        try:
            print("email should be ", get("email"))
            out = client.call(session, 'cart.order', [
                              gevent['sessionAttributes']['CartId']])
            msg = "Your order has been sucessfully placed. The order id is " + \
                str(out) + " and the details have been emailed to you at " + \
                str(get("email"))
        except Error as e:
            print(e)
            flag = True
            return denied("Sorry, couldn't place the order right now. Try again later or you can contact to our customer service here 1800 263 951 (Toll free within Australia) \
0800 170 165 (Toll free to Australia from New Zealand)")

        # try:
        #     print("tyring mail send")
        #     sendemail(event['currentIntent']['slots']['email'], msg2, out)
        # except ClientError as e:
        #     msg = ("There was an error while message sending")
        #     return denied(msg)
        print(msg)
        return confirmed(msg)
    else:
        return denied("Thanks for your time!!")
############################################################################################################

def finalizeCheckout(event, customerId, address_id):
    print("denied...........")
    print(session, client)
    msg = " "
    msg2 = "Hi Customer,\n Your order has been placed."
    cartid = event['sessionAttributes']['CartId']
    if cartid == "None" or cartid == None:
        buildtheconnection(event)
        cartid = create_cart()
    if event['sessionAttributes']['BookList'] != " " and event['sessionAttributes']['BookList'] != "None":
        buildtheconnection(event)
        addtocart(cartid)
    if event['sessionAttributes']['CartId'] == "None":
        return denied("Thanks for your time")
    print(session, client)
    if not session:
        buildtheconnection(event)
    if client.call(session, 'cart.info', [event['sessionAttributes']['CartId']])['items'] == []:
        return denied("Thanks for the time")
        
    print(event['sessionAttributes']['CartId'], (event['sessionAttributes']
                                                 ['CartId'] == "None"), (event['sessionAttributes']['CartId'] == None))
    print("cartid  is ", gevent['sessionAttributes']['CartId'])

    if not event['currentIntent']['slots']['finalconfirmation']:
        try:

            out = client.multiCall(session, [['cart_customer.set', [[gevent['sessionAttributes']['CartId']], {"entity_id": customerId, "mode": "customer"}]], ['cart_customer.addresses', [[gevent['sessionAttributes']['CartId']],
                                                                                                                                                                                      [{"mode": "shipping", "address_id" : str(address_id)},
                                                                                                                                                                                       {"mode": "billing", "address_id" : str(address_id)}]]],
                                             ['cart_payment.method', [[gevent['sessionAttributes']['CartId']], {"method": "cashondelivery"}]], ['cart_shipping.method', [[gevent['sessionAttributes']['CartId']], 'freeshipping_freeshipping']]])
        except Error as e:
            print(e)
            print(dir(e))
            print(e.faultCode, " :::", e.faultString, ";;; ", e.message)
            # return denied("Sorry, couldn't add your details" )
            return erroneous(e)
        print("cart for total", gevent['sessionAttributes']['CartId'], client.call(
            session, 'cart.totals', [gevent['sessionAttributes']['CartId']])[0]['amount'])
        ms = "OK. The total amount of your Cart is $" + str(client.call(session, 'cart.totals', [
                                                            gevent['sessionAttributes']['CartId']])[0]['amount']) + ". Shall I place the order."
        out = ElicitSlot(ms, "finalconfirmation")
        out['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": [{"title": "Book-title", "subTitle": "Book-sub-title", "buttons":
                                                                                                                                              [{'text': "Yes", "value": "yes"}, {"text": "Cancel", "value": "cancel"}]}]}
        return out
    if isityes(event['currentIntent']['slots']['finalconfirmation']) and not isitno(event['currentIntent']['slots']['finalconfirmation']):
        out = " "
        flag = False
        try:
            print("email should be ", get("email"))
            out = client.call(session, 'cart.order', [
                              gevent['sessionAttributes']['CartId']])
            msg = "Your order has been sucessfully placed. The order id is " + \
                str(out) + " and the details have been emailed to you at " + \
                str(get("email"))
        except Error as e:
            print(e)
            flag = True
            return denied("Sorry, couldn't place the order right now. tru again later")

        # try:
        #     print("tyring mail send")
        #     sendemail(event['currentIntent']['slots']['email'], msg2, out)
        # except ClientError as e:
        #     msg = ("There was an error while message sending")
        #     return denied(msg)
        print(msg)
        return confirmed(msg)
    else:
        return denied("Thanks for your time!!")
############################################################################################################


def retshopagain():
    print(gevent, session, client)
    if gevent['sessionAttributes']['CartId'] == "None" or client.call(session, 'cart.info', [gevent['sessionAttributes']['CartId']])['items'] == []:
        return {"version": 1, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": [{"title": "Book-title", "subTitle": "Book-sub-title", "buttons":
                                                                                                               [{'text': "Shop again", "value": "Shopagain"}, {'text': "No", "value": "No"}]}]}
    return {"version": 1, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": [{"title": "Book-title", "subTitle": "Book-sub-title", "buttons":
                                                                                                           [{'text': "Shop again", "value": "Shopagain"}, {"text": "Checkout", "value": "checkout"}, {"text": "View Cart", "value": "view Cart"}]}]}
############################################################################################################


def isityes(inp):
    yes = ['yes', 'yo', 'yess', 'yes!!', "yup", 'yup!!',
           'yaa', 'yaah', 'yaah!!', 'ok', 'sure', 'okk']
    inp = inp.lower()
    if difflib.get_close_matches(inp, yes) != []:
        return 1
    for each in yes:
        if inp in each or each in inp:
            return 1
    return 0
############################################################################################################


def isitbought(inp):
    yes = ['add to cart', 'yes', 'add it to cart', ";;;;", 'add it to the cart', 'add the book to cart',
           'add this book to cart', 'add this book to the cart', 'Ok add it', 'Ok i will buy this']
    inp = inp.lower()
    if difflib.get_close_matches(inp, yes) != []:
        return 1
    for each in yes:
        if inp in each or each in inp:
            return 1
    return 0
############################################################################################################


def getcustomer_id(email):
    buildtheconnection(gevent)
    res = client.call(session, 'customer.list', [{"email": email}])
    if len(res):
        return res[0].get('customer_id'), res[0].get('firstname', 'Guest')
    return None, 'Guest'
############################################################################################################


def getpredictedres(customer_id=None):
    res = False
    try:
        if customer_id != None:
            res = client.call(session, 'prediction_suggestion.list', [{"qty": "10", "customer_id": customer_id}, 22, [
                              "contractorigin", "cover", "pp_authorblistbyline", "discounted_price"]])
            res = res[:min(len(res), 5)]
        else:
            res = client.call(session, 'prediction_suggestion.list', [{"qty": "10"}, 22, [
                              "contractorigin", "cover", "pp_authorblistbyline", "discounted_price"]])
            res = res[:min(len(res), 5)]
        print(res)
    except Error as e:
        print(e)
    return res
############################################################################################################


def lambda_handler(event, context):
            # TODO implementcr
    print('here')
    customer_id = ''
    if event['sessionAttributes'] == {} or event['sessionAttributes'] == None:
        event['sessionAttributes'] = {'CartId': "None", 'BookList': " ", 'lastslottoelicit': " ", 'Booksbought': " ", 'cart': "no", "Lastsearchmethod": "",
                                      'customer_id': "", 'Buyornot': 'None', 'qty': 'None', 'lastslot': "None", 'repeat': "None", 'findit': False, "withoutsugg": "", "ShowingDisplay": "false", "email": ""}
    global gevent
    gevent = event
    print(event)
    if event['sessionAttributes'].get("lastslottoelicit", None) != None and len(gets('lastslottoelicit')):
        resp = validateinput(event)
        print("after vaildating output we have recieved this\n", resp)
        if resp != 1:
            return resp
    print(gevent)
    if (gets('lastslottoelicit') == " " or gets("withoutsugg") == ""):
        if difflib.get_close_matches(str(get("buyorask")).lower(), ['shop now', 'want to shop now', 'shoping now', 'let me shop now', 'lemme shop now', 'I\'ll shop for now']):

            if get('haveaccount') == None:
                out = ElicitSlot(
                    "Do you have an account with us?", "haveaccount")
                return out
            elif isityes(get('haveaccount')) or isthismailfine(get("haveaccount")):
                email = " "
                if isthismailfine(get('haveaccount')):
                    email = get("haveaccount")  # if its an email
                elif get("email") == None and 0 == len(gets("email")) and isityes(get("haveaccount")):
                    # if its
                    return ElicitSlot("Please enter your email id.", "email")
                # print get("email"),len(gets("email")), isityes(get("haveaccount"))
                if email == " ":
                    email = gevent['sessionAttributes']['email'] = get("email")
                customer_id, name = getcustomer_id(email)
                if get('Buyornot') == None:
                    out = ElicitSlot(
                        "Welcome "+str(name)+", we have some recommendations for you. Do you want to see them?", "Buyornot")
                    return out
                elif isityes(get('Buyornot')):
                    print("wants suggestions")
                    if customer_id:
                        res = getpredictedres(customer_id)
                        if len(res):
                            out = ElicitSlot(
                                "Following are our recommendations", "Buyornot")
                            out['sessionAttributes']['withoutsugg'] = "listshown"
                            #list_of_buttons = [{'text':"Add to cart","value":"yes"},{"text":"No","value":"no"}]
                            list_of_books = []
                            for each in res:
                                img = 'https://cert1-www.apac.elsevierhealth.com/media/catalog/product/9/7/9780323525886.jpg'
                                out2 = client.call(session, 'catalog_product_attribute_media.list', [
                                                   each['product_id']])
                                # and len(out2[0]['url']) < 80:
                                if len(out2) > 0 and out2[0]['url'] != None:
                                    img = out2[0]['url']
                                discounted_price = " "
                                if str(each['final_price']).lower() != "false" and len(str(each['final_price'])) != 0:
                                    discounted_price = "####@ $" + \
                                        str(round(
                                            float(each['final_price']), 2))
                                list_of_books.append({"title": str(each['name'][:70]), "imageUrl": img,
                                                      "subTitle": str(each['pp_authorblistbyline']).split(",")[0] + "####!"+str(round(float(each['price']), 2))+discounted_price, "buttons": [{'text': "Add to cart", "value": str(each['name'])[:70]+";;;;"+str(each['sku'])}]})
                            out['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic",
                                                                   "genericAttachments": list_of_books}
                        else:
                            out = ElicitSlot(
                                rep+" We are to show you best sellers here. For now choose one.", "shopagain")
                            out['sessionAttributes']['withoutsugg'] = "topsellers"
                            out['dialogAction']['responseCard'] = retshopagain()
                        out['sessionAttributes']['customer_id'] = customer_id
                        out['sessionAttributes']['ShowingDisplay'] = "true"
                        print(out)
                        return out
                    else:
                        res = getpredictedres(customer_id)
                        if len(res):
                            out = ElicitSlot(
                                "Following are our recommendations", "Buyornot")
                            out['sessionAttributes']['withoutsugg'] = "listshown"
                            #list_of_buttons = [{'text':"Add to cart","value":"yes"},{"text":"No","value":"no"}]
                            list_of_books = []
                            for each in res:
                                img = 'https://cert1-www.apac.elsevierhealth.com/media/catalog/product/9/7/9780323525886.jpg'
                                out2 = client.call(session, 'catalog_product_attribute_media.list', [
                                                   each['product_id']])
                                # and len(out2[0]['url']) < 80:
                                if len(out2) > 0 and out2[0]['url'] != None:
                                    img = out2[0]['url']
                                discounted_price = " "
                                if str(each['final_price']).lower() != "false" and len(str(each['final_price'])) != 0:
                                    discounted_price = "####@ $" + \
                                        str(round(
                                            float(each['final_price']), 2))
                                list_of_books.append({"title": str(each['name'][:70]), "imageUrl": img,
                                                      "subTitle": str(each['pp_authorblistbyline']).split(",")[0]+"####! $"+str(round(float(each['price']), 2))+discounted_price, "buttons": [{'text': "Add to cart", "value": str(each['name'])[:70]+";;;;"+str(each['sku'])}]})
                                # list_of_books.append({"text":str(each['name'][:70])+"::"+str(each['price']),"value":str('Master Medicine: General and Systematic Pathology'+';;;;'+'9780080451299')})
                            # list_of_books.append({"text":"Skip These","value":"skip these"})
                            out['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic",
                                                                   "genericAttachments": list_of_books}
                            out['sessionAttributes']['ShowingDisplay'] = "true"
                            return out
                else:
                    out = ElicitSlot(
                        "Would you like to make a search?", "shopagain")
                    out['sessionAttributes']['withoutsugg'] = "yes"
                    return out
            elif isitno(get("haveaccount")):
                out = ElicitSlot(
                    "Would you like to make a search?", "shopagain")
                out['sessionAttributes']['withoutsugg'] = "yes"
                return out
            else:
                print(isityes(get('haveaccount')),
                      isthismailfine(get("haveaccount")))
                out = ElicitSlot(
                    "Sorry,I could'nt understand. Please share your email id or shall we continue without it.", "haveaccount")
                out['sessionAttributes']['lastslottoelicit'] = " "
                return out
        elif str(get('buyorask')) == "FAQ":
            out = ElicitSlot("FAQ is not available as of now.", "buyorask")
            out['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": [{"title": "Menu", "subTitle": "Options", "buttons":
                                                                                                                                                  [{'text': "Shop now", "value": "shop now"}, {'text': "FAQ", "value": "FAQ"}]}]}
            return out

    ############################################################################
    #print(get("shopagain").lower())
    if gets("withoutsugg") == "listshown":
        if difflib.get_close_matches(str(get("Buyornot")).lower(), ['skip these please', 'skip the above', 'no', 'skip', 'continue']):
            out = ElicitSlot("Want to shop again.", "shopagain")
            out['dialogAction']['responseCard'] = retshopagain()
            out['sessionAttributes']['withoutsugg'] = "rejected"
            return out
        elif len(str(get("Buyornot")).lower().split(";;;;")) != 2:
            out = ElicitSlot(
                "That wasn't a valid input. Please choose from above list or Skip.", "Buyornot")
            out['sessionAttributes']['BookList'] = " "
            return out
        else:
            buildtheconnection(event)
            output = ElicitSlot(str(get('Buyornot').split(";;;;")[
                                0])+" has been added to your cart\n. Add more to cart from above list or click Continue", "Buyornot")
            if event['sessionAttributes']['CartId'] == "None" or event['sessionAttributes']['CartId'] == None:
                output['sessionAttributes']['CartId'] = create_cart()
            addtocart(output['sessionAttributes']['CartId'])
            output['sessionAttributes']['BookList'] = " "
            output['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": [{"title": "Book-title", "subTitle": "Book-sub-title", "buttons":
                                                                                                                                                     [{'text': "Continue", "value": "Continue"}]}]}
            print(output)
            return output
    if gets("withoutsugg") == "yes":
        # checking if he has enterd the title instead of saying yes or no
        if isityes(get('shopagain')) or isitno(get('shopagain')):
            pass
        else:
            event['sessionAttributes']['withoutsugg'] = "check input"

    if event['currentIntent']['slots']['shopagain'] == None and gets("withoutsugg") != "check input":
        if event['currentIntent']['slots']['choice'] == None:
            # if isthismailfine(get("start")):
            if "search" in str(event['currentIntent']['slots']['start']).lower():
                return ElicitSlot("Ok. Do you know the ISBN of the book you want to search", "choice")
            elif "buy" in str(event['currentIntent']['slots']['start']).lower():
                return ElicitSlot("So, Do you know the ISBN of the book you want to buy", "choice")
            else:
                return ElicitSlot("Sorry, we couldn't understand that. You want to search or buy", "start")
        elif isityes(event['currentIntent']['slots']['choice']) or str(event['sessionAttributes']['findit']).lower() == "true":
            if event['currentIntent']['slots']['Buyornot'] == None:
                if event['currentIntent']['slots']['Book'] == None:
                    return ElicitSlot("Please give me the ISBN", "Book")
                else:
                    buildtheconnection(event)
                    output = findthebookname(
                        event['currentIntent']['slots']['Book'])
                    return output
            else:
                print(event['currentIntent']['slots']['Buyornot'])
                # if event['sessionAttributes']['Lastsearchmethod'] == "name":
                #x = "book name"

                if isitbought(event['currentIntent']['slots']['Buyornot']):
                    # if get("quantity") == None:
                        # return ElicitSlot("How many units ?", "quantity")
                    buildtheconnection(event)
                    output = ElicitSlot(
                        "We have added the product to you cart.", "Buyornot")
                    if event['sessionAttributes']['CartId'] == "None" or event['sessionAttributes']['CartId'] == None:
                        output['sessionAttributes']['CartId'] = create_cart()
                    addtocart(output['sessionAttributes']['CartId'])
                    output['sessionAttributes']['BookList'] = " "
                    #output['dialogAction']['responseCard'] = retshopagain()
                    output['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": [{"title": "Book-title", "subTitle": "Book-sub-title", "buttons":
                                                                                                                                                             [{'text': "Continue", "value": "Continue"}]}]}
                    print(output)
                    return output
                else:
                    print(gets("Booksbought") ==
                          " "), (gets("Booksbought") == None)
                    msg = " "
                    if gets("BookList") == " " or gets("BookList") == None:
                        msg = "Hey there is nothing in the cart. "

                    output = ElicitSlot(
                        msg+"Do you like to shopagain ? ", "shopagain")
                    output['sessionAttributes']['BookList'] = " "
                    output['dialogAction']['responseCard'] = retshopagain()
                    return output
        else:
            out = ElicitSlot("ISBN is needed. Wanna try again", "shopagain")
            out['dialogAction']['responseCard'] = retshopagain()
            # out['sessionAttributes'] = {} # Not sure why this was added. But that must be reasonable.
            out['sessionAttributes']['customer_id'] = getcustomer_id(
                get('email'))
            return out
    elif get("shopagain").lower() == "checkout" or isitno(get("shopagain")):
        print(gets("Booksbought") != " "), (gets("Booksbought") != None)
        if event['sessionAttributes']['CartId'] != "None":
            # buildtheconnection(event)
            email = event['sessionAttributes']['email'] = get("email")
            if email:
                customer_id, name = getcustomer_id(email) 
            if customer_id and get("Buyornot").find('address') == -1:
                
                return showAddresses(event, customer_id)
            elif customer_id and get("Buyornot").find('address') != -1:
                customerAddressId = get("Buyornot").replace('address','')
                print(customerAddressId+'testttttt')
                return finalizeCheckout(event,customer_id,customerAddressId)
            else:
                return finalize(event,customer_id)
            # return finalize(event,customer_id)    
        else:
            return denied("Thanks for your time")
    elif get("shopagain").lower() == "view cart" or get("shopagain").lower() == "no":
        buildtheconnection(event)
        out = finalize2(event)
        return out
    elif get("shopagain").find('address') != -1:
        return ElicitSlot("Please enter you Heyyyy Name?", "firstname")
    else:
        if gets("withoutsugg") == "check input":
            print("here changing the withoutsugg", gets("withoutsugg"))
            gevent['sessionAttributes']['lastslot'] = "Index"
            gevent['sessionAttributes']['withoutsugg'] = "searched"
            book = get("shopagain")
        else:
            book = event['currentIntent']['slots']['Book']
        print("wanted to Shopagain", event)
        slotsequence = {'None': 'Index', 'Index': 'Buyornot',
                        'Buyornot': 'qty', 'qty': 'confirmation'}
        curr = event['sessionAttributes']['lastslot']
        print(curr, event['sessionAttributes']['lastslot'])
        if curr == 'None':
            print("taking confirmation here")
            output = ElicitSlot(
                'Okay! That\'s great Let me know your search keyword', "shopagain")
            output['sessionAttributes']['lastslot'] = slotsequence[curr]
            print(output)
            return output
        elif curr == 'Index':
            buildtheconnection(event)
            book = get("shopagain")
            print("Before search", event)
            print("searching for ", str(book))
            output = findthebookname(str(book))
            print("after search", event,
                  slotsequence[curr], (event['sessionAttributes']['findit'] == True))
            if event['sessionAttributes']['findit']:
                output['sessionAttributes']['lastslot'] = slotsequence[curr]
            else:
                output['sessionAttributes']['lastslot'] = 'None'
            print(output)
            return output
        elif curr == 'Buyornot':
            print("recieved the confirmation")
            if isitbought(event['currentIntent']['slots']['Buyornot']):
                output = ElicitSlot(
                    "That was added to your cart.Choose more from above list or Continue", 'Buyornot')
                print(event['sessionAttributes']['BookList'])
                output['sessionAttributes']['Buyornot'] = 'None'
                output['sessionAttributes']['qty'] = 'None'
                #output['sessionAttributes']['lastslot'] = 'None'
                buildtheconnection(event)
                if event['sessionAttributes']['CartId'] == "None" or event['sessionAttributes']['CartId'] == None:
                    output['sessionAttributes']['CartId'] = create_cart()
                addtocart(output['sessionAttributes']['CartId'])
                #output['dialogAction']['responseCard'] = retshopagain()
                output['dialogAction']['responseCard'] = {"version": 1, "contentType": "application/vnd.amazonaws.card.generic", "genericAttachments": [{"title": "Book-title", "subTitle": "Book-sub-title", "buttons":
                                                                                                                                                         [{'text': "Continue", "value": "Continue"}]}]}
                output['sessionAttributes']['BookList'] = " "
                return output
            else:
                print("he contniued after deleting last product")
                output = ElicitSlot("Do you want shop more?", 'shopagain')
                output['dialogAction']['responseCard'] = retshopagain()
                output['sessionAttributes']['Buyornot'] = 'None'
                output['sessionAttributes']['qty'] = 'None'
                output['sessionAttributes']['lastslot'] = 'None'
                output['sessionAttributes']['BookList'] = " "
                print(output)
                return output

    closetheconnection()
    return 'no one would/should ever reach here but only error!!'
