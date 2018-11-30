import argparse
import os

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
