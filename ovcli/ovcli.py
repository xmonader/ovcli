#!/usr/bin/env python3
import requests
from configparser import ConfigParser
import argparse
import os
import subprocess
import time
import base64
import json

def base64url_decode(input):
    """Helper method to base64url_decode a string.
    Args:
        input (str): A base64url_encoded string to decode.
    """
    rem = len(input) % 4

    if rem > 0:
        input += b'=' * (4 - rem)

    return base64.urlsafe_b64decode(input)


def select_item_fzf(items, prompt):
    proc = subprocess.Popen(['fzf', '--prompt', prompt], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    proc.stdin.write(('\n'.join(items)).encode('utf-8'))
    proc.stdin.close()
    proc.wait()
    return proc.stdout.read().strip().decode('utf-8')

def select_item(items, prompt, match=None):
    items = list(sorted(items))
    if match:
        items = list(filter(lambda item: match in item, items))
        if len(items) == 0:
            raise LookupError('Could not find item with filter {}'.format(match))
    if len(items) == 1:
        return items[0]
    try:
        subprocess.check_call(['which', 'fzf'])
    except subprocess.CalledProcessError:
        while True:
            for idx, item in enumerate(items):
                print("{}: {}".format(idx + 1, item))
            data = input(prompt)
            if data.isdigit():
                idx = int(data) - 1
                if idx < len(items):
                    return items[idx]
            print('Entered wrong value')
    else:
        return select_item_fzf(items, prompt)


class OVCli:
    def __init__(self):
        self.config = ConfigParser()
        self.configpath = os.path.expanduser('~/.config/ovc.cfg')
        with open(self.configpath) as fd:
            self.config.read_file(fd)
        self.environments = list(self.config['environments'].keys())
        self.session = requests.Session()

    def is_jwt_expired(self, jwt):
        jwt = jwt.encode('utf-8')
        signing_input, _ = jwt.rsplit(b'.', 1)
        _, claims_segment = signing_input.split(b'.', 1)
        claimsdata = base64url_decode(claims_segment)
        if isinstance(claimsdata, bytes):
            claimsdata = claimsdata.decode('utf-8')
        data = json.loads(claimsdata)
        return data['exp'] < time.time()

    def get_jwt(self):
        jwtkey = 'jwt.{}'.format(self.environment)
        jwt = self.config['iyo'].get(jwtkey)
        if jwt and not self.is_jwt_expired(jwt):
            return jwt
        iyourl = 'https://itsyou.online/v1/oauth/access_token'
        data = {'grant_type': 'client_credentials',
                  'client_id': self.config['iyo']['clientId'],
                  'client_secret': self.config['iyo']['clientsecret'],
                  'response_type': 'id_token',
                  'scope': 'user:memberof:{0}.0-access,user:publickey:ssh'.format(self.environment)
        }
        resp = requests.post(iyourl, data=data, headers={'Accept': 'application/json'})
        resp.raise_for_status()
        jwt = resp.json()['access_token']
        self.config['iyo'][jwtkey] = jwt
        with open(self.configpath, 'w+') as fd:
            self.config.write(fd)
        return jwt


    def select_environment(self, match=None):
        self.environment = select_item(self.environments, "Select environment:  ", match)
        self.envurl = self.config['environments'][self.environment]
        self.session.headers = {'Authorization': 'Bearer {}'.format(self.get_jwt()),
                                'Accept': 'application/json'}

    def select_node(self, match=None):
        response = self.session.post('https://{}/restmachine/system/gridmanager/getNodes'.format(self.envurl))
        response.raise_for_status()
        self.nodes = response.json()
        nodenames = [node['name'] for node in self.nodes]
        nodename = select_item(nodenames, "Select node: ", match)
        self.node = list(filter(lambda node: node['name'] == nodename, self.nodes))[0]

    def select_cloudspace(self, match=None):
        response = self.session.post('https://{}/restmachine/cloudapi/cloudspaces/list'.format(self.envurl))
        response.raise_for_status()
        cloudspaces = {cs['name']: cs for cs in response.json()}
        cloudspacename = select_item(list(cloudspaces.keys()), "Select Cloudspace: ", match)
        return cloudspaces[cloudspacename]

    def select_account(self, match=None):
        response = self.session.post('https://{}/restmachine/cloudapi/accounts/list'.format(self.envurl))
        response.raise_for_status()
        cloudspaces = {cs['name']: cs for cs in response.json()}
        cloudspacename = select_item(list(cloudspaces.keys()), "Select Account: ", match)
        return cloudspaces[cloudspacename]

    def select_vm(self, cloudspaace, match=None):
        response = self.session.post('https://{}/restmachine/cloudapi/machines/list'.format(self.envurl), json={'cloudspaceId': cloudspace['id']})
        response.raise_for_status()
        vms = {vm['name']: vm for vm in response.json()}
        vmname = select_item(list(vms.keys()), "Select VM: ", match)
        return vms[vmname]

    def list_vms(self, cloudspace):
        response = self.session.post('https://{}/restmachine/cloudapi/machines/list'.format(self.envurl), json={'cloudspaceId': cloudspace['id']})
        response.raise_for_status()
        for vm in response.json():
            print("{name} {status}".format(**vm))

    def list_cloudspaces(self):
        response = self.session.post('https://{}/restmachine/cloudapi/cloudspaces/list'.format(self.envurl))
        response.raise_for_status()
        for cloudspace in response.json():
            print("{name} {status} {externalnetworkip}".format(**cloudspace))

    def delete_vm(self, cloudspace, name):
        vm = self.select_vm(cloudspace, name)
        data = {'machineId': vm['id'], 'permanently': True}
        response = self.session.post('https://{}/restmachine/cloudapi/machines/delete'.format(self.envurl), json=data)
        response.raise_for_status()

    def delete_cloudspace(self, cloudspace):
        data = {'cloudspaceId': cloudspace['id'], 'permanently': True, 'reason': 'From CLI'}
        response = self.session.post('https://{}/restmachine/cloudbroker/cloudspace/destroy'.format(self.envurl), json=data)
        response.raise_for_status()

    def create_machine(self, cloudspace, name=None, memory=None, vcpus=None, forward=True):
        """
        Create virtual machine
        
        :param cloudspace: Cloudspace to create virtual machine in
        :type cloudspace: dict
        :param name: Name of the vm to create, defaults to None
        :param name: str, optional
        :param memory: Amount of Memory to give to the virtual machine in MiB, defaults to None
        :param memory: int, optional
        :param vcpus: Amount of virtual CPUS to provide to the virtual machine, defaults to None
        :param vcpus: int, optional
        :raises LookupError: [description]
        """

        if name is None:
            name = input('Enter name: ')
        if memory is None:
            memory = int(input('Memory: '))
        if vcpus is None:
            vcpus = int(input('VCPUS: '))
        response = self.session.post('https://{}/restmachine/cloudapi/images/list'.format(self.envurl))
        response.raise_for_status()
        for image in response.json():
            if 'Ubuntu 16.04' in image['name']:
                imageId = image['id']
                break
        else:
            raise LookupError('Could not find Ubuntu image')
        keyfile = os.path.expanduser('~/.ssh/id_rsa.pub')
        userdata = None
        if os.path.exists(keyfile):
            pubkey = open(keyfile).read()
            userdata = {'users': [{"name":'root', "ssh-authorized-keys": [pubkey], 'shell': '/bin/bash'}]}

        data = {
            'cloudspaceId': cloudspace['id'],
            'name': name,
            'description': name,
            'memory': memory,
            'vcpus': vcpus,
            'imageId': imageId,
            'disksize': 100,
            'userdata': userdata,
        }
        print('Creating VM')
        response = self.session.post('https://{}/restmachine/cloudapi/machines/create'.format(self.envurl), json=data)
        response.raise_for_status()
        machineId = response.json()
        response = self.session.post('https://{}/restmachine/cloudapi/machines/get'.format(self.envurl), json={'machineId': machineId})
        response.raise_for_status()
        vm = response.json()
        print('VM {}: {}'.format(vm['name'], vm['interfaces'][0]['ipAddress']))
        for account in vm['accounts']:
            print('\tUser: {login} / {password}'.format(**account))
       
        pubport = self.get_publicport(cloudspace)

        data = {
            'cloudspaceId': cloudspace['id'],
            'publicIp': cloudspace['externalnetworkip'],
            'publicPort': pubport,
            'machineId': vm['id'],
            'localPort': 22,
            'protocol': 'tcp'
        }
        response = self.session.post('https://{}/restmachine/cloudapi/portforwarding/create'.format(self.envurl), json=data)
        response.raise_for_status()
        print('ssh -p {} root@{}'.format(pubport, cloudspace['externalnetworkip']))

    def get_publicport(self, cloudspace):
        response = self.session.post('https://{}/restmachine/cloudapi/portforwarding/list'.format(self.envurl), json={'cloudspaceId': cloudspace['id']})
        response.raise_for_status()
        forwards = response.json()
        pubport = 3500
        usedports = [int(fwd['publicPort']) for fwd in forwards]
        while pubport in usedports:
            pubport += 1
        return pubport

    def create_forward(self, cloudspace, machine, publicport, privateport):
        vm = self.select_vm(cloudspace, machine)
        if not publicport:
            publicport = self.get_publicport(cloudspace)

        data = {
            'cloudspaceId': cloudspace['id'],
            'publicIp': cloudspace['externalnetworkip'],
            'publicPort': publicport,
            'machineId': vm['id'],
            'localPort': privateport,
            'protocol': 'tcp'
        }
        response = self.session.post('https://{}/restmachine/cloudapi/portforwarding/create'.format(self.envurl), json=data)
        response.raise_for_status()
        data['name'] = vm['name']
        print("{publicIp}:{publicPort} -> {name}:{localPort} {protocol}".format(**data))

    def delete_forward(self, cloudspace, publicport):
        data = {
            'cloudspaceId': cloudspace['id'],
            'publicIp': cloudspace['externalnetworkip'],
            'publicPort': publicport,
        }
        response = self.session.post('https://{}/restmachine/cloudapi/portforwarding/deleteByPort'.format(self.envurl), json=data)
        response.raise_for_status()

    def list_forwards(self, cloudspace):
        response = self.session.post('https://{}/restmachine/cloudapi/portforwarding/list'.format(self.envurl), json={'cloudspaceId': cloudspace['id']})
        response.raise_for_status()
        for fwd in response.json():
            print("{machineName} {publicIp}:{publicPort} -> {localIp}:{localPort} {protocol}".format(**fwd))

    def create_cloudspace(self, name, account, cstype):
        if name is None:
            name = input('Enter name: ')
        account = self.select_account(account)['id']
        data = {'accountId': account, 'name': name}
        if cstype:
            data['type'] = cstype
        whoami = self.session.post('https://{}/restmachine/system/usermanager/whoami'.format(self.envurl))
        whoami.raise_for_status()
        data['access'] = whoami.json()['name']
        location = self.session.post('https://{}/restmachine/cloudapi/locations/list'.format(self.envurl))
        location.raise_for_status()
        data['location'] = location.json()[0]['locationCode']
        response = self.session.post('https://{}/restmachine/cloudapi/cloudspaces/create'.format(self.envurl), json=data)
        response.raise_for_status()

    def connect_node(self):
        def get_nic_ip(iface):
            for nic in self.node['netaddr']:
                if nic['name'] == iface:
                    for ip in nic['ip']:
                        return ip
            return None
        nodeip = get_nic_ip('backplane1')
        if not nodeip:
            nodeip = self.node['ipaddr'][0]

        data = {'remote': nodeip}
        response = self.session.post('https://{}/restmachine/cloudbroker/zeroaccess/provision'.format(self.envurl), json=data)
        response.raise_for_status()
        result = response.json()
        print('Executing: ssh -A -p {ssh_port} {username}@{ssh_ip}'.format(**result))
        subprocess.Popen(['ssh', '-A', '-p', str(result['ssh_port']), "{username}@{ssh_ip}".format(**result)]).communicate()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", help="Filter for environment", default=os.environ.get("ENV_NAME"))
    subparsers = parser.add_subparsers(dest="group")
    
    vmgroup = subparsers.add_parser("vm")
    vmsubs = vmgroup.add_subparsers(dest="vmaction")
    vmcreate = vmsubs.add_parser("create")
    vmlist = vmsubs.add_parser("list")
    vmlist.add_argument('--cloudspace', default=None, help='Preselect cloudspace')

    vmcreate.add_argument('--name', default=None)
    vmcreate.add_argument('--memory', default=1024, type=int, help='VM memory in MiB defaults to 1024')
    vmcreate.add_argument('--vcpus', default=1, type=int, help='VM vcpus defaults to 1')
    vmcreate.add_argument('--cloudspace', default=None, help='Preselect cloudspace')

    vmdelete = vmsubs.add_parser("delete")
    vmdelete.add_argument('--name', default=None)
    vmdelete.add_argument('--cloudspace', default=None, help='Preselect cloudspace')

    console = subparsers.add_parser('zaccess')
    console.add_argument('--node', default=None, help='Preselect node to connect to')

    cloudspace = subparsers.add_parser("cloudspace")
    cssubs = cloudspace.add_subparsers(dest="csaction")
    cssubs.add_parser("list")
    cscreate = cssubs.add_parser("create")
    cscreate.add_argument('--name', default=None)
    cscreate.add_argument('--account', default=None)
    cscreate.add_argument('--type', default=None)

    csdelete = cssubs.add_parser("delete")
    csdelete.add_argument('--name', default=None)

    forwards = subparsers.add_parser('forwarding')
    fwdsubs = forwards.add_subparsers(dest="fwdaction")

    fwdlist = fwdsubs.add_parser("list")
    fwdlist.add_argument('--cloudspace', default=None, help='Preselect cloudspace')

    fwdcreate = fwdsubs.add_parser("create")
    fwdcreate.add_argument('--machine', default=None, help='Preselect vm')
    fwdcreate.add_argument('--publicport', default=None, help='Choose public port')
    fwdcreate.add_argument('--privateport', default=None, help='Choose private port', required=True)
    fwdcreate.add_argument('--cloudspace', default=None, help='Preselect cloudspace')

    fwddelete = fwdsubs.add_parser("delete")
    fwddelete.add_argument('--publicport', default=None, help='Choose public port', required=True)
    fwddelete.add_argument('--cloudspace', default=None, help='Preselect cloudspace')
    options = parser.parse_args()
    try:
        cli = OVCli()
        cli.select_environment(options.env)
        if options.group in [None, 'zaccess']:
            cli.select_node(getattr(options, 'node', None))
            cli.connect_node()
        elif options.group == 'vm':
            cloudspace = cli.select_cloudspace(options.cloudspace)
            if options.vmaction == 'create':
                cli.create_machine(cloudspace, options.name, options.memory, options.vcpus)
            elif options.vmaction == 'list':
                cli.list_vms(cloudspace)
            elif options.vmaction == 'delete':
                cli.delete_vm(cloudspace, options.name)
        elif options.group == 'cloudspace':
            if options.csaction == "list":
                cli.list_cloudspaces()
            elif options.csaction == "create":
                cli.create_cloudspace(options.name, options.account, options.type)
            elif options.csaction == "delete":
                cs = cli.select_cloudspace(options.name)
                cli.delete_cloudspace(cs)
        elif options.group == 'forwarding':
            cloudspace = cli.select_cloudspace(options.cloudspace)
            if options.fwdaction == 'list':
                cli.list_forwards(cloudspace)
            elif options.fwdaction == 'create':
                cli.create_forward(cloudspace, options.machine, options.publicport, options.privateport)
            elif options.fwdaction == 'delete':
                cli.delete_forward(cloudspace, options.publicport)
    except KeyboardInterrupt:
        print('Fine be that way')

