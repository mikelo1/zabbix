#!/usr/bin/python
import sys
import os.path
import re
from datetime import datetime, timedelta
import time
import json
from contexts import Contexts, BasicAuth
from zbx_API.APIClient import ZabbixAPIClient
from zbx_API.entities import Entity, EntitySingletonFactory as EntitySF
from optparse import OptionParser, OptionGroup


def get_help(COMMAND,SUBCOMMAND=None,output=sys.stdout):
  if output not in [sys.stdout,sys.stderr]: return
  if COMMAND=="help" and SUBCOMMAND is None:
    optParser.print_help()
  elif COMMAND=="get" and SUBCOMMAND is None:
    sys.stderr.write("Usage: zbxctl get [Problems|Triggers|Hosts] [options]\n\n")
#  elif COMMAND=="describe" and SUBCOMMAND is None:
#    sys.stderr.write("Usage: zbxctl describe [policy|action|schedule|healthrule|\n" + \
#                     "                    detection-rule|businesstransaction|backend|entrypoint|\n" + \
#                     "                    application|tier|node|dashboard|config|user] <entity_name> [options]\n\n")
  elif COMMAND=="config" and SUBCOMMAND is None:
    output.write ("Modify zbxconfig files using subcommands like \"zbxctl config set current-context my-context\"\n\n" + \
                "Available Commands:\n" + \
                "  current-context Displays the current-context\n" + \
                "  delete-context  Delete the specified context from the zbxconfig\n" + \
                "  get-contexts    Describe one or many contexts\n" + \
                "  rename-context  Renames a context from the zbxconfig file.\n" + \
                "  set-context     Sets a context entry in zbxconfig\n" + \
                "  set-credentials Sets a user entry in zbxconfig\n" + \
                "  unset           Unsets an individual value in a zbxconfig file\n" + \
                "  use-context     Sets the current-context in a zbxconfig file\n" + \
                "  view            Display merged zbxconfig settings or a specified zbxconfig file\n\n" + \
                "Usage:\n" + \
                "  zbxctl config SUBCOMMAND [options]\n\n")
#  elif COMMAND=="patch" and SUBCOMMAND is None:
#    output.write("Usage: appdctl patch [schedules] [options]\n\n")
#  elif COMMAND=="apply" and SUBCOMMAND is None:
#    sys.stderr.write("Usage: appdctl apply -f <source_file> -a <application(s)>\n\n")
#  elif COMMAND=="drain" and SUBCOMMAND is None:
#    sys.stderr.write("Drain unavailable nodes for a set of applications.\nUsage: appdctl drain -a <application(s)>\n\n")
  exit()

def get_selectors():
    return { selector.split('=')[0]:selector.split('=')[1] for selector in options.selector.split(',') } if options.selector else {}

usage = "usage: %prog [get|describe|config|apply|patch|drain] [options]"
epilog= "examples: %prog get applications"

optParser = OptionParser(usage=usage, version="%prog 0.1", epilog=epilog)
#optParser.add_option("-h", "--help", 
#                  action="store_true", default=False, dest="showHelp",
#                  help="Display help for command")
optParser.add_option("-o", "--output", action="store", dest="outFormat",
                  help="Output format. One of: json|csv")
optParser.add_option("--server-url", action="store", dest="serverURL",
                  help="URL of the Zabbix server")
optParser.add_option("--user-API", action="store", dest="userAPI",
                  help="API client username")
optParser.add_option("--basic-auth-file", action="store", dest="basicAuthFile",
                  help="Basic authentication file")
groupQuery = OptionGroup(optParser, "Query range options")
groupQuery.add_option("-l", "--selector",
                  action="store", dest="selector",
                  help="Selector to filter on, supports '=', '==', and '!='.(e.g. -l key1=value1,key2=value2)")
optParser.add_option_group(groupQuery)
(options, args) = optParser.parse_args()


# Load contexts
zbxContexts = Contexts("zbxconfig.yaml")
if zbxContexts is not None:
  serverURL    = zbxContexts.get_current_context_serverURL()
  API_username = zbxContexts.get_current_context_username()
  if API_username is not None and options.basicAuthFile:
    bAuth = BasicAuth(basicAuthFile=options.basicAuthFile)
    API_password = bAuth.get_password(user)
  elif API_username is not None:
    API_password = zbxContexts.get_credentials(zbxContexts.get_current_context(output=None))

if "serverURL" not in locals() or serverURL is None:       serverURL    = "http://localhost:8081/api_jsonrpc.php"
if "API_username" not in locals() or API_username is None: API_username = "Admin"
if "API_password" not in locals() or API_password is None: API_password = "zabbix"


# Start interpreting command line parameters
if len(args) < 1:
    optParser.error("incorrect number of arguments")
    exit()
 
COMMAND = args[0]

if COMMAND.lower() == "help":
  sys.stderr.write(usage+"\n\n")

#######################################
############ CONFIG COMMAND ###########
#######################################
elif COMMAND.lower() == "config":

  if len(args) < 2:
      optParser.error("incorrect number of arguments")
      exit()

  SUBCOMMAND = args[1]

  if SUBCOMMAND == "help":
    get_help(COMMAND)
  elif SUBCOMMAND in ['view','get-contexts','current-context']:
    functions = { 'view':zbxContexts.view,
                  'get-contexts':zbxContexts.get_contexts,
                  'current-context':zbxContexts.get_current_context
                }
    functions[SUBCOMMAND]()
  elif SUBCOMMAND in ['use-context','delete-context','set-credentials','get-credentials']:
    if len(args) < 3:
      optParser.error("incorrect number of arguments")
      exit()
    functions = { 'use-context':zbxContexts.select_context,
                  'delete-context':zbxContexts.delete_context,
                  'set-credentials':zbxContexts.set_credentials,
                  'get-credentials':zbxContexts.get_credentials
                }
    functions[SUBCOMMAND](args[2])
  elif SUBCOMMAND == 'set-context':
    if len(args) < 3:
      optParser.error("incorrect number of arguments")
      exit()
    if not options.serverURL or not options.userAPI:
      optParser.error("missing controller URL or API username.")
      exit()
    zbxContexts.create_context(contextname=args[2],serverURL=options.serverURL,API_Client=options.userAPI)
  elif SUBCOMMAND == 'rename-context':
    if len(args) < 4:
      optParser.error("incorrect number of arguments")
      exit()
    zbxContexts.rename_context(args[2],args[3])
  elif SUBCOMMAND == 'unset':
    sys.stderr.write("Subcommand " + SUBCOMMAND + " not implemented yet.\n")
  else:
    optParser.error("incorrect subcommand \""+SUBCOMMAND+"\"")

#######################################
############# GET COMMAND #############
#######################################
elif COMMAND.lower() == "get":

  if len(args) < 2:
      optParser.error("incorrect number of arguments")
      exit()

  ENTITY = args[1].capitalize()

  # create the filters list, if applies
  selectors = get_selectors()

  if ENTITY == 'Help':
    get_help(COMMAND)

  elif ENTITY in ['Problems','Triggers','Hosts','Hostinterfaces']:

    # Start session
    zbxSession = ZabbixAPIClient()
    zbxSession.user_login(serverURL=serverURL, API_username=API_username, API_password=API_password)

    # Data request and load
    response    = zbxSession.request(entityClassName=ENTITY, verb="fetch")
    entityObj   = EntitySF.getInstance().getEntityObj(ENTITY)
    entityObj.load( response.json()["result"] )

    # Print out loaded data
    if options.outFormat and options.outFormat == "JSON":
        entityObj.generate_JSON()
    elif not options.outFormat or options.outFormat == "CSV":
        if ENTITY in ["Triggers","Hostinterfaces"]: #Load host data as well
            response = zbxSession.request(entityClassName="Hosts", verb="fetchNamesList")
            hostDict = EntitySF.getInstance().getEntityObj("Hosts")
            hostDict.load( response.json()["result"] )
        entityObj.generate_CSV()

    # Close session
    zbxSession.user_logout()