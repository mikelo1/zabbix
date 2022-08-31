#!/usr/bin/python
import json
import csv
import sys

class Entity(dict):

    def __init__(self):
        super(Entity,self).__init__()
        self.update({"keywords":[],"CSVfields":{},"entities":None})

#    def __str__(self):
#        return "({0},{1})".format(self.__class__.__name__,len(self['entities']))
#        return "({0},{1})".format(type(self),id(self))

#    def info(self):
#        return "Class ",self.__class__,"Number of entities in ", hex(id(self['entities'])), len(self['entities'])

    def load(self,streamdata):
        """
        Load entities from a JSON stream data.
        :param streamdata: the stream data in JSON format
        :returns: the number of loaded entities. Zero if no entity was loaded.
        """
        if type(streamdata) is dict or type(streamdata) is list:
            self['entities'] = streamdata
        else:
            try:
                self['entities'] = json.loads(streamdata)
            except (TypeError,ValueError) as error:
                if 'DEBUG' in locals(): sys.stderr.write("load_Entity("+self.__class__.__name__+"): "+str(error)+"\n")
                return 0
        return len(self['entities'])

    def generate_CSV(self,fileName=None):
        """
        Generate CSV output from dictionary data
        :param fileName: output file name
        :returns: None
        """
        if fileName is not None:
            try:
                csvfile = open(fileName, 'w')
            except:
                sys.stderr.write("Could not open output file " + fileName + ".")
                return (-1)
        else:
            csvfile = sys.stdout

        #from zbx_API.APIClient import ZabbixAPIClient
        #APIFields = ZabbixAPIClient.target[self.__class__.__name__][]

        # create the csv writer object
        fieldnames = [ name for name in self['CSVfields'] ]
        filewriter = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=',', quotechar='"')

        for entity in self['entities']:
            if 'header_is_printed' not in locals():
                filewriter.writeheader()
                header_is_printed=True
            row = { name: self['CSVfields'][name](entity) for name in self['CSVfields'] }
            try:
                filewriter.writerow(row)
            except ValueError as valError:
                sys.stderr.write("generate_CSV: "+str(valError)+"\n")
                if fileName is not None: csvfile.close()
                return (-1)
        if fileName is not None: csvfile.close()
        #raise NotImplementedError("Don't forget to implement the generate_CSV function!")

    def generate_JSON(self,fileName=None):
        """
        Generate JSON output from dictionary data
        :param fileName: output file name
        :returns: None
        """
        if fileName is not None:
            try:
                with open(fileName, 'w') as outfile:
                    json.dump(self['entities'], outfile)
                outfile.close()
            except:
                sys.stderr.write("Could not open output file " + fileName + ".")
                return (-1)
        else:
            print (json.dumps(self['entities']))



class Problems(Entity):

    def __init__(self):
        super(Problems,self).__init__()
        self['CSVfields']= {'Name':         self.__str_problem_name,
                            'Severity':     self.__str_problem_severity,
                            'Acknowledged': self.__str_problem_acknowledged }

    def __str_problem_name(self,problem):
        if 'name' in problem:
            return problem['name'] if sys.version_info[0] >= 3 else problem['name'].encode('ASCII', 'ignore')
        else:
            return problem['objectid']


    def __str_problem_severity(self,problem):
        return problem['severity'] if 'severity' in problem else ""

    def __str_problem_acknowledged(self,problem):
        return problem['acknowledged'] if 'acknowledged' in problem else ""


class Triggers(Entity):

    def __init__(self):
        super(Triggers,self).__init__()
        self['CSVfields']= {'Name':       self.__str_trigger_name,
                            'Expression': self.__str_trigger_expression,
                            'Priority':   self.__str_trigger_priority,
                            'Error':      self.__str_trigger_error,
                            'Hosts':      self.__str_trigger_hosts,
                            'Comments':   self.__str_trigger_comments }

    def __str_trigger_name(self,trigger):
        return trigger['description'] if sys.version_info[0] >= 3 else trigger['description'].encode('ASCII', 'ignore')

    def __str_trigger_expression(self,trigger):
        return trigger['expression']

    def __str_trigger_priority(self,trigger):
        return trigger['priority']

    def __str_trigger_error(self,trigger):
        return trigger['error']

    def __str_trigger_hosts(self,trigger):
        hostDict = EntitySingletonFactory.getInstance().getEntityObj("Hosts")
        return [ host['name'] for trigger_host in trigger['hosts'] for host in hostDict['entities'] if host['hostid'] == trigger_host['hostid'] ]

    def __str_trigger_comments(self,trigger):
        return trigger['comments']

class Hosts(Entity):

    def __init__(self):
        super(Hosts,self).__init__()
        self['CSVfields']= {'Name':       self.__str_host_name }

    def __str_host_name(self,host):
        return host['name'] if sys.version_info[0] >= 3 else host['name'].encode('ASCII', 'ignore')

class Hostinterfaces(Entity):

    def __init__(self):
        super(Hostinterfaces,self).__init__()
        self['CSVfields']= {'ID':   self.__str_hostinterface_id,
                            'Host': self.__str_hostinterface_host,
                            'IP':   self.__str_hostinterface_ip,
                            'Port': self.__str_hostinterface_port }

    def __str_hostinterface_id(self,hostinterface):
        return hostinterface['interfaceid']

    def __str_hostinterface_host(self,hostinterface):
        hostDict = EntitySingletonFactory.getInstance().getEntityObj("Hosts")
        for host in hostDict['entities']:
            if host['hostid'] == hostinterface['hostid']:
                return host['name']
        return hostinterface['hostid']

    def __str_hostinterface_ip(self,hostinterface):
        return hostinterface['ip']

    def __str_hostinterface_port(self,hostinterface):
        return hostinterface['port']

class EntitySingletonFactory:
    __instance = None
    entities   = dict()
 
    def __init__(self):
        """ Virtually private constructor. """
        if EntitySingletonFactory.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            EntitySingletonFactory.__instance = self
        self.entities['Problems']       = Problems()
        self.entities['Triggers']       = Triggers()
        self.entities['Hosts']          = Hosts()
        self.entities['Hostinterfaces'] = Hostinterfaces()
 
    @staticmethod
    def getInstance():
        """ Static access method. """
        if EntitySingletonFactory.__instance == None:
            EntitySingletonFactory()
        return EntitySingletonFactory.__instance

    def getEntityObj(self,name):
        return self.entities[name]