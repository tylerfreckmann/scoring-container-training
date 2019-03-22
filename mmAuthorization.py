#Very simple authorization model. Will need to be updated along with main python code when ready for use

'''
Created on Jan 15, 2016

@author: wenbao
commented out CAS related stuff
'''
import requests
import json
#from swat import *

AUTHORIZATION_TOKEN = "Bearer "
AUTHORIZATION_HEADER = "Authorization"

class mmAuthorization(object):
    
    AUTHORIZATION_TOKEN = "Bearer "
    AUTHORIZATION_HEADER = "Authorization"
    
    uriAuth='/SASLogon/oauth/token'


    def __init__(self, params):
        '''
        Constructor
        '''
        
    def getAuthToken(self, url, user='viyademo01', password='lnxsas'):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            self.AUTHORIZATION_HEADER: 'Basic c2FzLmVjOg=='
            }
        payload = 'grant_type=password&username=' + user + '&password=' + password
        authReturn = requests.post(url+self.uriAuth, data=payload, headers=headers)

        mAuthJson = json.loads(authReturn.content.decode('utf-8'))
        mytoken = mAuthJson['access_token']
        return mytoken
    
    def sasLogout(self, url):
        headers = {}
        
        logoutReturn = requests.get(url+'/SASLogon/logout', headers=headers)
        #myReturn = json.loads(logoutReturn.content)
        
        return logoutReturn

    
