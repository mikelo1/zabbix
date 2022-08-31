
import json
import yaml
import csv
import sys
from datetime import datetime, timedelta
if sys.version_info.major < 3:
    from urlparse import urlparse
else:
    from urllib.parse import urlparse
import base64

class Contexts:
    data       = {
        'Kind': 'Config',
        'contexts': [ ],
        'users': [ ],
        'current-context': ''
    }
    contextFile = ""

    def __init__(self,dataFileName):
        self.contextFile = dataFileName
        try:
            with open(self.contextFile, 'r') as stream:
                self.data = yaml.safe_load(stream)
        except (IOError, yaml.YAMLError) as exc:
            sys.stderr.write(str(exc)+"\n")
            return None

    def __str__(self):
        return "({0},{1})".format(self.contextFile,self.data)

    def view(self):
        try:
            with open(self.contextFile, 'r') as stream:
                sys.stdout.write(stream.readlines())
        except EnvironmentError as exc:
            sys.stderr.write(str(exc)+"\n")

    def save(self):
        if 'DEBUG' in locals(): sys.stdout.write("Saving changes...")
        try:
            with open(self.contextFile, "w") as outfile:
                yaml.dump(self.data, outfile, default_flow_style=False, allow_unicode=True)
        except yaml.YAMLError as exc:
            sys.stderr.write(str(exc)+"\n")


    def get_configFileName(self):
        return self.contextFile

    def get_contexts(self,output=sys.stdout):
        fieldnames = ['CURRENT', 'NAME', 'AUTHINFO']
        filewriter = csv.DictWriter(output, fieldnames=fieldnames, delimiter=',', quotechar='"')
        filewriter.writeheader()

        for context in self.data['contexts']:
            try:
                filewriter.writerow({'CURRENT': "*" if 'current-context' in self.data and context['name'] == self.data['current-context'] else "",
                                     'NAME': context['name'],
                                     'AUTHINFO': context['context']['user']})
            except ValueError as valError:
                sys.stderr.write(str(valError)+"\n")
                return (-1)

    def get_current_context(self,output=sys.stdout):
        if 'current-context' in self.data and len(self.data['current-context']) > 0:
            if output in [sys.stdout,sys.stderr]:
                output.write(self.data['current-context']+"\n")
            return self.data['current-context']
        else:
            return None

    def get_current_context_serverURL(self):
        if 'current-context' in self.data and len(self.data['current-context']) > 0:
            return [context for context in self.data['contexts'] if context['name']==self.data['current-context']][0]['context']['server']

    def get_current_context_user(self):
        if 'current-context' in self.data and len(self.data['current-context']) > 0:
            return [context for context in self.data['contexts'] if context['name']==self.data['current-context']][0]['context']['user']

    def get_current_context_username(self):
        if 'current-context' in self.data and len(self.data['current-context']) > 0:
            return [context for context in self.data['contexts'] if context['name']==self.data['current-context']][0]['context']['user'].split('/')[0]

    def get_current_context_token(self):
        if 'current-context' in self.data and len(self.data['current-context']) > 0:
            current_user = self.get_current_context_user()
            userdata = [user for user in self.data['users'] if user['name']==current_user][0]['user']
            if userdata is not None and 'expire' in userdata and datetime.today() < userdata['expire']:
                if 'DEBUG' in locals(): sys.stdout.write("Found valid token in config YAML file.")
                return userdata['token']
            else:
                if 'DEBUG' in locals(): sys.stderr.write("Token expired or invalid in config YAML file.")
                return None

    def set_current_context_token(self,access_token,expires_in):
        if 'current-context' in self.data and len(self.data['current-context']) > 0:
            current_user = self.get_current_context_user()
            userdata = [user for user in self.data['users'] if user['name']==current_user][0]['user']
            if userdata is not None:
                userdata['token']  = str(access_token)
                userdata['expire'] = datetime.now()+timedelta(seconds=expires_in)
                self.save()
                return True
        return False

    def select_context(self,contextname):
        if 'current-context' in self.data and self.data['current-context'] == contextname:
            sys.stdout.write("Context " + contextname + " already selected.\n")
            return contextname
        for context in self.data['contexts']:
            if context['name'] == contextname:
                self.data['current-context'] = contextname
                self.save()
                sys.stdout.write("Context changed to "+contextname+"\n")
                return contextname
        sys.stderr.write("Context "+contextname+" does not exist.\n")
        return None

    # @param serverURL Full hostname of the Appdynamics controller. i.e.: https://demo1.appdynamics.com:443
    # @param API_Client Full username, including account. i.e.: myuser@customer1
    def create_context(self,contextname,serverURL,API_Client):
        url = urlparse(serverURL)
        if len(url.scheme) == 0 or len(url.netloc) == 0:
            sys.stderr.write("URL is not correctly formatted. <protocol>://<host>:<port>\n")
            return
        servername = url.netloc
        username = API_Client + "/" + servername
        if contextname is None: contextname = servername + "/" + API_Client

        # Check whether provided user does exist or not
        if ( len([ usr['name'] for usr in self.data['users'] if usr['name']==username ]) > 0 or
             len([ ctx['name'] for ctx in self.data['contexts'] if ctx['name']==contextname ]) > 0 ):
            sys.stderr.write("User or context already exists.\n")
        else:
            # Create the new user and set this one as current-context
            self.data['users'].append({'name': username,'user': {}})
            self.data['contexts'].append({'name': contextname,'context': { 'server': serverURL, 'user': username}})
            self.data['current-context'] = contextname
            self.save()

    def delete_context(self,contextname):
        context_index = 0
        for context in self.data['contexts']:
            if context['name'] == contextname:
                context_user = context['context']['user']
                user_index = 0
                for user in self.data['users']:
                    if user['name'] == context_user: break
                    else: user_index += 1
                if user_index < len (self.data['users']):
                    self.data['users'].pop(user_index)
                break
            else: context_index += 1
        if context_index < len(self.data['contexts']): 
            self.data['contexts'].pop(context_index)
            if 'current-context' in self.data and self.data['current-context'] == contextname:
                self.data.pop('current-context')
            self.save()
        else:
            sys.stderr.write("Context does not exist.\n")

    def rename_context(self,contextname,new_contextname):
        for context in self.data['contexts']:
            if context['name'] == contextname:
                context['name'] = new_contextname
                self.save()
                sys.stdout.write("Context changed to "+new_contextname+"\n")
                return new_contextname
        sys.stderr.write("Context "+contextname+" does not exist.\n")
        return None

    def set_credentials(self,contextname):
        context = [context for context in self.data['contexts'] if context['name']==contextname]
        if not context:
            sys.stdout.write("Context "+contextname+" does not exist.\n")
        else:
            API_Client = context[0]['context']['user']
            user = [user for user in self.data['users'] if user['name']==API_Client][0]
            sys.stderr.write("Authentication required for " + API_Client + "\n")
            Client_Secret = getpass(prompt='Password: ')
            user['user'].update({'password': base64.b64encode(Client_Secret.encode('ascii'))})
            self.save()

    def get_credentials(self,contextname):
        context = [context for context in self.data['contexts'] if context['name']==contextname]
        if not context:
            sys.stdout.write("Context "+contextname+" does not exist.\n")
        else:
            API_Client = context[0]['context']['user']
            user = [user for user in self.data['users'] if user['name']==API_Client][0]
            if 'password' in user['user']:
                return base64.b64decode(user['user']['password'].encode('ascii')).decode('ascii')


class BasicAuth:
    authFile  = ""
    authDict = dict()

    def __init__(self,basicAuthFile=None):
        if basicAuthFile is not None:
            try:
                with open(basicAuthFile, mode='r') as csv_file:
                    auth_dict = csv.DictReader(csv_file,fieldnames=['password','apiClient','host'])
                    for row in auth_dict:
                        self.authDict.update({row['apiClient']+"/"+row['host']:row['password']})
            except (IOError, FileNotFoundError) as exc:
                sys.stderr.write(str(exc)+"\n")
                return None
            self.authFile = basicAuthFile

    def __str__(self):
        return "({0},{1})".format(self.authFile, len(self.authDict))

    def get_authFileName(self):
        return self.authFile

    def get_password(self,API_Client):
        if API_Client in self.authDict:
            return base64.b64decode(self.authDict[API_Client].encode('ascii')).decode('ascii')
        return None