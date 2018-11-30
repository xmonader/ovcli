from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completion
from prompt_toolkit.eventloop.async_generator import AsyncGeneratorItem
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.shortcuts import yes_no_dialog
from prompt_toolkit.styles import Style
import yaml

from .client import Client


def log(text):
    with open("/tmp/ovc.log", "a+") as fd:
        fd.writelines([str(text)])

style = Style.from_dict({
    # User input (default text).
    '':          '#aaaaaa',
    'default':          '#aaaaaa',

    # Prompt.
    'env': 'ansiyellow',
    'action':       'ansimagenta',
    'cloudspace':    'ansimagenta',
    'cloudspaces':    'ansiblue',
    'console':    'ansiblue',
    'forwards':    'ansicyan',
    'machines':    'ansicyan',
    'host':     '#00ffff bg:#444400',
    'path':     'ansicyan underline',
})

def action(text):
    return Completion(text, style="bg:ansigreen fg:ansiwhite")

def deleteaction(text):
    return Completion(text, style="bg:ansired fg:ansiwhite")

def menu(text):
    return Completion(text, style="bg:ansibrightblue fg:ansiwhite")

class Component:
    def __init__(self, shell):
        self.shell = shell

    def completer(self):
        yield

    def update_components(self, result):
        if result == "..":
            self.shell.components.pop()
            return True
        elif result == "/":
            self.shell.components = self.shell.components[:1]
            return True

    def message(self):
        return ('class:default', str(self))

    def validate(self, document):
        text = document.current_line_before_cursor
        if not text:
            return
        for item in self.completer():
            if not isinstance(item, Completion):
                item = Completion(item)
            if item.text == text:
                return
        if text in ["/", ".."]:
            return
        raise ValidationError(message="Invalid action")

class EnvSubComponent(Component):
    def __init__(self, shell, environment):
        super().__init__(shell)
        self.shell.client.set_environment(environment)

    def completer(self):
        yield menu("console")
        yield menu("cloudspace")

    def update_components(self, result):
        if super().update_components(result):
            return
        if result == "console":
            self.shell.components.append(ConsoleComponent(self.shell))
        elif result == "cloudspace":
            self.shell.components.append(CloudSpaceListComponent(self.shell))

    def message(self):
        return ('class:env', str(self))

    def __str__(self):
        return self.shell.client.environment.split(".")[-1]

class CloudSpaceComponent(Component):
    def __init__(self, shell, cloudspace):
        super().__init__(shell)
        self.cloudspace = cloudspace

    def update_components(self, result):
        if super().update_components(result):
            return
        if result == "delete":
            if yes_no_dialog("Confirm", "Are you sure you want to delete cloudspace {}".format(self.cloudspace["name"])):
                self.shell.client.delete_cloudspace(self.cloudspace)
                super().update_components("..")
        elif result == "vm":
            vmcom = VMListComponent(self.shell, self.cloudspace)
            self.shell.components.append(vmcom)
        elif result == "forwards":
            fwcom = ForwardListCompontent(self.shell, self.cloudspace)
            self.shell.components.append(fwcom)

    def completer(self):
        yield menu("vm")
        yield menu("forwards")
        yield deleteaction("delete")


    def message(self):
        return ('class:cloudspace', str(self))

    def __str__(self):
        return self.cloudspace["name"]


class VMComponent(Component):
    def __init__(self, shell, vm):
        super().__init__(shell)
        self.vm = vm

    def update_components(self, result):
        if super().update_components(result):
            return
        if result == "delete":
            if yes_no_dialog("Confirm", "Are you sure you want to delete vm {}".format(self.vm["name"])):
                self.shell.client.delete_vm_by_id(self.vm['id'])
                super().update_components("..")
        elif result in ["start", "reboot", "pause", "resume", "stop"]:
            self.shell.client.vm_action(result, self.vm['id'])
            self.vm = self.shell.client.vm_action('get', self.vm['id'])
        elif result.startswith("createforward"):
            segments = result.split()
            if len(segments) not in [2, 3]:
                print("Invalid call, usages:\n createforward [publicport] privateport")
                return
            for port in segments[1:]:
                if not port.isdigit():
                    print("Ports should be numbers")
                    return
            if len(segments) == 2:
                privateport = int(segments[1])
                publicport = None
            else:
                privateport = int(segments[2])
                publicport = int(segments[1])
            self.shell.client.create_forward(self.shell.components[3].cloudspace, self.vm['name'], publicport, privateport)
        elif result == "print":
            self.vm = self.shell.client.vm_action('get', self.vm['id'])
            print(yaml.safe_dump(self.vm, default_flow_style=False))

    def completer(self):
        if self.vm['status'] == 'RUNNING':
            yield action("stop")
            yield action("reboot")
            yield action("pause")
        elif self.vm['status'] == 'HALTED':
            yield action("start")
        elif self.vm['status'] == 'PAUSED':
            yield action("resume")
            yield action("stop")
        yield action("createforward")
        yield action("print")
        yield deleteaction("delete")

    def message(self):
        return ('class:machine', str(self))

    def __str__(self):
        return self.vm["name"]

class CloudSpaceListComponent(Component):
    def __init__(self, shell):
        super().__init__(shell)
        self.cloudspaces = self.shell.client.list_cloudspaces()

    def completer(self):
        yield action("create")
        yield action("print")
        for cs in self.cloudspaces:
            yield cs["name"]

    def update_components(self, result):
        if super().update_components(result):
            return
        if result == "print":
            self.shell.client.print_cloudspaces(self.cloudspaces)
            return
        elif result == "create":
            name = self.shell.prompt("Name: ")
            self.shell.client.create_cloudspace(name, None, None)
            self.cloudspaces = self.shell.client.list_cloudspaces()
            result = name
        for cs in self.cloudspaces:
            if cs["name"] == result:
                cscomponent = CloudSpaceComponent(self.shell, cs)
                self.shell.components.append(cscomponent)
                return

    def __str__(self):
        return "cloudspace"

    def message(self):
        return ('class:cloudspaces', str(self))


class ForwardListCompontent(Component):
    def __init__(self, shell, cloudspace):
        super().__init__(shell)
        self.cloudspace = cloudspace
        self.forwards = self.shell.client.list_forwards(cloudspace)

    def completer(self):
        yield action("print")
        yield deleteaction("delete")

    def update_components(self, result):
        if super().update_components(result):
            return
        if result == "print":
            self.forwards = self.shell.client.list_forwards(self.cloudspace)
            self.shell.client.print_forwards(self.cloudspace, self.forwards)
        elif result.startswith("delete "):
            pubport = result.split()[-1]
            if pubport.isdigit():
                if yes_no_dialog("Confirm", "Are you sure you want to delete forward {}".format(pubport)):
                    self.shell.client.delete_forward(self.cloudspace, int(pubport))

    def validate(self, document):
        text = document.current_line_before_cursor
        if text in ["/", "..", "print"]:
            return
        if text.startswith("delete"):
            port = text.split()[-1]
            if not port.isdigit():
                raise ValidationError(message="Public port should be a number")

    def __str__(self):
        return "forwards"

    def message(self):
        return ('class:forwards', str(self))

class VMListComponent(Component):
    def __init__(self, shell, cloudspace):
        super().__init__(shell)
        self.cloudspace = cloudspace
        self.vms = self.shell.client.list_vms(cloudspace)

    def completer(self):
        yield action("create")
        yield action("print")
        for vm in self.vms:
            yield vm["name"]

    def update_components(self, result):
        if super().update_components(result):
            return
        if result == "create":
            vm = self.shell.client.create_machine(self.cloudspace)
            vmcomponent = VMComponent(self.shell, vm)
            self.shell.components.append(vmcomponent)
            return
        elif result == "print":
            self.vms = self.shell.client.list_vms(self.cloudspace)
            self.shell.client.print_vms(self.cloudspace, self.vms)
            return
        for vm in self.vms:
            if vm["name"] == result:
                vmcomponent = VMComponent(self.shell, vm)
                self.shell.components.append(vmcomponent)
                return

    def __str__(self):
        return "vm"

    def message(self):
        return ('class:machines', str(self))

class ConsoleComponent(Component):
    def __init__(self, shell):
        super().__init__(shell)
        self.nodes = self.shell.client.list_nodes()

    def completer(self):
        for node in self.nodes:
            yield node

    def update_components(self, result):
        if super().update_components(result):
            return
        if result in self.nodes:
            self.shell.client.set_node(result)
            self.shell.client.connect_node()

    def __str__(self):
        return "console"

    def message(self):
        return ('class:console', str(self))

class RootComponent(Component):
    def completer(self):
        for env in self.shell.client.environments:
            yield env

    def update_components(self, result):
        if result in self.shell.client.environments:
            self.shell.components.append(EnvSubComponent(self.shell, result))

    def __str__(self):
        return ""

class Shell(Validator):
    def __init__(self, client):
        self.client = client
        self._prompt = PromptSession()
        self.mode = None
        self.cloudspace = None
        self.components = [RootComponent(self)]

    def get_completions_async(self, document, complete_event):
        for item in self.components[-1].completer():
            text = document.current_line_before_cursor
            if not item:
                continue
            if isinstance(item, Completion):
                item.start_position = -len(text)
            else:
                item = Completion(item, -len(text))
            if text in item.text:
                yield AsyncGeneratorItem(item)

    def validate(self, document):
        return self.components[-1].validate(document)

    def make_prompt(self):
        seperator = ('class:default', '/')
        while True:
            component = self.components[-1]
            message = []
            for component in self.components:
                message.append(component.message())
                message.append(seperator)
            message[-1] = ('class:default', " > ")
            result = self.prompt(message)
            component.update_components(result)


    def prompt(self, msg):
        return self._prompt.prompt(msg, completer=self, style=style, validator=self)

        
def main():
    cl = Client()
    try:
        Shell(cl).make_prompt()
    except (EOFError, KeyboardInterrupt):
        pass

if __name__ == '__main__':
    main()

