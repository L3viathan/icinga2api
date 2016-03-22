# -*- coding: utf-8 -*-
'''
icinga2 api client

write for icinga2 2.4
'''

from __future__ import print_function
import logging
import os
import requests
import sys
# pylint: disable=import-error,no-name-in-module
if sys.version_info >= (3, 0):
    from urllib.parse import urljoin
    import configparser as configparser
else:
    from urlparse import urljoin
    import ConfigParser as configparser
# pylint: enable=import-error,no-name-in-module

import icinga2api

LOG = logging.getLogger(__name__)


class Icinga2ApiException(Exception):
    '''
    Icinga 2 API exception class
    '''

    def __init__(self, error):
        super(Icinga2ApiException, self).__init__(error)
        self.error = error

    def __str__(self):
        return str(self.error)


class Icinga2ApiConfigFileException(Exception):
    '''
    Icinga 2 API config file exception class
    '''

    def __init__(self, error):
        super(Icinga2ApiConfigFileException, self).__init__(error)
        self.error = error

    def __str__(self):
        return str(self.error)


class ClientConfigFile(object):
    '''
    Icinga 2 API config file
    '''

    def __init__(self, file_name):
        '''
        initialization
        '''

        self.file_name = file_name
        self.section = 'api'
        self.url = None
        self.username = None
        self.password = None
        self.certificate = None
        self.key = None
        self.ca_certificate = None
        self.timeout = None
        self._check_file_access()

    def _check_file_access(self):
        '''
        check access to the config file

        :returns: True
        :rtype: bool
        '''

        if not os.path.exists(self.file_name):
            raise Icinga2ApiConfigFileException(
                'Config file "{0}" doesn\'t exist.'.format(
                    self.file_name
                )
            )

        if not os.access(self.file_name, os.R_OK):
            raise Icinga2ApiConfigFileException(
                'No read access for config file "{0}".\n'.format(
                    self.file_name
                )
            )

        return True

    def parse(self):
        '''
        parse the config file
        '''

        cfg = configparser.ConfigParser()
        cfg.read(self.file_name)

        if not cfg.has_section(self.section):
            raise Icinga2ApiConfigFileException(
                'Config file is missing "{0}" section.'.format(
                    self.section
                )
            )

        # [api]/url
        try:
            self.url = cfg.get(
                self.section,
                'url'
            ).strip()
        except configparser.NoOptionError:
            pass

        # [api]/username
        try:
            self.username = cfg.get(
                self.section,
                'username'
            ).strip()
        except configparser.NoOptionError:
            pass

        # [api]/password
        # do we really want to store the password here
        # or use the keyring
        try:
            self.password = cfg.get(
                self.section,
                'password'
            ).strip()
        except configparser.NoOptionError:
            pass

        # [api]/certificate
        try:
            self.certificate = cfg.get(
                self.section,
                'certificate'
            ).strip()
        except configparser.NoOptionError:
            pass

        # [api]/client_key
        try:
            self.key = cfg.get(
                self.section,
                'key'
            ).strip()
        except configparser.NoOptionError:
            pass

        # [api]/ca_certificate
        try:
            self.ca_certificate = cfg.get(
                self.section,
                'ca_certificate'
            ).strip()
        except configparser.NoOptionError:
            pass

        # [api]/timeout
        try:
            self.timeout = cfg.get(
                self.section,
                'timeout'
            ).strip()
        except configparser.NoOptionError:
            pass


class Client(object):
    '''
    Icinga 2 Client class
    '''

    def __init__(self,
                 url=None,
                 username=None,
                 password=None,
                 timeout=None,
                 certificate=None,
                 key=None,
                 ca_certificate=None,
                 config_file=None):
        '''
        initialize object
        '''

        if config_file:
            config_from_file = ClientConfigFile(config_file)
            config_from_file.parse()
        self.url = url or \
            config_from_file.url
        self.username = username or \
            config_from_file.username
        self.password = password or \
            config_from_file.password
        self.timeout = timeout or \
            config_from_file.timeout
        self.certificate = certificate or \
            config_from_file.certificate
        self.key = key or \
            config_from_file.key
        self.ca_certificate = ca_certificate or \
            config_from_file.ca_certificate
        self.objects = Objects(self)
        self.actions = Actions(self)
        self.events = Events(self)
        self.status = Status(self)
        self.version = icinga2api.__version__

        if not self.url:
            raise Icinga2ApiException('No "url" defined.')
        # TODO: do more checking


class Base(object):
    '''
    Icinga 2 API Base class
    '''

    base_url_path = None  # 继承

    def __init__(self, manager):
        '''
        initialize object
        '''

        self.manager = manager
        self.stream_cache = ""

    def _create_session(self, method='POST'):
        '''
        create a session object
        '''

        session = requests.Session()
        # prefer certificate authentification
        # TODO: make it configurable
        if self.manager.certificate and self.manager.key:
            # certificate and key are in different files
            session.cert = (self.manager.certificate, self.manager.key)
        elif self.manager.certificate:
            # certificate and key are in the same file
            session.cert = self.manager.certificate
        elif self.manager.username and self.manager.password:
            # use username and password
            session.auth = (self.manager.username, self.manager.password)
        session.headers = {
            'User-Agent': 'Python-icinga2api/{0}'.format(self.manager.version),
            'X-HTTP-Method-Override': method.upper(),
            'Accept': 'application/json'
        }

        return session

    def _request(self, method, url_path, payload=None):
        '''
        make the request and return the body

        :param method: the HTTP method
        :type method: string
        :param url_path: the requested url path
        :type url_path: string
        :param payload: the payload to send
        :type payload: dictionary
        :returns: the response as json
        :rtype: dictionary
        '''

        request_url = urljoin(self.manager.url, url_path)
        LOG.debug("Request URL: {0}".format(request_url))

        # create session
        session = self._create_session(method)

        # create arguments for the request
        request_args = {
            'url': request_url
        }
        if payload:
            request_args['json'] = payload
        if self.manager.ca_certificate:
            request_args['verify'] = self.manager.ca_certificate
        else:
            request_args['verify'] = False

        # do the request
        response = session.post(**request_args)

        session.close()
        from pprint import pprint
        pprint(request_url)
        pprint(payload)
        pprint(response)

        if not 200 <= response.status_code <= 299:
            raise Icinga2ApiException('Request "{}" failed with status {}: {}'.format(
                response.url,
                response.status_code,
                response.text))

        return response.json()

    # TODO 使用stringIO
    def fetech_from_stream(self, stream, split_str='\n', chunk_size=1024):
        '''将stream中的多个chunk合并,并返回其中完整的数据
        :param split: 每条数据之间的分隔符
        :param chunk_size: byte
        :return:
        '''
        for chunk in stream(chunk_size):
            self.stream_cache += chunk
            lines = self.stream_cache.split(split_str)
            if len(lines) >= 2:
                self.stream_cache = lines[-1]  # 保留最后一行,他可能是不完整的.
                yield lines[:-1]


class Objects(Base):
    '''
    Icinga 2 API objects class
    '''

    base_url_path = '/v1/objects'

    @staticmethod
    def _convert_object_type(object_type=None):
        '''
        check if the object_type is a valid Icinga 2 object type
        '''

        type_conv = {
            'ApiListener': 'apilisteners',
            'ApiUser': 'apiusers',
            'CheckCommand': 'checkcommands',
            'Arguments': 'argumentss',
            'CheckerComponent': 'checkercomponents',
            'CheckResultReader': 'checkresultreaders',
            'Comment': 'comments',
            'CompatLogger': 'compatloggers',
            'Dependency': 'dependencys',
            'Downtime': 'downtimes',
            'Endpoint': 'endpoints',
            'EventCommand': 'eventcommands',
            'ExternalCommandListener': 'externalcommandlisteners',
            'FileLogger': 'fileloggers',
            'GelfWriter': 'gelfwriters',
            'GraphiteWriter': 'graphitewriters',
            'Host': 'hosts',
            'HostGroup': 'hostgroups',
            'IcingaApplication': 'icingaapplications',
            'IdoMySqlConnection': 'idomysqlconnections',
            'IdoPgSqlConnection': 'idopgsqlconnections',
            'LiveStatusListener': 'livestatuslisteners',
            'Notification': 'notifications',
            'NotificationCommand': 'notificationcommands',
            'NotificationComponent': 'notificationcomponents',
            'OpenTsdbWriter': 'opentsdbwriters',
            'PerfdataWriter': 'perfdatawriters',
            'ScheduledDowntime': 'scheduleddowntimes',
            'Service': 'services',
            'ServiceGroup': 'servicegroups',
            'StatusDataWriter': 'statusdatawriters',
            'SyslogLogger': 'syslogloggers',
            'TimePeriod': 'timeperiods',
            'User': 'users',
            'UserGroup': 'usergroups',
            'Zone': 'zones',
        }
        if not object_type in type_conv:
            raise Icinga2ApiException('Icinga 2 object type "{}" does not exist.'.format(object_type))

        return type_conv[object_type]

    def list(self, object_type, name=None, attrs=None, filters=None, joins=None):
        '''
        get object by type or name

        :param object_type: type of the object
        :type object_type: string
        :param name: list object with this name
        :type name: string
        :param attrs: only return these attributes
        :type attrs: list
        :param filters: filter the object list
        :type filters: string
        :param joins: show joined object
        :type joins: list

        example 1:
        list('Host')

        example 2:
        list('Service', 'webserver01.domain!ping4')

        example 3:
        list('Host', attrs='["address", "state"])

        example 4:
        list('Host', filters='match("webserver*", host.name)')

        example 5:
        list('Service', joins=['host.name'])

        example 6:
        list('Service', joins=True)
        '''

        object_type_url_path = self._convert_object_type(object_type)
        url_path = '{}/{}'.format(self.base_url_path, object_type_url_path)
        if name:
            url_path += '/{}'.format(name)

        payload = {}
        if attrs:
            payload['attrs'] = attrs
        if filters:
            payload['filter'] = filters
        if isinstance(joins, bool) and joins:
            payload['all_joins'] = '1'
        elif joins:
            payload['joins'] = joins

        return self._request('GET', url_path, payload)

    def create(self, object_type, name, templates=None, attrs=None):
        '''
        create an object

        :param object_type: type of the object
        :type object_type: string
        :param name: the name of the object
        :type name: string
        :param templates: templates used
        :type templates: list
        :param attrs: object's attributes
        :type attrs: dictionary

        example 1:
        create('Host', 'localhost', ['generic-host'], {'address': '127.0.0.1'})

        example 2:
        create('Service', 'testhost3!dummy', {'check_command': 'dummy'}, ['generic-service'])
        '''

        object_type_url_path = self._convert_object_type(object_type)

        payload = {}
        if attrs:
            payload['attrs'] = attrs
        if templates:
            payload['templates'] = templates

        url_path = '{}/{}/{}'.format(self.base_url_path, object_type_url_path, name)

        return self._request('PUT', url_path, payload)

    def update(self, object_type, name, attrs):
        '''
        update an object

        :param object_type: type of the object
        :type object_type: string
        :param name: the name of the object
        :type name: string
        :param attrs: object's attributes to change
        :type attrs: dictionary

        example 1:
        update('Host', 'localhost', {'address': '127.0.1.1'})

        example 2:
        update('Service', 'testhost3!dummy', {'check_interval': '10m'})
        '''
        object_type_url_path = self._convert_object_type(object_type)
        url_path = '{}/{}/{}'.format(self.base_url_path, object_type_url_path, name)

        return self._request('POST', url_path, attrs)

    def delete(self, object_type, name=None, filters=None, cascade=True):
        '''
        delete an object

        :param object_type: type of the object
        :type object_type: string
        :param name: the name of the object
        :type name: string
        :param filters: filter the object list
        :type filters: string
        :param cascade: deleted dependent objects
        :type joins: bool

        example 1:
        delete('Host', 'localhost')

        example 2:
        delete('Service', filters='match("vhost*", service.name)')
        '''

        object_type_url_path = self._convert_object_type(object_type)

        payload = {}
        if filters:
            payload['filter'] = filters
        if cascade:
            payload['cascade'] = 1

        url = '{}/{}'.format(self.base_url_path, object_type_url_path)
        if name:
            url += '/{}'.format(name)

        return self._request('DELETE', url, payload)


class Actions(Base):
    '''
    Icinga 2 API actions class
    '''

    base_url_path = '/v1/actions'

    def process_check_result(self,
                             object_type,
                             name,
                             exit_status,
                             plugin_output,
                             performance_data=None,
                             check_command=None,
                             check_source=None):
        '''
        process a check result for a host or a service

        :param object_type: Host or Service
        :type object_type: string
        :param name: name of the object
        :type name: string
        :param exit_status: services: 0=OK, 1=WARNING, 2=CRITICAL, 3=UNKNOWN; hosts: 0=OK, 1=CRITICAL
        :type filters: integer
        :param plugin_output: plugins main ouput
        :type plugin_output: string
        :param check_command: check command path followed by its arguments
        :type check_command: list
        :param check_source: name of the command_endpoint
        :type check_source: string

        expample 1:
        process_check_result('Service',
                             'myhost.domain!ping4',
                             'exit_status': 2,
                             'plugin_output': 'PING CRITICAL - Packet loss = 100%',
                             'performance_data': [
                                 'rta=5000.000000ms;3000.000000;5000.000000;0.000000',
                                 'pl=100%;80;100;0'],
                             'check_source': 'python client'})
        '''

        if object_type not in ['Host', 'Service']:
            raise Icinga2ApiException('object_type needs to be "Host" or "Service".')

        url = '{}/{}'.format(self.base_url_path, "process-check-result")

        # payload
        payload = {
            '{}'.format(object_type.lower()): name,
            "exit_status": exit_status,
            "plugin_output": plugin_output,
        }
        if performance_data:
            payload["performance_data"] = performance_data
        if check_command:
            payload["check_command"] = check_command
        if check_source:
            payload["check_source"] = check_source

        return self._request('POST', url, payload)

    def reschedule_check(self, filters, next_check=None, force_check=True):
        '''Reschedule a check for hosts and services. The check can be forced if required.

        Parameter 	Type 	Description
        next_check 	timestamp 	Optional. The next check will be run at this time. If omitted the current time is used.
        force_check 	boolean 	Optional. Defaults to false. If enabled the checks are executed regardless of time period restrictions and checks being disabled per object or on a global basis.

        In addition to these parameters a filter must be provided. The valid types for this action are Host and Service.


        example 1:
        filters = {
            "type" : "Service",
            "filter": r'service.name=="ping4"',
        }
        reschedule_check(filters)

        example 2:
        filters = {
            "type" : "Host",
            "filter": r'host.name=="youfu-zf"',
        }
        reschedule_check(filters)
        '''
        if not filters:
            raise Icinga2ApiException("filters is empty or none")
        url = '{}/{}'.format(self.base_url_path, "reschedule-check")

        payload = {
            "force_check": force_check
        }
        if next_check:
            payload["next_check"] = next_check
        payload.update(filters)
        return self._request('POST', url, payload=payload)

    def send_custom_notification(self, filters, author, comment, force=False):
        '''Send a custom notification for hosts and services. This notification type can be forced being sent to all users.

        Parameter 	Type 	Description
        author 	string 	Required. Name of the author, may be empty.
        comment 	string 	Required. Comment text, may be empty.
        force 	boolean 	Optional. Default: false. If true, the notification is sent regardless of downtimes or whether notifications are enabled or not.

        In addition to these parameters a filter must be provided. The valid types for this action are Host and Service.


        example 1:
        filters = {
            "type" : "Host"
        }
        send_custom_notification(filters,'fmnisme',"test comment")
        '''
        if not filters:
            raise Icinga2ApiException("filters is empty or none")
        url = '{}/{}'.format(self.base_url_path, "send-custom-notification")

        payload = {
            "author": author,
            "comment": comment,
            "force": force
        }
        payload.update(filters)
        return self._request('POST', url, payload)

    def delay_notification(self, filters, timestamp):
        '''Delay notifications for a host or a service.
        Note that this will only have an effect if the service stays in the same problem state that it is currently in.
        If the service changes to another state, a new notification may go out before the time you specify in the timestamp argument.

        Parameter 	Type 	Description
        timestamp 	timestamp 	Required. Delay notifications until this timestamp.

        In addition to these parameters a filter must be provided. The valid types for this action are Host and Service.


        example 1:
        filters = {
            "type" : "Service",
        }
        delay_notification(filters,"1446389894")

        example 2:
        filters = {
            "type" : "Host",
            "filter" : r'host.name=="youfu-zf"'
        }
        delay_notification(filters,"1446389894")

        '''
        if not filters:
            raise Icinga2ApiException("filters is empty or none")
        url = '{}/{}'.format(self.base_url_path, "delay-notification")

        payload = {
            "timestamp": timestamp
        }
        payload.update(filters)
        return self._request('POST', url, payload)

    def acknowledge_problem(self,
                            object_type,
                            filters,
                            author,
                            comment,
                            expiry=None,
                            sticky=None,
                            notify=None):
        '''
        Acknowledge a Service or Host problem.

        :param object_type: Host or Service
        :type object_type: string
        :param filters: filter the object
        :type filters: string
        :param author: name of the author
        :type author: string
        :param comment: comment text
        :type comment: string
        :param expiry: acknowledgement expiry timestamp
        :type expiry: int
        :param sticky: stay till full problem recovery
        :type sticky: bool
        :param notify: send notification
        :type notify: string
        :returns: the response as json
        :rtype: dictionary
        '''
        url = '{}/{}'.format(self.base_url_path, "acknowledge-problem")

        payload = {
            'type': object_type,
            'filter': filters,
            'author': author,
            'comment': comment,
        }
        if expiry:
            payload['expiry'] = expiry
        if sticky:
            payload['sticky'] = sticky
        if notify:
            payload['notify'] = notify

        return self._request('POST', url, payload)

    def remove_acknowledgement(self,
                               object_type,
                               filters):
        '''
        Remove the acknowledgement for services or hosts.

        example 1:
        remove_acknowledgement(object_type='Service',
                               'service.state==2')

        :param object_type: Host or Service
        :type object_type: string
        :param filters: filter the object
        :type filters: string
        :returns: the response as json
        :rtype: dictionary
        '''

        url = '{}/{}'.format(self.base_url_path, 'remove-acknowledgement')

        payload = {
            'type': object_type,
            'filter': filters
        }

        return self._request('POST', url, payload)

    def add_comment(self,
                    object_type,
                    filters,
                    author,
                    comment):
        '''
        Add a comment from an author to services or hosts.

        example 1:
        add_comment('Service',
                    'service.name=="ping4"',
                    'icingaadmin',
                    'Incident ticket #12345 opened.')

        :param object_type: Host or Service
        :type object_type: string
        :param filters: filter the object
        :type filters: string
        :param author: name of the author
        :type author: string
        :param comment: comment text
        :type comment: string
        :returns: the response as json
        :rtype: dictionary
        '''

        url = '{}/{}'.format(self.base_url_path, 'add-comment')

        payload = {
            'type': object_type,
            'filter': filters,
            'author': author,
            'comment': comment
        }

        return self._request('POST', url, payload)

    def remove_comment(self,
                       object_type,
                       name,
                       filters):
        '''
        Remove a comment using its name or a filter.

        example 1:
        remove_comment('Comment'
                       'localhost!localhost-1458202056-25')

        example 2:
        remove_comment('Service'
                       filters='service.name=="ping4"')

        :param object_type: Host, Service or Comment
        :type object_type: string
        :param name: name of the Comment
        :type name: string
        :param filters: filter the object
        :type filters: string
        :returns: the response as json
        :rtype: dictionary
        '''

        url = '{}/{}'.format(self.base_url_path, 'remove-comment')

        payload = {
            'type': object_type
        }
        if name:
            payload[object_type.lower()] = name
        if filters:
            payload['filter'] = filters

        return self._request('POST', url, payload)

    def schedule_downtime(self,
                          object_type,
                          filters,
                          author,
                          comment,
                          start_time,
                          end_time,
                          duration,
                          fixed=None,
                          trigger_name=None):
        '''
        Schedule a downtime for hosts and services.

        example 1:
        schedule_downtime(
            'object_type': 'Service',
            'filters': r'service.name=="ping4"',
            'author': 'icingaadmin',
            'comment': 'IPv4 network maintenance',
            'start_time': 1446388806,
            'end_time': 1446389806,
            'duration': 1000
        }

        example 2:
        schedule_downtime(
            'object_type': 'Host',
            'filters': r'match("*", host.name)',
            'author': 'icingaadmin',
            'comment': 'IPv4 network maintenance',
            'start_time': 1446388806,
            'end_time': 1446389806,
            'duration': 1000
        }

        :param object_type: Host or Service
        :type object_type: string
        :param filters: filter the object
        :type filters: string
        :param author: name of the author
        :type author: string
        :param comment: comment text
        :type comment: string
        :param start_time: timestamp marking the beginning
        :type start_time: string
        :param end_time: timestamp marking the end
        :type end_time: string
        :param duration: duration of the downtime in seconds
        :type duration: int
        :param fixed: fixed or flexible downtime
        :type fixed: bool
        :param trigger_name: trigger for the downtime
        :type trigger_name: string
        :returns: the response as json
        :rtype: dictionary
        '''

        url = '{}/{}'.format(self.base_url_path, 'schedule-downtime')

        payload = {
            'type': object_type,
            'filter': filters,
            'author': author,
            'comment': comment,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration
        }
        if fixed:
            payload['fixed'] = fixed
        if trigger_name:
            payload['trigger_name'] = trigger_name

        return self._request('POST', url, payload)

    def remove_downtime(self,
                        object_type,
                        name=None,
                        filters=None):
        '''
        Remove the downtime using its name or a filter.

        example 1:
        remove_downtime('Downtime',
                        'localhost!ping4!localhost-1458148978-14')

        example 2:
        remove_downtime('Service',
                        filters='service.name=="ping4"')

        :param object_type: Host, Service or Downtime
        :type object_type: string
        :param name: name of the downtime
        :type name: string
        :param filters: filter the object
        :type filters: string
        :returns: the response as json
        :rtype: dictionary
        '''

        if not name and not filters:
            raise Icinga2ApiException("name and filters is empty or none")

        url = '{}/{}'.format(self.base_url_path, 'remove-downtime')

        payload = {
            'type': object_type
        }
        if name:
            payload[object_type.lower()] = name
        if filters:
            payload['filter'] = filters

        return self._request('POST', url, payload)

    def shutdown_process(self):
        '''
        Shuts down Icinga2. May or may not return.

        example 1:
        shutdown_process()
        '''

        url = '{}/{}'.format(self.base_url_path, 'shutdown-process')

        return self._request('POST', url)

    def restart_process(self):
        '''
        Restarts Icinga2. May or may not return.

        example 1:
        restart_process()
        '''

        url = '{}/{}'.format(self.base_url_path, 'restart-process')

        return self._request('POST', url)


class Events(Base):
    '''
    Icinga 2 API events class
    '''

    base_url_path = "/v1/events"

    def subscribe(self, types, queue, filters=None):
        '''You can subscribe to event streams by sending a POST request to the URL endpoint /v1/events.

        The following parameters need to be specified (either as URL parameters or in a JSON-encoded message body):
        Parameter 	Type 	Description
        types 	string array 	Required. Event type(s). Multiple types as URL parameters are supported.
        queue 	string 	Required. Unique queue name. Multiple HTTP clients can use the same queue as long as they use the same event types and filter.
        filter 	string 	Optional. Filter for specific event attributes using filter expressions.

        Event Stream Types

        The following event stream types are available:
        Type 	Description
        CheckResult 	Check results for hosts and services.
        StateChange 	Host/service state changes.
        Notification 	Notification events including notified users for hosts and services.
        AcknowledgementSet 	Acknowledgement set on hosts and services.
        AcknowledgementCleared 	Acknowledgement cleared on hosts and services.
        CommentAdded 	Comment added for hosts and services.
        CommentRemoved 	Comment removed for hosts and services.
        DowntimeAdded 	Downtime added for hosts and services.
        DowntimeRemoved 	Downtime removed for hosts and services.
        DowntimeTriggered 	Downtime triggered for hosts and services.

        Note: Each type requires API permissions being set.


        example 1:
        types = ["CheckResult"]
        queue = "michi"
        filters = "event.check_result.exit_status==2"
        for event in subscribe(types,queue,filters):
            print event
        :param types:
        :param queue:
        :param filters:
        :return:
        '''
        payload = {
            "types": types,
            "queue": queue,
        }
        if filters:
            payload["filters"] = filters
        stream = self._request('POST', self.base_url_path, payload, stream=True)
        for events in self.fetech_from_stream(stream):   # return list
            for event in events:
                yield event


class Status(Base):
    '''
    Icinga 2 API status class
    '''

    base_url_path = "/v1/status"

    def list(self, component=None):
        '''
        retrieve status information and statistics for Icinga 2

        example 1:
        list()

        example 2:
        list('IcingaApplication')

        :param component: only list the status of this component
        :type component: string
        :returns: status information
        :rtype: dictionary
        '''

        url = self.base_url_path
        if component:
            url += "/{}".format(component)

        return self._request('GET', url)
