# zmfcli

![build](https://github.com/kressi/zmf-cli/workflows/Python%20package/badge.svg)
[![PyPi Version](https://img.shields.io/pypi/v/zmfcli.svg)](https://pypi.python.org/pypi/zmfcli)
[![Maintainability](https://api.codeclimate.com/v1/badges/d2ded62d131d2b832d9b/maintainability)](https://codeclimate.com/github/kressi/zmf-cli/maintainability)
[![codecov](https://codecov.io/gh/kressi/zmf-cli/branch/main/graph/badge.svg?token=ZDHD04MJDR)](https://codecov.io/gh/kressi/zmf-cli)

Command line interface (cli) for ChangeMan ZMF through REST API. Using
[fire](https://github.com/google/python-fire) to create the cli.

## Usage

### Credentials
Credentials and url can be exported to `ZMF_REST_*` variables, so those
do not need to be privided with each command execution.
```bash
export ZMF_REST_URL=http://httpbin.org:80/anything/zmfrest
export ZMF_REST_USER=U000000
export ZMF_REST_PWD=pa$$w0rd
zmf build "APP 000001" "['src/SRE/APP00001.sre', 'src/SRB/APP00002.srb', 'src/SRB/APP00003.srb']"
```

### Example
Audit a package
```bash
$ zmf audit "APP 000001"
```

### Commands
Get help for a command
```bash
$ zmf promote --help
```

| Command              | Description                                 |
|----------------------|---------------------------------------------|
| checkin              | PUT component/checkin                       |
| build                | PUT component/build                         |
| scratch              | PUT component/scratch                       |
| audit                | PUT package/audit                           |
| promote              | PUT package/promote                         |
| freeze               | PUT package/freeze                          |
| revert               | PUT package/revert                          |
| search-package       | GET package/search                          |
| create-package       | POST package                                |
| get-package          | Search or create if package does not exist  |
| get-components       | GET component                               |
| get-load-components  | GET component/load                          |
| browse-component     | GET component/browse                        |

### Pretty print result
Some results may return JSON data, this data can be pretty printed with Python
```bash
zmf get-load-components "APP 000001" "LST" | python -m json.tools
```

## ChangeMan ZMF Documents
- [ChangeMan ZMF 8.1 - Web Services Getting Started Guide](https://supportline.microfocus.com/documentation/books/ChangeManZMF/8.1.4/ChangeManZMFWebServices/ZMF%20Web%20Services%20Getting%20Started%20Guide.pdf)
- [ChangeMan ZMF - REST Services Getting Started Guide](https://www.microfocus.com/documentation/changeman-zmf/8.2.2/ZMF%20REST%20Services%20Getting%20Started%20Guide%20(Updated%2024%20October%202019).pdf)
- [ChangeMan ZMF - User’s Guide](https://www.microfocus.com/documentation/changeman-zmf/8.2.1/ZMF%20Users%20Guide.pdf)
- [ChangeMan ZMF 8.1 - XML Services User’s Guide](https://supportline.microfocus.com/documentation/books/ChangeManZMF/8.1.4/ChangeManZMF/ZMF%20XML%20Services%20Users%20Guide.pdf)

