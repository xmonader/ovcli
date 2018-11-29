# ovcli

Small script to access nodes over zero-access and do crud operations on cloudspace/vm/forwards

## Prerequirements

Public key in IYO needs to be configured under the label `ssh`

## Config files

`~/.config/ovc.cfg`
```
[environments]
greenitglobe.environments.be-g8-3 = be-g8-3.demo.greenitglobe.com
greenitglobe.environments.be-g8-4 = be-g8-4.demo.greenitglobe.com
greenitglobe.environments.be-conv-2 = be-conv-2.demo.greenitglobe.com

[iyo]
clientid = my client id
clientsecret = my client secret
```

# Demo
[![asciicast](https://asciinema.org/a/jSdN48CyV4QM0AadnbKnvd9ss.svg)](https://asciinema.org/a/jSdN48CyV4QM0AadnbKnvd9ss)

