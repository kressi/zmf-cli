# zmfcli

[![Build Status](https://travis-ci.org/kressi/zmf-cli.svg?branch=main)](https://travis-ci.org/kressi/zmf-cli)
[![PyPi Version](https://img.shields.io/pypi/v/zmfcli.svg)](https://pypi.python.org/pypi/zmfcli)
[![Maintainability](https://api.codeclimate.com/v1/badges/d2ded62d131d2b832d9b/maintainability)](https://codeclimate.com/github/kressi/zmf-cli/maintainability)
[![Coverage Status](https://coveralls.io/repos/github/kressi/zmf-cli/badge.svg?branch=main)](https://coveralls.io/github/kressi/zmf-cli?branch=main)

Command line interface (cli) for ChangeMan ZMF through REST API. Using
[fire](https://github.com/google/python-fire) to create the cli.

## Usage

Export credentials and url, so it is available in later requests.
```bash
export ZMF_REST_URL=https://example.com:8080/zmfrest
export ZMF_REST_USER=username
export ZMF_REST_PWD=password
zmf build "APP 000001" "['src/SRE/APP00001.sre', 'src/SRB/APP00002.srb', 'src/SRB/APP00003.srb']"
```

```bash
cat <<'CONFIG' | zmf package /dev/stdin
applName: APP
createMethod: 0
packageLevel: 1
packageType: 1
requestorDept: DEVB
requestorName: DEVA
requestorPhone: 01000000
workChangeRequest: APP 000000
packageTitle: DEV release/2021-12-31
packageDesc: created with ZMF Rest API
siteName: ZPLEX0
installDate: 20211231
fromInstallTime: 0000
toInstallTime: 2359
contactName: Timothy Leary
contactPhone: 01000000
alternateContactName: Terrence McKenna
alternateContactPhone: 01000000
CONFIG
```

## ChangeMan ZMF Documents
- [ChangeMan ZMF 8.1 - Web Services Getting Started Guide](https://supportline.microfocus.com/documentation/books/ChangeManZMF/8.1.4/ChangeManZMFWebServices/ZMF%20Web%20Services%20Getting%20Started%20Guide.pdf)
- [ChangeMan ZMF - REST Services Getting Started Guide](https://www.microfocus.com/documentation/changeman-zmf/8.2.2/ZMF%20REST%20Services%20Getting%20Started%20Guide%20(Updated%2024%20October%202019).pdf)
- [ChangeMan ZMF - User’s Guide](https://www.microfocus.com/documentation/changeman-zmf/8.2.1/ZMF%20Users%20Guide.pdf)
- [ChangeMan ZMF 8.1 - XML Services User’s Guide](https://supportline.microfocus.com/documentation/books/ChangeManZMF/8.1.4/ChangeManZMF/ZMF%20XML%20Services%20Users%20Guide.pdf)
