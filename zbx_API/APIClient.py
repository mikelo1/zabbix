import requests
import json
import sys
#from requests_toolbelt.utils import dump


class ZabbixAPIClient(requests.Session):
    basicAuth   = dict()
    appD_Config = None
    authToken   = ""
    API_URL     = ""

    target = {

        'Problems':         {'fetch':    {
                                "jsonrpc": "2.0",
                                "method": "problem.get",
                                "params": {
                                    "output": "extend", 
                                    "selectAcknowledges": "extend", 
                                    "recent": "true", 
                                    "sortfield": ["eventid"],
                                    "sortorder": "DESC"
                                },
                                "id": 2,
                                "auth": "{AUTHTOKEN}"
                              }
                            },

        'Triggers':         {'fetch':    {
                                "jsonrpc": "2.0",
                                "method": "trigger.get",
                                "params": {
                                    "output": ["triggerid","description","expression","priority","comments"],
                                    "expandExpression": 1,
                                    "selectHosts": 1,
                                    "sortfield": "priority",
                                    "sortorder": "DESC"
                                },
                                "id": 2,
                                "auth": "{AUTHTOKEN}"
                              },
                             'fetchWithProblem':    {
                                "jsonrpc": "2.0",
                                "method": "trigger.get",
                                "params": {
                                    "output": ["triggerid","description","expression","priority","comments"],
                                    "filter": {"value": 1},
                                    "expandExpression": 1,
                                    "selectHosts": 1,
                                    "sortfield": "priority",
                                    "sortorder": "DESC"
                                },
                                "id": 2,
                                "auth": "{AUTHTOKEN}"
                              },
                             'fetchWithError':    {
                                "jsonrpc": "2.0",
                                "method": "trigger.get",
                                "params": {
                                    "output": ["triggerid","description","expression","error"],
                                    "filter": {"state": 1},
                                    "expandExpression": 1,
                                    "selectHosts": 1,
                                    "sortfield": "priority",
                                    "sortorder": "DESC"
                                },
                                "id": 2,
                                "auth": "{AUTHTOKEN}"
                              },

                            },

        'Hosts':            {'fetch': {
                                "jsonrpc": "2.0",
                                "method": "host.get",
                                "params": {
                                #     "output": ["name","proxy_hostid"],
                                },
                                "id": 1,
                                "auth": "{AUTHTOKEN}"
                              },
                             'fetchNamesByIDs': {
                                "jsonrpc": "2.0",
                                "method": "host.get",
                                "params": {
                                     "output": ["name","hostid"],
                                     "hostids": ["{HOST_IDS}"]
                                },
                                "id": 1,
                                "auth": "{AUTHTOKEN}"
                              },
                             'fetchNamesList': {
                                "jsonrpc": "2.0",
                                "method": "host.get",
                                "params": {
                                     "output": ["name","hostid"],
                                },
                                "id": 1,
                                "auth": "{AUTHTOKEN}"
                              }                              
                            },

        'Hostinterfaces':   {'fetch': {
                                "jsonrpc": "2.0",
                                "method": "hostinterface.get",
                                "params": {
                                     "output": ["interfaceid","hostid","ip","port"],
                                },
                                "id": 1,
                                "auth": "{AUTHTOKEN}"
                              }
                            }
    }


    def __init__(self, serverURL=None, API_username=None, API_password=None, *args, **kwargs):
        super(ZabbixAPIClient, self).__init__(*args, **kwargs)
        self.API_URL = serverURL
        if serverURL and API_username and API_password:
            self.user_login(serverURL=serverURL,API_username=API_username,API_password=API_password)
        
    ### TO DO: Implement sessions
#    def _get_session(self):    
#        if not self._session:
#            from requests.sessions import Session
#            self._session = Session()
#            self._session.verify = self.verify
#        return self._session

    def request(self, entityClassName, verb, *args, **kwargs):
        """
        Send a request to a Zabbix server.
        :param entityClassName: Type of entity to be sent a request
        :param verb: Method to use in the request
        :returns: the request response data. Null if no data was received.
        """
        #url        = urljoin(self.prefix_url, url)
        method     = "post"
        req_json   = self.target[entityClassName]['fetch']
        req_json.update( {"auth": self.authToken} )
        try:
            response = super(ZabbixAPIClient, self).request(method, self.API_URL, json=req_json, *args, **kwargs)
        except requests.exceptions.InvalidURL:
            sys.stderr.write("Invalid URL: " + url + ". Do you have the right hostname?\n")
            return None

        if response.status_code > 399:
            sys.stderr.write("[Warn] Something went wrong on HTTP request. Status:" + str(response.status_code) + "\n")
            content = str(response.content)
            message_start = content.find('<b>message</b>')
            if message_start >= 0:
                message_end = content.find("</p>",message_start)
                sys.stderr.write("Message: "+content[message_start+14:message_end] + "\n" )
            description_start = content.find('<b>description</b>')
            if description_start >= 0:
                description_end = content.find("</p>",description_start)
                sys.stderr.write("Description: "+content[description_start+18:description_end] + "\n" )
            elif message_start < 0 and description_start < 0:
                sys.stderr.write(content)
            return None
            if 'DEBUG' in locals(): sys.stderr.write("\nurl: "+str(url)+"\nauth: "+str(auth)+"\nparams: "+str(params)+"\nheaders: "+str(headers)+"\ndata: "+str(data)+"\nfiles:"+str(files)+"\n")
        elif 'DEBUG' in locals():
            sys.stderr.write("HTTP request successful with status:" + str(response.status_code) + " ")

        return response

    def user_login(self,serverURL,API_username,API_password):
        """
        Login to a zabbix server. Provide an username/password.
        :param serverURL: Full hostname of the Zabbix server . i.e.: http://localhost:8081
        :param userName: Full username. i.e.: myuser@customer1
        :param password: password for the specified user and host. i.e.: mypassword
        :returns: the status code of the login request. Null if there was a problem getting the login.
        """
        if 'DEBUG' in locals(): print ("Logging to zabbix server with " + API_username + ":" + API_password + "@" + serverURL + " ...")
        self.API_URL = serverURL
        try:
            response = super(ZabbixAPIClient, self).request(url=self.API_URL, method="post", json={
                            "jsonrpc": "2.0",
                            "method": "user.login",
                            "params": { "user": API_username, "password": API_password },
                            "id": 1
                        })
        except requests.exceptions.ConnectionError as error:
            sys.stderr.write(str(error)+"\n")
            return None

        responseJSON = response.json()
        if 'error' in responseJSON:
            sys.stderr.write(responseJSON['error']['data']+"\n")
            return responseJSON['error']['code']
        self.authToken = responseJSON["result"]
        if 'DEBUG' in locals(): print ("New token obtained: " + self.authToken)
        return response.status_code

    def user_logout(self):
        """
        Logout from zabbix server.
        :returns: the status code of the logout request. Null if there was a problem getting logged out.
        """
        try:
            response = super(ZabbixAPIClient, self).request(url=self.API_URL, method="post", json={
                            "jsonrpc": "2.0",
                            "method": "user.logout",
                            "params": {},
                            "id": 2,
                            "auth": self.authToken
                        })
        except:
            sys.stderr.write("There was a problem logging out.\n")
            return None
        return response.status_code