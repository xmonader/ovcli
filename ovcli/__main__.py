#!/usr/bin/env python3
from .client import Client
from .parsers import parser

def main():
    options = parser.parse_args()
    try:
        cli = Client()
        cli.select_environment(options.env)
        if options.group in [None, 'zaccess']:
            cli.select_node(getattr(options, 'node', None))
            cli.connect_node()
        elif options.group == 'vm':
            cloudspace = cli.select_cloudspace(options.cloudspace)
            if options.vmaction == 'create':
                cli.create_machine(cloudspace, options.name, options.memory, options.vcpus)
            elif options.vmaction == 'list':
                cli.print_vms(cloudspace)
            elif options.vmaction == 'delete':
                cli.delete_vm(cloudspace, options.name)
        elif options.group == 'cloudspace':
            if options.csaction == "list":
                cli.print_cloudspaces()
            elif options.csaction == "create":
                cli.create_cloudspace(options.name, options.account, options.type)
            elif options.csaction == "delete":
                cs = cli.select_cloudspace(options.name)
                cli.delete_cloudspace(cs)
        elif options.group == 'forwarding':
            cloudspace = cli.select_cloudspace(options.cloudspace)
            if options.fwdaction == 'list':
                cli.print_cloudspaces(cloudspace)
            elif options.fwdaction == 'create':
                cli.create_forward(cloudspace, options.machine, options.publicport, options.privateport)
            elif options.fwdaction == 'delete':
                cli.delete_forward(cloudspace, options.publicport)
    except KeyboardInterrupt:
        print('Fine be that way')

if __name__ == '__main__':
    main()
